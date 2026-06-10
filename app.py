"""
CSVWhisperer — Natural language querying for any CSV file.
Fully local: your data never leaves your machine.

Run: streamlit run app.py
"""

import os
import streamlit as st
import pandas as pd

from core.schema import load_csv, build_schema_description, get_schema_summary
from core.executor import QueryExecutor
from core.sql import generate_sql_with_retry
from core.visualizer import auto_visualize, format_single_value_result, should_visualize

# Detect HF Spaces deployment
IS_HF_SPACE = os.getenv("HF_SPACE", "false").lower() == "true"
SAMPLE_DATA_PATH = os.path.join(os.path.dirname(__file__), "sample_data.csv")

# ── Page config ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="CSVWhisperer",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styling ────────────────────────────────────────────────────────────────────

CUSTOM_CSS = """
<style>
:root {
    --bg-elevated: #1c1a17;
    --border: #2e2b27;
    --text: #ede9e4;
    --text-muted: #968e84;
    --accent: #d97757;
}

h1, h2, h3 {
    font-family: Georgia, "Iowan Old Style", "Times New Roman", serif !important;
    font-weight: 500 !important;
    letter-spacing: -0.01em;
}

/* Hide the "Deploy" button — not relevant for a local tool */
[data-testid="stAppDeployButton"] { display: none; }

/* Sidebar */
[data-testid="stSidebar"] {
    border-right: 1px solid var(--border);
}

.wordmark {
    font-family: Georgia, "Iowan Old Style", "Times New Roman", serif;
    font-size: 1.6rem;
    font-weight: 600;
    letter-spacing: -0.02em;
    color: var(--text);
    line-height: 1.2;
}
.wordmark-tag {
    color: var(--text-muted);
    font-size: 0.85rem;
    margin-top: 0.15rem;
}

.section-label {
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-size: 0.7rem;
    color: var(--text-muted);
    font-weight: 600;
    margin: 1.4rem 0 0.5rem 0;
}

.status-line {
    font-size: 0.85rem;
    color: var(--text);
    padding: 0.45rem 0.7rem;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--bg-elevated);
    margin-bottom: 0.5rem;
}
.status-line::before {
    content: "";
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--accent);
    margin-right: 0.55rem;
}

/* Buttons */
.stButton > button {
    border-radius: 6px;
    border: 1px solid var(--border);
    background: transparent;
    color: var(--text);
    font-weight: 400;
    transition: border-color 0.15s ease, color 0.15s ease;
}
.stButton > button:hover {
    border-color: var(--accent);
    color: var(--accent);
}

/* Alerts */
div[data-testid="stAlertContainer"] {
    border-radius: 6px;
    border: 1px solid var(--border);
}

/* Hero */
.hero {
    padding: 2.5rem 0 2rem 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 2rem;
}
.hero h1 {
    font-size: 2.6rem !important;
    margin: 0 0 0.7rem 0 !important;
}
.hero p {
    color: var(--text-muted);
    font-size: 1.05rem;
    max-width: 38rem;
    line-height: 1.65;
}

/* How it works */
.steps {
    display: flex;
    gap: 2.5rem;
    margin: 0 0 2.5rem 0;
    flex-wrap: wrap;
}
.step {
    max-width: 16rem;
}
.step-num {
    font-family: Georgia, serif;
    color: var(--accent);
    font-size: 1.1rem;
    margin-bottom: 0.3rem;
}
.step-title {
    font-weight: 600;
    margin-bottom: 0.2rem;
}
.step-desc {
    color: var(--text-muted);
    font-size: 0.9rem;
    line-height: 1.55;
}

/* Example prompts */
.prompt-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 0.6rem;
    margin-top: 0.6rem;
}
.prompt-card {
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.8rem 1rem;
    font-size: 0.9rem;
    color: var(--text-muted);
    font-family: Georgia, "Iowan Old Style", "Times New Roman", serif;
    font-style: italic;
}

/* Data bar */
.data-bar {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 0.4rem 1.5rem;
    padding-bottom: 0.8rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: 1.2rem;
}
.data-bar-name {
    font-family: Georgia, "Iowan Old Style", "Times New Roman", serif;
    font-size: 1.2rem;
    color: var(--text);
}
.data-bar-meta {
    color: var(--text-muted);
    font-size: 0.85rem;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ── Helpers ────────────────────────────────────────────────────────────────────

def render_result(result_df: pd.DataFrame, sql: str, attempts: list, question: str = ""):
    """Render a successful query result: value/table + chart + SQL expander."""
    single = format_single_value_result(result_df)
    if single:
        st.markdown(single)
    elif result_df.empty:
        st.info("The query returned no results.")
    else:
        st.dataframe(result_df, use_container_width=True)
        if should_visualize(result_df):
            fig = auto_visualize(result_df, question)
            if fig:
                fig.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="#ede9e4",
                    font_family="-apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, sans-serif",
                    title_font_family="Georgia, 'Times New Roman', serif",
                )
                st.plotly_chart(fig, use_container_width=True)

    with st.expander("View generated SQL"):
        st.code(sql, language="sql")
        if len(attempts) > 1:
            st.caption(f"Required {len(attempts)} attempt(s) to produce valid SQL.")


def render_failure(error: str, attempts: list):
    """Render a failed query with error details."""
    st.error(f"Could not generate valid SQL after {len(attempts)} attempt(s).")
    st.caption(f"Last error: `{error}`")
    with st.expander("View attempted SQL"):
        for i, attempt in enumerate(attempts):
            st.markdown(f"**Attempt {i+1}:**")
            st.code(attempt["sql"], language="sql")
            if attempt["error"]:
                st.caption(f"Error: {attempt['error']}")


def render_stored_message(msg: dict):
    """Re-render a stored assistant message from session history."""
    if not msg.get("success", True):
        render_failure(msg.get("error", "Unknown error"), msg.get("attempts", []))
        return
    render_result(
        msg["result_df"],
        msg["sql"],
        msg.get("attempts", []),
        msg.get("question", ""),
    )


# ── Session state ──────────────────────────────────────────────────────────────

def init_state():
    defaults = {
        "df": None,
        "executor": None,
        "schema_description": None,
        "schema_summary": None,
        "filename": None,
        "messages": [],
        "llm_history": [],
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_state()

# ── Auto-load sample data on HF Spaces ────────────────────────────────────────

def _load_into_state(file_or_path, spinner_label="Loading dataset..."):
    with st.spinner(spinner_label):
        try:
            df, filename = load_csv(file_or_path)
            if st.session_state.executor:
                st.session_state.executor.close()
            st.session_state.df = df
            st.session_state.executor = QueryExecutor(df)
            st.session_state.schema_description = build_schema_description(df, filename)
            st.session_state.schema_summary = get_schema_summary(df)
            st.session_state.filename = filename
            st.session_state.messages = []
            st.session_state.llm_history = []
            return True, df
        except Exception as e:
            st.error(f"Couldn't read this file: {e}")
            return False, None


# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        """
        <div class="wordmark">CSVWhisperer</div>
        <div class="wordmark-tag">Plain-English queries for CSV files.</div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()

    uploaded_file = st.file_uploader(
        "Upload a CSV file", type=["csv"], label_visibility="collapsed"
    )
    if uploaded_file is not None and uploaded_file.name != st.session_state.filename:
        _load_into_state(uploaded_file)

    if st.session_state.df is not None:
        st.markdown('<div class="section-label">Dataset</div>', unsafe_allow_html=True)
        st.markdown(
            f"<div class='status-line'>{st.session_state.filename}</div>",
            unsafe_allow_html=True,
        )
        st.caption(
            f"{len(st.session_state.df):,} rows · {len(st.session_state.df.columns)} columns"
        )

        st.markdown('<div class="section-label">Columns</div>', unsafe_allow_html=True)
        for col, info in st.session_state.schema_summary.items():
            stats = f"{info['type']} · {info['unique']:,} unique"
            if info["nulls"]:
                stats += f" · {info['nulls']:,} nulls"
            st.caption(f"**{col}** — {stats}")

        st.divider()
        if st.button("Clear data", use_container_width=True):
            st.session_state.executor.close()
            st.session_state.df = None
            st.session_state.executor = None
            st.session_state.schema_description = None
            st.session_state.schema_summary = None
            st.session_state.filename = None
            st.session_state.messages = []
            st.session_state.llm_history = []
            st.rerun()


