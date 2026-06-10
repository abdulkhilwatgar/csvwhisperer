"""
executor.py — DuckDB query execution engine for CSVWhisperer.
Registers the uploaded dataframe as an in-memory table and runs SQL against it.
"""

import duckdb
import pandas as pd
from typing import Union


class QueryExecutor:
    """
    Wraps a DuckDB in-memory connection with the uploaded CSV registered as 'data'.
    Handles query execution, error capture, and result formatting.
    """

    def __init__(self, df: pd.DataFrame):
        self.conn = duckdb.connect(database=":memory:")
        self.conn.register("data", df)
        self._df = df

    def execute(self, sql: str) -> tuple:
        """
        Execute a SQL query.
        Returns (success: bool, result: DataFrame | error_message: str).
        """
        try:
            result = self.conn.execute(sql).df()
            return True, result
        except Exception as e:
            return False, str(e)

    def get_sample(self, n: int = 5) -> pd.DataFrame:
        """Return the first n rows of the dataset."""
        return self._df.head(n)

    def get_row_count(self) -> int:
        return len(self._df)

    def get_column_names(self) -> list:
        return list(self._df.columns)

    def close(self):
        self.conn.close()
