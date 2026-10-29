from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ColumnProfile(BaseModel):
    name: str
    dtype: str
    null_count: int
    null_percentage: float
    unique_count: int
    sample_values: List[Any]
    stats: Optional[Dict[str, Any]] = None

class DatasetProfileResponse(BaseModel):
    dataset_id: str
    filename: str
    row_count: int
    column_count: int
    columns: List[ColumnProfile]
    sample_rows: List[Dict[str, Any]]

class KPICard(BaseModel):
    metric_name: str
    formatted_value: str
    raw_value: Optional[float] = None
    sql_query: str
    insight: str

class AutoKPIResponse(BaseModel):
    dataset_id: str
    kpis: List[KPICard]

class QueryRequest(BaseModel):
    dataset_id: str
    question: str

class AgentQueryResponse(BaseModel):
    dataset_id: str
    question: str
    answer_summary: str
    sql_executed: str
    result_data: List[Dict[str, Any]]
    key_insights: List[str]
    retries_used: int = 0