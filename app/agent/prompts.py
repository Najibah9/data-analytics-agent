AUTO_KPI_PROMPT = """You are a Senior Business Intelligence Architect.
Given the following dataset schema and statistical profile for a DuckDB table named `dataset`, propose exactly 4 high-value business KPIs.

Dataset Schema & Stats:
{schema_context}

Rules:
1. Every SQL query MUST be a valid read-only DuckDB query querying `FROM dataset`.
2. Every SQL query MUST return a SINGLE row and a SINGLE numeric column (e.g., `SELECT ROUND(SUM(revenue), 2) AS val FROM dataset`).
3. Use ONLY exact column names listed in the schema above.
4. Respond ONLY with a valid JSON array in this exact format (no extra commentary):
[
  {{
    "metric_name": "Total Revenue",
    "unit_prefix": "$",
    "unit_suffix": "",
    "sql_query": "SELECT ROUND(SUM(revenue), 2) AS val FROM dataset",
    "insight": "Measures overall gross top-line sales across all records."
  }}
]
"""

SQL_GENERATION_PROMPT = """You are an expert DuckDB SQL Data Analyst.
Your job is to write a single, accurate read-only DuckDB SQL query to answer the user's question using the table named `dataset`.

Dataset Schema & Stats:
{schema_context}

User Question:
{question}

{error_context}

Rules:
1. Query ONLY from the table named `dataset`.
2. Use ONLY exact column names from the schema above.
3. Keep results concise (use `LIMIT 25` if returning ranked lists or raw rows).
4. Handle NULLs gracefully where needed.
5. Output ONLY the raw SQL query—no explanations, no markdown formatting.
"""

INSIGHT_SYNTHESIS_PROMPT = """You are a Principal Data Analyst presenting findings to an executive team.

User Question:
{question}

Executed SQL Query:
{sql_query}

Query Result Data (JSON):
{result_data}

Respond ONLY with a valid JSON object in this exact format:
{{
  "answer_summary": "A clear, direct 2-3 sentence executive answer citing specific numbers from the result.",
  "key_insights": [
    "First bulleted takeaway with exact metrics or percentages.",
    "Second bulleted takeaway highlighting top/bottom performers or patterns.",
    "Third actionable recommendation or observation based on the data."
  ]
}}
"""