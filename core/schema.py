"""
schema.py — CSV loading and schema inference for CSVWhisperer.
Handles type detection, column sanitization, and building LLM-ready schema descriptions.
"""

import os
import pandas as pd
import re
import io
from typing import Union


def sanitize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sanitize column names for DuckDB compatibility.
    Replaces spaces and special characters with underscores.
    Returns a new dataframe with clean column names and a mapping dict.
    """
    mapping = {}
    new_cols = []
    for col in df.columns:
        clean = re.sub(r"[^\w]", "_", col.strip())
        clean = re.sub(r"_+", "_", clean).strip("_")
        if not clean or clean[0].isdigit():
            clean = "col_" + clean
        # Handle duplicates
        original_clean = clean
        counter = 1
        while clean in mapping.values():
            clean = f"{original_clean}_{counter}"
            counter += 1
        mapping[col] = clean
        new_cols.append(clean)
    df = df.copy()
    df.columns = new_cols
    return df, mapping


def load_csv(file) -> tuple:
    """
    Load a CSV file from a Streamlit UploadedFile or a file path.
    Returns (dataframe, original_filename).
    """
    if hasattr(file, "name"):
        filename = file.name
        content = file.read()
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        df = pd.read_csv(io.StringIO(content))
    else:
        filename = os.path.basename(str(file))
        df = pd.read_csv(file)

    df, _ = sanitize_columns(df)
    return df, filename


def infer_column_type(series: pd.Series) -> str:
    """Return a human-readable type description for a column."""
    dtype = str(series.dtype)
    if "int" in dtype:
        return "integer"
    elif "float" in dtype:
        return "decimal"
    elif "datetime" in dtype:
        return "date/time"
    elif "bool" in dtype:
        return "boolean"
    else:
        # Try to detect if it looks like a date
        sample = series.dropna().head(10)
        try:
            pd.to_datetime(sample, format="mixed")
            return "date (stored as text)"
        except Exception:
            pass
        return "text"


def build_schema_description(df: pd.DataFrame, filename: str = "data.csv") -> str:
    """
    Build a concise schema description for injection into LLM prompts.
    Includes column names, types, sample values, and basic stats.
    """
    lines = [
        f"Dataset: {filename}",
        f"Table name: data",
        f"Rows: {len(df):,}  |  Columns: {len(df.columns)}",
        "",
        "Column definitions:",
    ]

    for col in df.columns:
        series = df[col]
        col_type = infer_column_type(series)
        unique = series.nunique()
        nulls = series.isna().sum()
        samples = series.dropna().head(3).tolist()
        sample_str = ", ".join([repr(str(v)[:40]) for v in samples])

        stats = f"{unique} unique"
        if nulls > 0:
            stats += f", {nulls} nulls"

        lines.append(f"  {col} ({col_type}) — e.g. {sample_str} [{stats}]")

    return "\n".join(lines)


def get_schema_summary(df: pd.DataFrame) -> dict:
    """Return schema as a structured dict for display in the UI."""
    summary = {}
    for col in df.columns:
        series = df[col]
        summary[col] = {
            "type": infer_column_type(series),
            "unique": int(series.nunique()),
            "nulls": int(series.isna().sum()),
            "sample": series.dropna().head(3).tolist(),
        }

    return summary
