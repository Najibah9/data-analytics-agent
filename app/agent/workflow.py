import re
import json
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END

from app.core.profiler import get_dataset_and_profile, format_schema_for_llm
from app.core.sandbox import execute_sql_on_dataset, clean_sql_query
from app.core.llm_router import get_llm
from app.agent.prompts import AUTO_KPI_PROMPT, SQL_GENERATION_PROMPT, INSIGHT_SYNTHESIS_PROMPT
from app.schemas.models import KPICard, AutoKPIResponse, AgentQueryResponse


def extract_json_payload(text: str) -> Any:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\}|\[.*\])", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise


class AgentState(TypedDict):
    dataset_id: str
    question: str
    schema_context: str
    sql_query: str
    result_data: List[Dict[str, Any]]
    error: Optional[str]
    retries: int
    answer_summary: str
    key_insights: List[str]


def generate_sql_node(state: AgentState) -> Dict[str, Any]:
    llm = get_llm(temperature=0.0)

    error_context = ""
    if state.get("error"):
        error_context = (
            f"PREVIOUS SQL FAILED:\n{state.get('sql_query')}\n"
            f"DUCKDB ERROR TRACEBACK:\n{state.get('error')}\n"
            f"Fix the SQL query above so it runs without errors on `dataset`."
        )

    prompt = SQL_GENERATION_PROMPT.format(
        schema_context=state["schema_context"],
        question=state["question"],
        error_context=error_context,
    )

    response = llm.invoke(prompt)
    sql = clean_sql_query(str(response.content))
    return {"sql_query": sql}


def execute_sql_node(state: AgentState) -> Dict[str, Any]:
    exec_result = execute_sql_on_dataset(state["dataset_id"], state["sql_query"])

    if exec_result["success"]:
        return {
            "sql_query": exec_result["sql"],
            "result_data": exec_result["data"],
            "error": None,
        }
    else:
        return {
            "sql_query": exec_result["sql"],
            "result_data": [],
            "error": exec_result["error"],
            "retries": state.get("retries", 0) + 1,
        }


def route_after_execution(state: AgentState) -> str:
    if state.get("error") and state.get("retries", 0) < 3:
        return "generate_sql"
    return "synthesize"


def synthesize_insights_node(state: AgentState) -> Dict[str, Any]:
    if state.get("error"):
        return {
            "answer_summary": f"Could not execute query after {state.get('retries', 0)} attempts. Last error: {state['error']}",
            "key_insights": ["Check if the requested columns exist in the uploaded dataset."],
        }

    llm = get_llm(temperature=0.1)
    prompt = INSIGHT_SYNTHESIS_PROMPT.format(
        question=state["question"],
        sql_query=state["sql_query"],
        result_data=json.dumps(state["result_data"][:25], default=str),
    )

    response = llm.invoke(prompt)
    try:
        parsed = extract_json_payload(str(response.content))
        return {
            "answer_summary": parsed.get("answer_summary", str(response.content)),
            "key_insights": parsed.get("key_insights", []),
        }
    except Exception:
        return {
            "answer_summary": str(response.content),
            "key_insights": ["Executed SQL query successfully against dataset."],
        }


workflow_builder = StateGraph(AgentState)
workflow_builder.add_node("generate_sql", generate_sql_node)
workflow_builder.add_node("execute_sql", execute_sql_node)
workflow_builder.add_node("synthesize", synthesize_insights_node)

workflow_builder.set_entry_point("generate_sql")
workflow_builder.add_edge("generate_sql", "execute_sql")
workflow_builder.add_conditional_edges(
    "execute_sql",
    route_after_execution,
    {
        "generate_sql": "generate_sql",
        "synthesize": "synthesize",
    },
)
workflow_builder.add_edge("synthesize", END)

analytics_agent_graph = workflow_builder.compile()


def run_agent_query(dataset_id: str, question: str) -> AgentQueryResponse:
    _, profile = get_dataset_and_profile(dataset_id)
    schema_context = format_schema_for_llm(profile)

    initial_state: AgentState = {
        "dataset_id": dataset_id,
        "question": question,
        "schema_context": schema_context,
        "sql_query": "",
        "result_data": [],
        "error": None,
        "retries": 0,
        "answer_summary": "",
        "key_insights": [],
    }

    final_state = analytics_agent_graph.invoke(initial_state)

    return AgentQueryResponse(
        dataset_id=dataset_id,
        question=question,
        answer_summary=final_state["answer_summary"],
        sql_executed=final_state["sql_query"],
        result_data=final_state["result_data"],
        key_insights=final_state["key_insights"],
        retries_used=final_state.get("retries", 0),
    )


def generate_auto_kpis(dataset_id: str) -> AutoKPIResponse:
    _, profile = get_dataset_and_profile(dataset_id)
    schema_context = format_schema_for_llm(profile)
    llm = get_llm(temperature=0.0)

    prompt = AUTO_KPI_PROMPT.format(schema_context=schema_context)
    response = llm.invoke(prompt)
    kpi_specs = extract_json_payload(str(response.content))

    verified_kpis: List[KPICard] = []
    for item in kpi_specs[:5]:
        sql = item.get("sql_query", "")
        exec_res = execute_sql_on_dataset(dataset_id, sql, max_rows=1)

        raw_val: Optional[float] = None
        formatted_val = "N/A"

        if exec_res["success"] and exec_res["data"]:
            first_row = exec_res["data"][0]
            first_val = next(iter(first_row.values()), None)
            if isinstance(first_val, (int, float)):
                raw_val = float(first_val)
                prefix = item.get("unit_prefix", "")
                suffix = item.get("unit_suffix", "")
                formatted_val = f"{prefix}{raw_val:,.2f}{suffix}".replace(".00", "")
            elif first_val is not None:
                formatted_val = str(first_val)

        verified_kpis.append(
            KPICard(
                metric_name=item.get("metric_name", "Metric"),
                formatted_value=formatted_val,
                raw_value=raw_val,
                sql_query=exec_res["sql"],
                insight=item.get("insight", "Calculated directly from dataset."),
            )
        )

    return AutoKPIResponse(
        dataset_id=dataset_id,
        kpis=verified_kpis,
    )