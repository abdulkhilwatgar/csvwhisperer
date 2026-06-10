"""
visualizer.py — Automatic chart generation for CSVWhisperer query results.
Detects result shape and picks the most appropriate Plotly chart type.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional


# ── Palette ────────────────────────────────────────────────────────────────────
# A muted, hand-picked palette (clay, sage, slate, sand, dusk) used in place of
# Plotly's default primary-color set, plus a two-stop scale for the accent color.

PALETTE = ["#D97757", "#7C9885", "#5B7C99", "#B8A394", "#A8763E", "#6B7B8C"]
ACCENT_SCALE = ["#2A2724", "#D97757"]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _numeric_cols(df: pd.DataFrame) -> list:
    return df.select_dtypes(include=["number"]).columns.tolist()


def _categorical_cols(df: pd.DataFrame) -> list:
    return df.select_dtypes(exclude=["number"]).columns.tolist()


def _looks_like_date(col: pd.Series) -> bool:
    try:
        pd.to_datetime(col.dropna().head(10), format="mixed")
        return True
    except Exception:
        return False


def _format_number(val) -> str:
    """Format a number for display in single-value results."""
    try:
        f = float(val)
        if f == int(f) and abs(f) < 1e12:
            return f"{int(f):,}"
        elif abs(f) >= 1e9:
            return f"{f/1e9:.2f}B"
        elif abs(f) >= 1e6:
            return f"{f/1e6:.2f}M"
        elif abs(f) >= 1e3:
            return f"{f/1e3:.1f}K"
        else:
            return f"{f:,.2f}"
    except Exception:
        return str(val)


def format_single_value_result(df: pd.DataFrame) -> Optional[str]:
    """
    If the result is a single cell (1 row, 1 column), format it as a
    large markdown value with its column name as a caption.
    Returns None for any other shape.
    """
    if df is None or df.shape != (1, 1):
        return None

    col = df.columns[0]
    val = df.iloc[0, 0]

    if pd.isna(val):
        display = "—"
    elif pd.api.types.is_numeric_dtype(df[col]) and not pd.api.types.is_bool_dtype(df[col]):
        display = _format_number(val)
    else:
        display = str(val)

    label = str(col).replace("_", " ").strip()
    return f"### {display}\n{label}"


# ── Chart decision logic ───────────────────────────────────────────────────────

def should_visualize(df: pd.DataFrame) -> bool:
    if df is None or df.empty or len(df) < 2:
        return False
    return len(_numeric_cols(df)) > 0


def auto_visualize(df: pd.DataFrame, question: str = "") -> Optional[go.Figure]:
    """
    Given a query result DataFrame, auto-select and build the best chart.
    Returns a Plotly Figure or None if visualization isn't appropriate.
    """
    if not should_visualize(df):
        return None

    num_cols = _numeric_cols(df)
    cat_cols = _categorical_cols(df)

    # Clamp to top 25 rows for bar charts (readability)
    MAX_BAR_ROWS = 25

    # ── Case 1: date-like first col + numeric → line chart ──────────────────
    if cat_cols and num_cols and _looks_like_date(df[cat_cols[0]]):
        date_col = cat_cols[0]
        try:
            plot_df = df.copy()
            plot_df[date_col] = pd.to_datetime(plot_df[date_col])
            plot_df = plot_df.sort_values(date_col)
            fig = px.line(
                plot_df,
                x=date_col,
                y=num_cols,
                title=f"Trend over {date_col}",
                markers=True,
                color_discrete_sequence=PALETTE,
            )
            return fig
        except Exception:
            pass

    # ── Case 2: 1 categorical + 1 numeric → horizontal bar ──────────────────
    if len(cat_cols) == 1 and len(num_cols) == 1:
        cat, num = cat_cols[0], num_cols[0]
        plot_df = df.nlargest(MAX_BAR_ROWS, num) if len(df) > MAX_BAR_ROWS else df
        plot_df = plot_df.sort_values(num, ascending=True)
        fig = px.bar(
            plot_df,
            x=num,
            y=cat,
            orientation="h",
            title=f"{num} by {cat}",
            color=num,
            color_continuous_scale=ACCENT_SCALE,
            text=num,
        )
        fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
        fig.update_layout(showlegend=False, coloraxis_showscale=False)
        return fig

    # ── Case 3: 1 categorical + multiple numerics → grouped bar ─────────────
    if len(cat_cols) == 1 and len(num_cols) > 1:
        cat = cat_cols[0]
        plot_df = df.head(MAX_BAR_ROWS)
        fig = px.bar(
            plot_df,
            x=cat,
            y=num_cols,
            title=f"Comparison by {cat}",
            barmode="group",
            color_discrete_sequence=PALETTE,
        )
        return fig

    # ── Case 4: 2 numeric cols → scatter ────────────────────────────────────
    if len(num_cols) >= 2:
        x_col, y_col = num_cols[0], num_cols[1]
        color_col = cat_cols[0] if cat_cols else None
        fig = px.scatter(
            df,
            x=x_col,
            y=y_col,
            color=color_col,
            title=f"{y_col} vs {x_col}",
            color_discrete_sequence=PALETTE,
        )
        return fig

    # ── Case 5: single numeric column → histogram ────────────────────────────
    if len(num_cols) == 1:
        num = num_cols[0]
        fig = px.histogram(
            df,
            x=num,
            title=f"Distribution of {num}",
            color_discrete_sequence=PALETTE,
        )
        return fig

    return None