# ── Main panel ─────────────────────────────────────────────────────────────────

if st.session_state.df is None:
    st.markdown(
        """
        <div class="hero">
            <h1>Talk to your CSV.</h1>
            <p>
                Upload a CSV file and ask questions about it in plain English.
                CSVWhisperer turns your question into SQL, runs it locally
                against your data, and shows you a table or chart — no query
                writing required.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-label">How it works</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="steps">
            <div class="step">
                <div class="step-num">1</div>
                <div class="step-title">Upload a CSV</div>
                <div class="step-desc">
                    Use the uploader in the sidebar. Your data stays on your
                    machine and is never sent anywhere.
                </div>
            </div>
            <div class="step">
                <div class="step-num">2</div>
                <div class="step-title">Ask a question</div>
                <div class="step-desc">
                    Type a question about your data the same way you'd ask a
                    colleague.
                </div>
            </div>
            <div class="step">
                <div class="step-num">3</div>
                <div class="step-title">Get an answer</div>
                <div class="step-desc">
                    CSVWhisperer writes the SQL, runs it, and shows you a
                    table or chart.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-label">Example prompts</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="prompt-grid">
            <div class="prompt-card">"What are the top 10 rows by revenue?"</div>
            <div class="prompt-card">"Show me the average value by category."</div>
            <div class="prompt-card">"How many records are there per month?"</div>
            <div class="prompt-card">"Which group has grown the most over time?"</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

else:
    df = st.session_state.df
    st.markdown(
        f"""
        <div class="data-bar">
            <div class="data-bar-name">{st.session_state.filename}</div>
            <div class="data-bar-meta">{len(df):,} rows · {len(df.columns)} columns</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(msg["content"])
        else:
            with st.chat_message("assistant"):
                render_stored_message(msg)

    if question := st.chat_input("Ask a question about your data..."):
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = generate_sql_with_retry(
                    question,
                    st.session_state.schema_description,
                    st.session_state.executor,
                    st.session_state.llm_history,
                )

            if response["success"]:
                render_result(
                    response["result"], response["sql"], response["attempts"], question
                )
                st.session_state.messages.append({
                    "role": "assistant",
                    "success": True,
                    "result_df": response["result"],
                    "sql": response["sql"],
                    "attempts": response["attempts"],
                    "question": question,
                })
                st.session_state.llm_history.append({"role": "user", "content": question})
                st.session_state.llm_history.append(
                    {"role": "assistant", "content": response["sql"]}
                )
            else:
                render_failure(response["error"], response["attempts"])
                st.session_state.messages.append({
                    "role": "assistant",
                    "success": False,
                    "error": response["error"],
                    "attempts": response["attempts"],
                    "question": question,
                })
