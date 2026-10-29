import re
import duckdb
import pandas as pd
from typing import Dict, Any
from app.core.profiler import get_dataset_and_profile, to_python_safe

FORBIDDEN_SQL_PATTERNS = re.compile(
    r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|TRUNCATE|CREATE|REPLACE|ATTACH|DETACH|COPY|EXPORT)\b",
    re.IGNORECASE,
)


def clean_sql_query(raw_sql: str) -> str:
    cleaned = raw_sql.strip()
    cleaned = re.sub(r"^```(?:sql|duckdb)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip().rstrip(";")


def execute_sql_on_dataset(dataset_id: str, sql_query: str, max_rows: int = 100) -> Dict[str, Any]:
    df, _ = get_dataset_and_profile(dataset_id)
    cleaned_sql = clean_sql_query(sql_query)

    if FORBIDDEN_SQL_PATTERNS.search(cleaned_sql):
        return {
            "success": False,
            "sql": cleaned_sql,
            "data": [],
            "error": "Security Error: Only read-only SELECT/WITH queries are allowed in the sandbox.",
        }

    try:
        con = duckdb.connect(database=":memory:")
        con.register("dataset", df)
        result_df: pd.DataFrame = con.execute(cleaned_sql).df()
        con.close()

        truncated_df = result_df.head(max_rows)
        records = [
            {str(col): to_python_safe(row[col]) for col in truncated_df.columns}
            for _, row in truncated_df.iterrows()
        ]

        return {
            "success": True,
            "sql": cleaned_sql,
            "row_count": len(records),
            "columns": list(truncated_df.columns),
            "data": records,
            "error": None,
        }
    except Exception as exc:
        return {
            "success": False,
            "sql": cleaned_sql,
            "data": [],
            "error": str(exc),
        }