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
        st.dataframe(result_df, width="stretch")
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
                st.plotly_chart(fig, width="stretch")

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


if IS_HF_SPACE and st.session_state.df is None:
    if os.path.exists(SAMPLE_DATA_PATH):
        ok, df = _load_into_state(SAMPLE_DATA_PATH, "Loading demo dataset...")
        # Don't show a status message — just proceed silently

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

    if IS_HF_SPACE:
        st.markdown(
            "<div class='status-line'>Demo mode — sample dataset loaded</div>",
            unsafe_allow_html=True,
        )
        st.caption(
            "To query your o