# Z.AI — Economic Empowerment & Decision Intelligence

> **Hackathon Domain**: AI for Economy
> **Project**: Z.AI — BNPL (Buy Now, Pay Later) Advisory for SMEs
> **Stack**: Python 3.11+ · FastAPI · SQLite · ILMU Anthropic API (Claude)
> **Status**: ✅ Functional end-to-end (Backend + Frontend)

---

## 1. What This System Does

Z.AI is an AI-powered financial advisory platform that helps SMEs (Small & Medium Enterprises) make data-driven decisions on whether to use **BNPL (Buy Now, Pay Later)** or **traditional financing** for business purchases.

### Core Capabilities
- **Financial Data Ingestion** — Upload CSV, JSON, or PDF financial documents
- **Automated Financial Health Analysis** — 20+ metrics calculated automatically
- **AI-Powered Decision Engine** — Uses Claude (via ILMU Anthropic API) to evaluate purchases and recommend BNPL vs traditional financing
- **Impact Quantification** — Estimated interest savings, cash flow improvements, ROI projections
- **Interactive Dashboard** — Real-time financial health visualization with AI health score
- **Audit Trail** — Full recommendation history with decision rationale logging

---

## 2. Project Structure

```
z-ai/
├── backend/                        # ← Python FastAPI backend
│   ├── app/
│   │   ├── main.py                 # FastAPI entry point
│   │   ├── __init__.py
│   │   ├── api/
│   │   │   ├── __init__.py         # Router exports
│   │   │   └── endpoints/
│   │   │       ├── __init__.py
│   │   │       ├── health.py       # Health check endpoint
│   │   │       ├── companies.py    # Company CRUD
│   │   │       ├── sme.py          # SME profile + file upload + metrics
│   │   │       ├── advisor.py      # BNPL evaluation (AI-powered)
│   │   │       ├── dashboard.py    # Dashboard data aggregation
│   │   │       ├── recommendations.py  # Recommendation history
│   │   │       └── transactions.py # Transaction management
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py           # Settings (env vars, API keys)
│   │   │   └── z_ai_client.py      # ILMU/Anthropic API client wrapper
│   │   ├── db/
│   │   │   ├── __init__.py         # DB exports (engine, Base, SessionLocal)
│   │   │   ├── base.py             # SQLAlchemy Base
│   │   │   ├── database.py         # Engine + session factory
│   │   │   └── session.py          # Session dependency
│   │   ├── models/
│   │   │   ├── __init__.py         # Model exports
│   │   │   ├── financial.py        # CompanyProfile, Transaction, etc.
│   │   │   ├── financial_record.py
│   │   │   └── sme_profile.py
│   │   ├── schemas/
│   │   │   ├── __init__.py         # Pydantic schemas
│   │   │   ├── decision_schema.py
│   │   │   ├── file_upload.py
│   │   │   └── sme_schema.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── glm_integration.py  # GLM client for recommendations
│   │   │   ├── decision_engine.py  # Core decision logic
│   │   │   ├── business_logic.py   # Financial calculations
│   │   │   ├── data_processor.py   # CSV/JSON/PDF parsing
│   │   │   ├── document_processor.py
│   │   │   └── financial_metrics.py
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── helpers.py
│   ├── tests/
│   │   └── test_integration.py
│   ├── .env                        # API keys & config (DO NOT COMMIT)
│   ├── .gitignore
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── .dockerignore
│
├── frontend/                       # ← Single-page app (HTML/CSS/JS)
│   ├── index.html                  # Main HTML (dark premium theme)
│   ├── styles.css                  # Glassmorphism design system
│   └── app.js                      # Frontend logic (API integration)
│
└── context.md                      # ← This file (project documentation)
```

---

## 3. Step-by-Step: How to Run

