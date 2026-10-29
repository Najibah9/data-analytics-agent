import os
import uuid
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException, Body
from app.config import settings
from app.schemas.models import (
    DatasetProfileResponse,
    AutoKPIResponse,
    QueryRequest,
    AgentQueryResponse,
)
from app.core.profiler import load_and_profile_dataset, get_dataset_and_profile
from app.core.sandbox import execute_sql_on_dataset
from app.agent.workflow import run_agent_query, generate_auto_kpis

router = APIRouter(prefix="/api/v1", tags=["Data Analytics Agent"])


@router.post("/datasets/upload", response_model=DatasetProfileResponse)
async def upload_dataset(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".csv", ".xlsx", ".xls"]:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Please upload a .csv or .xlsx file.",
        )

    dataset_id = f"ds_{uuid.uuid4().hex[:8]}"
    saved_path = os.path.join(settings.UPLOAD_DIR, f"{dataset_id}{ext}")

    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        return load_and_profile_dataset(dataset_id, saved_path, file.filename)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to parse dataset: {str(exc)}")


@router.get("/datasets/{dataset_id}/profile", response_model=DatasetProfileResponse)
async def get_profile(dataset_id: str):
    try:
        _, profile = get_dataset_and_profile(dataset_id)
        return profile
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/datasets/{dataset_id}/test-sql")
async def test_sql_sandbox(
    dataset_id: str,
    sql_query: str = Body("SELECT * FROM dataset LIMIT 5", embed=True),
):
    try:
        result = execute_sql_on_dataset(dataset_id, sql_query)
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/datasets/{dataset_id}/kpis", response_model=AutoKPIResponse)
async def auto_discover_kpis(dataset_id: str):
    try:
        return generate_auto_kpis(dataset_id=dataset_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"KPI generation failed: {str(exc)}")


@router.post("/analytics/query", response_model=AgentQueryResponse)
async def ask_analytics_agent(request: QueryRequest):
    try:
        return run_agent_query(
            dataset_id=request.dataset_id,
            question=request.question,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(exc)}")