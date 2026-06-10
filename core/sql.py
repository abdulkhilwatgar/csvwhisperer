"""
sql.py — LLM-powered SQL generation for CSVWhisperer.
Supports both local Ollama (offline) and HuggingFace Inference API (deployed).
Includes automatic retry loop on SQL errors.
"""

import os
import re
from typing import Optional


# ── Prompt construction ────────────────────────────────────────────────────────

def build_system_prompt(schema_description: str) -> str:
    return f"""You are an expert DuckDB SQL analyst. Your job is to write precise SQL queries to answer questions about a dataset.

{schema_description}

STRICT RULES:
- The table is always named "data"
- Return ONLY the raw SQL query — no explanation, no markdown, no backticks, no comments
- Use DuckDB-compatible syntax (e.g. STRFTIME, EPOCH, LIST_AGG)
- For text matching, prefer ILIKE for case-insensitive search
- Always quote column names that contain spaces using double quotes
- Use LIMIT 500 unless the user explicitly asks for more rows
- For aggregation questions, always GROUP BY the categorical dimension
- Never use SELECT * unless the user explicitly asks to "show all columns"
- Always alias aggregate or computed expressions (e.g. COUNT(*), SUM(...), AVG(...)) with a descriptive snake_case name using AS — never leave a column unaliased
"""


def build_retry_prompt(original_question: str, failed_sql: str, error: str) -> str:
    return f"""The previous SQL query failed. Fix it.

Original question: {original_question}
Failed SQL: {failed_sql}
Error: {error}

Return ONLY the corrected SQL query with no explanation."""


# ── SQL extraction ─────────────────────────────────────────────────────────────

def extract_sql(response: str) -> str:
    """Strip markdown formatting and extract raw SQL from LLM response."""
    # Try code blocks first
    for pattern in [r"```sql\n(.*?)```", r"```\n(.*?)```", r"```(.*?)```"]:
        match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

    # Strip any leading "sql" keyword artifact
    sql = response.strip()
    sql = re.sub(r"^sql\s*\n?", "", sql, flags=re.IGNORECASE)

    # Take only lines that look like SQL (stop at blank explanation lines)
    sql_lines = []
    for line in sql.splitlines():
        stripped = line.strip()
        if not stripped:
            if sql_lines:
                break
        else:
            sql_lines.append(line)

    return "\n".join(sql_lines).strip()


# ── LLM backends ──────────────────────────────────────────────────────────────

def _call_ollama(messages: list, model: str = "qwen2.5-coder:7b") -> str:
    """Call local Ollama instance."""
    import ollama
    response = ollama.chat(
        model=model,
        messages=messages,
        options={"temperature": 0.0, "num_predict": 512},
    )
    return response["message"]["content"]


def _call_hf(messages: list) -> str:
    """Call HuggingFace Inference API."""
    from huggingface_hub import InferenceClient

    client = InferenceClient(token=os.getenv("HF_TOKEN"))
    response = client.chat_completion(
        model="Qwen/Qwen2.5-Coder-7B-Instruct",
        messages=messages,
        temperature=0.0,
        max_tokens=512,
    )
    return response.choices[0].message.content


def _generate(messages: list) -> str:
    """Route to Ollama or HF depending on environment."""
    if os.getenv("HF_SPACE", "false").lower() == "true":
        return _call_hf(messages)
    return _call_ollama(messages)


# ── Main generation function ───────────────────────────────────────────────────

def generate_sql_with_retry(
    question: str,
    schema_description: str,
    executor,
    conversation_history: Optional[list] = None,
    max_retries: int = 3,
) -> dict:
    """
    Generate SQL for the user's question with automatic retry on errors.

    Returns a dict with:
        sql       — final SQL attempted
        result    — DataFrame on success, None on failure
        error     — error message on failure, None on success
        attempts  — list of (sql, error) for each attempt
        success   — bool
    """
    system_prompt = build_system_prompt(schema_description)

    # Build base messages with optional conversation context
    base_messages = [{"role": "system", "content": system_prompt}]

    # Include last 2 Q&A pairs for follow-up awareness
    if conversation_history:
        for turn in conversation_history[-4:]:
            base_messages.append(turn)

    base_messages.append({"role": "user", "content": question})

    attempts = []
    last_sql = ""
    last_error = ""

    for i in range(max_retries):
        if i == 0:
            messages = base_messages
        else:
            # On retry, replace last user message with retry prompt
            messages = base_messages[:-1] + [
                {
                    "role": "user",
                    "content": build_retry_prompt(question, last_sql, last_error),
                }
            ]

        try:
            raw_response = _generate(messages)
        except Exception as e:
            last_sql = ""
            last_error = f"LLM call failed: {e}"
            attempts.append({"sql": last_sql, "error": last_error})
            continue

        sql = extract_sql(raw_response)
        last_sql = sql

        if not sql:
            last_error = "LLM returned an empty response."
            attempts.append({"sql": sql, "error": last_error})
            continue

        success, result = executor.execute(sql)

        if success:
            attempts.append({"sql": sql, "error": None})
            return {
                "sql": sql,
                "result": result,
                "error": None,
                "attempts": attempts,
                "success": True,
            }

        last_error = result
        attempts.append({"sql": sql, "error": last_error})

    return {
        "sql": last_sql,
        "result": None,
        "error": last_error,
        "attempts": attempts,
        "success": False,
    }
