# Orbit Analytics — Data Analytics Assistant

An autonomous, in-memory conversational data analytics platform powered by **DuckDB**, **FastAPI**, **LangGraph**, and **Groq Cloud**. Upload spreadsheets (`.csv`, `.xlsx`, `.xls`), automatically inspect data quality, and query your data using everyday English.

---

## ⚡ Key Features

* **Zero-Setup Spreadsheet Ingestion:** Drag and drop `.csv`, `.xlsx`, or `.xls` files. Headers are automatically sanitized into clean `snake_case`.
* **Data Quality & Schema Inspector:** Collapsible accordion displaying inferred data types, missing value percentages, and unique value counts before querying.
* **Natural Language to DuckDB SQL:** Translates natural language questions into verified, read-only SQL queries executed in-memory in 8ms–35ms.
* **Self-Healing Query Execution:** Powered by a stateful **LangGraph** workflow that automatically catches SQL execution errors and repairs queries (up to 3 retries).
* **Minimalist Blue & Black UI:** Utilitarian, distraction-free interface built with pure Blue (`#2563eb`) and Deep Black (`#0f172a`).
* **1-Click Productivity Tools:**
  * `⬇ Export CSV` — Downloads current filtered query results.
  * `📋 Copy SQL` — Copies executed DuckDB SQL directly to your clipboard.
* **Dual Execution Modes:** Runs as a standalone browser app with built-in client-side parsing, or connected to the full-stack FastAPI + DuckDB engine.

---

## 🏗️ System Architecture

```
[ User Browser / index.html ]
        │  (Upload Spreadsheet / Ask Natural Language Question)
        ▼
[ FastAPI Backend (/api/v1) ]
   ├── Dataset Profiler ─────► In-Memory Pandas DataFrame (Cleaned headers)
   └── LangGraph Agent  ─────► Isolated DuckDB Sandbox (:memory:)
                                   ▲
                 Groq LPU          │ (Executes read-only SQL in 8ms-35ms)
           (LLaMA-3.3 70B) ────────┘
```

### Self-Healing LangGraph Workflow
1. **`generate_sql`**: Converts schema context and user question into DuckDB SQL.
2. **`execute_sql`**: Runs query in an isolated, read-only in-memory sandbox.
3. **`route_after_execution`**: If DuckDB throws an error (e.g., column mismatch), the error traceback is fed back to the LLM for automated self-correction (max 3 retries).
4. **`synthesize_insights`**: Converts the output rows into an executive summary and actionable takeaways.

---

## 🚀 How to Run

### Mode 1: Instant Browser Mode (No Server Needed)
You can test the application immediately without starting any server:
* Simply double-click **`index.html`** in File Explorer, or run:
  ```powershell
  Start-Process "c:\data-analytics-agent\index.html"
  ```
* Upload any CSV/Excel file, or click *"load sample sales dataset"* to explore immediately.

---

### Mode 2: Full-Stack Mode (Live DuckDB + Groq LLM)

#### 1. Navigate to Project Directory
```powershell
cd c:\data-analytics-agent
```

#### 2. Activate Virtual Environment
```powershell
.\venv\Scripts\Activate.ps1
```

#### 3. Install Dependencies
```powershell
python -m pip install -r requirements.txt
```

#### 4. Configure Environment Variables (`.env`)
Make sure your `.env` file contains your Groq API key:
```dotenv
APP_NAME="Data Analytics Assistant"
UPLOAD_DIR="data/uploads"
GROQ_API_KEY="gsk_your_groq_api_key_here"
LLM_MODEL="llama-3.3-70b-versatile"
```

#### 5. Start the Server
```powershell
python -m uvicorn app.main:app --reload --port 8000
```

#### 6. Open Dashboard
Open your browser and navigate to:
👉 **`http://localhost:8000`**

---

## 📂 Project Structure

```
data-analytics-agent/
├── app/
│   ├── agent/
│   │   ├── prompts.py          # Prompt templates for SQL generation, KPIs & synthesis
│   │   └── workflow.py         # LangGraph state machine & self-healing retry loop
│   ├── api/
│   │   └── routes.py           # FastAPI REST endpoints (/upload, /query, /kpis)
│   ├── core/
│   │   ├── llm_router.py       # Groq client factory with model fallback
│   │   ├── profiler.py         # Ingestion, cleaning & column profiling engine
│   │   └── sandbox.py          # Safe in-memory DuckDB execution sandbox
│   ├── schemas/
│   │   └── models.py           # Pydantic v2 request/response schemas
│   ├── config.py               # Pydantic BaseSettings environment loader
│   ├── index.html              # Frontend user interface (FastAPI mount)
│   └── main.py                 # FastAPI application root & CORS configuration
├── data/
│   └── uploads/                # Local staging directory for uploaded files
├── .env                        # Configuration file (API keys & model options)
├── index.html                  # Standalone client HTML file
├── PROJECT_REPORT.md           # Technical documentation report
├── README.md                   # Project overview & operational guide
└── requirements.txt            # Python dependencies
```

---

## 🛡️ Security & Sandboxing

* **Read-Only Keyword Interceptor:** All generated queries pass through regex validation blocking destructive keywords (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`, `ATTACH`, `DETACH`, `COPY`).
* **Ephemeral Scope:** Queries execute in an isolated `:memory:` connection with zero write access to the host filesystem.
* **Row-Count Truncation:** Output sets are bounded by default row caps to prevent browser memory exhaustion.
* **Privacy by Design:** Raw row records are never sent over external APIs; only column names and statistical blueprints are provided to the LLM (< 350 tokens).

---

## 💡 Example Questions to Ask

When analyzing datasets (like the OECD Healthcare dataset):
* `Compare spending in 2020 across all countries`
* `Rank all countries by life expectancy in the year 2020`
* `Which country achieved the highest life expectancy with the lowest spending in 2020?`
* `Show the growth of USA healthcare spending from 1970 to 2020`
* `What is the average spending and life expectancy for each country?`