### Prerequisites
- **Python 3.11+** installed ([download](https://www.python.org/downloads/))
- **pip** (comes with Python)
- A terminal (Command Prompt, PowerShell, or VS Code terminal)

### Step 1: Open Terminal
Open your terminal and navigate to the **backend** folder:
```bash
cd "c:\Users\mizn\Desktop\UM Hackathon\z-ai\backend"
```

### Step 2: Create Virtual Environment (Recommended)
```bash
python -m venv venv
```

### Step 3: Activate Virtual Environment
**Windows (PowerShell):**
```bash
.\venv\Scripts\Activate
```
**Windows (Command Prompt):**
```bash
venv\Scripts\activate.bat
```

### Step 4: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 5: Run the Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 6: Open in Browser

| URL | What You'll See |
|-----|-----------------|
| http://localhost:8000/app | 🎨 **Frontend Dashboard** — Main UI with all features |
| http://localhost:8000/docs | 📚 **Swagger API Docs** — Interactive API testing |
| http://localhost:8000/redoc | 📖 **ReDoc** — Clean API documentation |
| http://localhost:8000/ | 🔗 **API Root** — JSON info about the system |

### Step 7: Stop the Server
Press `Ctrl + C` in the terminal.

---

### Quick Run (Copy-Paste)
If you already have dependencies installed, just run these 2 commands:
```bash
cd "c:\Users\mizn\Desktop\UM Hackathon\z-ai\backend"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 4. Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Frontend (SPA)                     │
│         /frontend/index.html + styles.css + app.js  │
│         Served at /app via FastAPI                   │
└──────────────────┬──────────────────────────────────┘
                   │ HTTP (fetch)
                   ▼
┌─────────────────────────────────────────────────────┐
│              FastAPI Backend (:8000)                  │
│                                                      │
│  /health              → Health check                 │
│  /api/v1/sme/*        → SME profiles, file upload    │
│  /api/v1/advisor/*    → BNPL evaluation (AI)         │
│  /api/v1/dashboard/*  → Dashboard aggregation        │
│  /api/v1/companies/*  → Company CRUD                 │
│  /api/v1/recommendations/* → History                 │
│  /api/v1/transactions/*    → Transactions            │
└──────────┬──────────────────────┬───────────────────┘
           │                      │
           ▼                      ▼
┌──────────────────┐   ┌──────────────────────────────┐
│   SQLite DB      │   │   ILMU Anthropic API         │
│   (z_ai_local.db)│   │   https://api.ilmu.ai/       │
│                  │   │   anthropic                   │
│   Tables:        │   │                              │
│   - companies    │   │   Model: claude-sonnet-4     │
│   - transactions │   │   Used for: BNPL decisions   │
│   - documents    │   │                              │
│   - recommendations│ │                              │
│   - reports      │   │                              │
└──────────────────┘   └──────────────────────────────┘
```

---

## 5. AI Integration (Critical Path)

### How it works
1. SME submits a purchase evaluation request (amount, purpose, financial context)
2. `advisor.py` endpoint receives the request
3. `z_ai_client.py` builds a structured prompt with the company's financial data
4. Prompt is sent to **ILMU Anthropic API** (`https://api.ilmu.ai/anthropic`) using Claude
5. Claude analyzes the financial situation and returns a JSON recommendation
6. Response is parsed into: decision (approve/defer/reject), financing type (bnpl/traditional/cash), confidence score, explanation, and impact metrics
7. Result is stored in the database and returned to the frontend

### Key Files
| File | Role |
|------|------|
| `backend/app/core/config.py` | API URL, key, model, timeout settings |
| `backend/app/core/z_ai_client.py` | Full Anthropic API client with prompt building and response parsing |
| `backend/app/services/glm_integration.py` | Higher-level GLM client for structured recommendation requests |
| `backend/app/services/decision_engine.py` | Core decision logic combining financial metrics + AI |

### API Configuration (in `backend/.env`)
```env
ZAI_GLM_API_URL=https://api.ilmu.ai/anthropic
ZAI_GLM_API_KEY=sk-2e43e103ba457c433fc78b5e59d25f644dd68128d84f40d0
ZAI_GLM_MODEL=claude-sonnet-4-20250514
ZAI_GLM_TIMEOUT=60
```

---

## 6. API Endpoints

### Health
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |

### SME Profiles
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/sme/register` | Register new SME |
| GET | `/api/v1/sme/{sme_id}` | Get SME profile |
| POST | `/api/v1/sme/{sme_id}/upload-financials` | Upload CSV/JSON/PDF financial data |
| GET | `/api/v1/sme/{sme_id}/metrics` | Get calculated financial metrics |

### BNPL Advisor (AI-Powered)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/advisor/evaluate` | Evaluate a purchase using AI |
| GET | `/api/v1/advisor/history/{sme_id}` | Get evaluation history |

### Dashboard
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/dashboard/overview/{company_id}` | Dashboard overview with KPIs |
| GET | `/api/v1/dashboard/forecast/{company_id}` | Cash flow forecast |
| GET | `/api/v1/dashboard/benchmarks/{company_id}` | Industry benchmarks |

### Companies
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/companies` | Create company |
| GET | `/api/v1/companies/{company_id}` | Get company |
| GET | `/api/v1/companies` | List companies |
| PATCH | `/api/v1/companies/{company_id}` | Update company |

### Recommendations
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/recommendations/analyze` | Get GLM recommendation |
| GET | `/api/v1/recommendations/{id}` | Get recommendation |
| GET | `/api/v1/recommendations/company/{company_id}` | List recommendations |
| POST | `/api/v1/recommendations/{id}/approve` | Approve recommendation |

### Transactions
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/transactions` | Create transaction |
| POST | `/api/v1/transactions/bulk` | Bulk upload |
| GET | `/api/v1/transactions/company/{company_id}` | Get company transactions |

---

## 7. Database Models

| Model | Table | Purpose |
|-------|-------|---------|
| `CompanyProfile` | `company_profiles` | SME company info, industry, credit score, annual revenue |
| `Transaction` | `transactions` | Financial transaction records (sales, expenses) |
| `FinancialDocument` | `financial_documents` | Uploaded documents (CSV, PDF, JSON) |
| `BNPLRecommendation` | `bnpl_recommendations` | AI recommendation history with decision rationale |
| `AnalysisReport` | `analysis_reports` | Comprehensive financial analysis reports |

---

## 8. Frontend

The frontend is a **single-page application** served at `/app` with a premium dark theme:

| View | What It Does |
|------|-------------|
| **Dashboard** | AI Health Score, Revenue, Operating Cash Flow, Net Profit Margin, EAPR Alert |
| **BNPL Evaluator** | Enter purchase details → get AI recommendation (approve/defer/reject) |
| **Upload Data** | Drag-and-drop CSV/JSON/PDF upload for financial data ingestion |
| **Transactions** | View transaction history |
| **Forecast** | Cash flow forecasting visualization |
| **Benchmarks** | Industry comparison metrics |

### Design
- Dark navy theme (`#0a0e1a` background)
- Glassmorphism cards with backdrop blur
- Gradient accents (indigo → violet)
- Animated KPI cards and confidence bars
- Google Fonts: Inter
- Fully responsive

---

## 9. Dependencies

```
fastapi==0.104.1           # Web framework
uvicorn[standard]==0.24.0  # ASGI server
sqlalchemy==2.0.23         # ORM
pydantic==2.5.0            # Data validation
pydantic-settings==2.1.0   # Settings management
python-dotenv==1.0.0       # .env loading
httpx==0.25.2              # Async HTTP client (for AI API)
pandas==2.1.3              # Data processing
openpyxl==3.11.0           # Excel file support
PyPDF2==4.0.1              # PDF parsing
aiofiles==23.2.1           # Async file I/O
python-multipart==0.0.6    # File upload support
python-json-logger==2.0.7  # Structured logging
```

---

## 10. Security Notes

- API keys stored in `.env` (gitignored)
- JWT/OAuth ready (SECRET_KEY configured)
- CORS restricted to localhost origins
- Database credentials isolated in environment variables
- Never commit `.env` to version control

---

## 11. Development Log

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1: Cleanup | ✅ Done | Removed redundant folders (`bnpl-advisor-backend/`, `Test.py`, 12 markdown docs, `__pycache__/`) |
| Phase 2: Backend | ✅ Done | FastAPI with all endpoints, Z.AI GLM client, SQLite database, demo data seeding |
| Phase 3: Frontend | ✅ Done | Premium dark-themed SPA with dashboard, BNPL evaluator, file upload, transactions, forecast, benchmarks |
| Phase 4: AI Integration | ✅ Done | ILMU Anthropic API configured with Claude claude-sonnet-4-20250514 model, API key set |
| Phase 5: Restructure | ✅ Done | Separated into `backend/` and `frontend/` folders for clean project organization |

---

**Built for the UM Hackathon — Economic Empowerment Track**
