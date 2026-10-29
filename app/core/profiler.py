import os
import re
import json
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple
from app.config import settings
from app.schemas.models import DatasetProfileResponse, ColumnProfile

DATASET_CACHE: Dict[str, pd.DataFrame] = {}
PROFILE_CACHE: Dict[str, DatasetProfileResponse] = {}


def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    cleaned_cols = []
    for i, col in enumerate(df.columns):
        col_str = str(col).strip().lower()
        col_str = re.sub(r"[^a-z0-9_]+", "_", col_str)
        col_str = re.sub(r"_+", "_", col_str).strip("_")
        if not col_str or col_str[0].isdigit():
            col_str = f"col_{col_str or i}"
        cleaned_cols.append(col_str)

    seen: Dict[str, int] = {}
    final_cols = []
    for col in cleaned_cols:
        if col in seen:
            seen[col] += 1
            final_cols.append(f"{col}_{seen[col]}")
        else:
            seen[col] = 0
            final_cols.append(col)

    df.columns = final_cols
    return df


def to_python_safe(val: Any) -> Any:
    if pd.isna(val):
        return None
    if isinstance(val, (np.integer, int)):
        return int(val)
    if isinstance(val, (np.floating, float)):
        return round(float(val), 4) if np.isfinite(val) else None
    if isinstance(val, (pd.Timestamp, np.datetime64)):
        return str(val)
    return str(val) if not isinstance(val, (str, bool)) else val


def load_and_profile_dataset(dataset_id: str, file_path: str, original_filename: str) -> DatasetProfileResponse:
    ext = os.path.splitext(original_filename)[1].lower()
    if ext == ".csv":
        try:
            df = pd.read_csv(file_path, encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(file_path, encoding="latin1")
    elif ext in [".xlsx", ".xls"]:
        df = pd.read_excel(file_path)
    else:
        raise ValueError(f"Unsupported file format '{ext}'. Please upload a .csv or .xlsx file.")

    df = clean_column_names(df)

    for col in df.select_dtypes(include=["object"]).columns:
        if "date" in col or "time" in col:
            try:
                df[col] = pd.to_datetime(df[col])
            except Exception:
                pass

    row_count, col_count = df.shape
    column_profiles = []

    for col in df.columns:
        series = df[col]
        null_count = int(series.isna().sum())
        null_pct = round((null_count / row_count) * 100, 2) if row_count > 0 else 0.0
        unique_count = int(series.nunique(dropna=True))
        non_null_samples = [to_python_safe(v) for v in series.dropna().unique()[:3]]

        stats = None
        if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
            clean_num = series.dropna()
            if len(clean_num) > 0:
                stats = {
                    "min": to_python_safe(clean_num.min()),
                    "max": to_python_safe(clean_num.max()),
                    "mean": to_python_safe(clean_num.mean()),
                    "median": to_python_safe(clean_num.median()),
                    "sum": to_python_safe(clean_num.sum()),
                }

        column_profiles.append(
            ColumnProfile(
                name=col,
                dtype=str(series.dtype),
                null_count=null_count,
                null_percentage=null_pct,
                unique_count=unique_count,
                sample_values=non_null_samples,
                stats=stats,
            )
        )

    sample_df = df.head(5)
    sample_rows = [
        {col: to_python_safe(row[col]) for col in sample_df.columns}
        for _, row in sample_df.iterrows()
    ]

    profile = DatasetProfileResponse(
        dataset_id=dataset_id,
        filename=original_filename,
        row_count=row_count,
        column_count=col_count,
        columns=column_profiles,
        sample_rows=sample_rows,
    )

    DATASET_CACHE[dataset_id] = df
    PROFILE_CACHE[dataset_id] = profile
    return profile


def get_dataset_and_profile(dataset_id: str) -> Tuple[pd.DataFrame, DatasetProfileResponse]:
    if dataset_id not in DATASET_CACHE or dataset_id not in PROFILE_CACHE:
        for ext in [".csv", ".xlsx", ".xls"]:
            candidate = os.path.join(settings.UPLOAD_DIR, f"{dataset_id}{ext}")
            if os.path.exists(candidate):
                load_and_profile_dataset(dataset_id, candidate, f"{dataset_id}{ext}")
                return DATASET_CACHE[dataset_id], PROFILE_CACHE[dataset_id]
        raise KeyError(f"Dataset '{dataset_id}' not found. Please upload the file first.")
    return DATASET_CACHE[dataset_id], PROFILE_CACHE[dataset_id]


def format_schema_for_llm(profile: DatasetProfileResponse) -> str:
    lines = [
        "Table Name: dataset",
        f"Total Rows: {profile.row_count} | Total Columns: {profile.column_count}",
        "Columns:",
    ]
    for col in profile.columns:
        stat_str = f" | Stats: {json.dumps(col.stats)}" if col.stats else ""
        lines.append(
            f"  - {col.name} ({col.dtype}): {col.unique_count} unique, "
            f"{col.null_percentage}% null, samples={col.sample_values}{stat_str}"
        )
    return "\n".join(lines)