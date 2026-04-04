# Enterprise Onboarding Agent

An AI-powered customer onboarding automation agent built with **Pydantic AI + FastMCP**, demonstrating how autonomous agents can streamline enterprise SaaS onboarding workflows using native tool calling.

## 🎯 Overview

This agent automates the customer journey from **Sales → Contract → Invoice → Provisioning**, featuring:

- **Agentic Architecture**: The LLM reasons and decides which tools to call — no hardcoded state machine or graph
- **Native Tool Calling**: 16 tools registered via `@agent.tool` decorators; the agent orchestrates them autonomously
- **MCP-Style Extensibility**: Every tool is mirrored as a FastMCP server definition for future extraction to standalone services
- **Multi-System Integration**: Salesforce, CLM, NetSuite, currency conversion (live API), and SaaS provisioning
- **Live Currency Conversion**: Historical and latest USD/CAD exchange rates via Frankfurter API (ECB data) for financial alignment checks
- **Financial Alignment Detection**: Automated comparison of opportunity deal values vs invoice totals across currencies (2% threshold)
- **Configurable Error Simulation**: Auth failures, permission errors, validation errors, rate limits, server errors with adjustable probabilities
- **Comprehensive Error Handling**: API errors are properly caught, recorded, and influence decisions
- **Proactive Notifications**: Slack and email alerts to stakeholders
- **Report Generation**: HTML emails, Markdown reports, JSON audit logs
- **Dual Observability**: Pydantic Logfire + LangSmith tracing (both opt-in), structured JSON logging, audit trails

## 🎥 Video Demo Walkthrough

Watch the full solution walkthrough here:

👉 **[View Demo Video](https://drive.google.com/file/d/1-ztLnzh89_dahqyzBxzX045lJkn83hNs/view?usp=sharing)**


## 🏗️ Architecture

### Agentic Architecture

Unlike a traditional state machine or workflow engine, this agent uses **native LLM tool calling**. The LLM receives a system prompt with business rules and a set of tools, then autonomously reasons through the workflow:

```
LLM Agent (Pydantic AI)
  ├── Fetch Tools (6)      → Salesforce, CLM, NetSuite
  ├── Validation Tools (2) → Business rules, Financial alignment
  ├── Currency Tool (1)    → Historical/live exchange rates (Frankfurter API)
  ├── Provisioning (1)     → SaaS tenant creation
  └── Notification Tools (6) → Slack, Email, Welcome
```

The agent decides **what to call, in what order, and how many times** based on tool results. Adding a new capability means registering a new `@agent.tool` — zero changes to orchestration logic.

Each tool is also defined as a **FastMCP server** in `app/mcp/`, ready for extraction to standalone MCP services.

### Architecture Diagram

```mermaid
---
config:
  theme: base
  themeVariables:
    background: '#ffffff'
    primaryColor: '#e8f0ff'
    primaryBorderColor: '#5b8def'
    lineColor: '#6b7a90'
    primaryTextColor: '#1f2937'
    clusterBkg: '#f7f9fc'
    clusterBorder: '#c7d0e0'
    fontSize: 13px
  flowchart:
    curve: basis
    nodeSpacing: 30
    rankSpacing: 40
---
flowchart LR
 subgraph TRIGGERS["1 · TRIGGER LAYER — How onboarding starts"]
    direction LR
        WH["fa:fa-bolt Salesforce Webhook\n(real-time)"]
        API["fa:fa-plug REST API / Manual\n(on-demand)"]
        BATCH["fa:fa-clock Scheduled Batch\n(nightly / periodic)"]
  end
 subgraph PARALLEL["Parallel fetches after account is loaded"]
    direction LR
        F_USER["fetch_salesforce\n_user\n(account owner)"]
        F_OPP["fetch_salesforce\n_opportunity\n(deal details)"]
        F_CON["fetch_salesforce\n_contract\n(SF contract)"]
        F_CLM["fetch_clm\n_contract\n(CLM system)"]
        F_INV["fetch_netsuite\n_invoice\n(billing data)"]
  end
 subgraph FETCH["Step 1 · GATHER DATA — fetch from source systems"]
    direction TB
        F_ACC["fetch_salesforce_account\n(primary record)"]
        PARALLEL
  end
 subgraph VALIDATE["Step 2 · VALIDATE — business rules + financial checks"]
    direction TB
        V_BIZ["validate_business_rules\n(5 domains · reads from deps)"]
        V_FIN["check_financial_alignment\n(cross-system · 2% threshold)"]
        V_CUR["convert_currency\n(historical ECB rate\nvia Frankfurter API)"]
  end
 subgraph ACT_B["BLOCK path — stop onboarding"]
    direction LR
        N_BLK["notify_blocked\n(Slack alert)"]
        N_FIN["notify_finance_overdue\n(finance team alert)"]
  end
 subgraph ACT_E["ESCALATE path — flag for review"]
        N_ESC["notify_escalation\n(CS team review)"]
  end
 subgraph ACT_P["PROCEED path — complete onboarding"]
    direction LR
        PROV["provision_account\n(activate services)"]
        N_SUC["notify_success\n(Slack confirmation)"]
        N_EMAIL["send_email\n(CS team summary)"]
        N_WEL["send_customer_welcome\n(welcome email)"]
  end
 subgraph AGENT["2 · PYDANTIC AI AGENT — 16 tools via @agent.tool"]
        ENTRY["Initialize OnboardingDeps\n(account_id, correlation_id)"]
        FETCH
        VALIDATE
        DECIDE{"LLM DECISION POINT\nbased on tool results\n(errors / warnings / clear)"}
        ACT_B
        ACT_E
        ACT_P
        OUTPUT["OnboardingResult\n(Pydantic structured output)"]
  end
 subgraph REPORTS["3 · GENERATED REPORTS — post-run artifacts"]
    direction LR
        R_MD["fa:fa-file-text Markdown\nReport"]
        R_HTML["fa:fa-envelope HTML\nEmail"]
        R_JSON["fa:fa-database JSON\nAudit Log"]
  end
 subgraph OBS["4 · OBSERVABILITY — opt-in tracing"]
    direction LR
        LOGFIRE["Pydantic Logfire\n(native tracing)"]
        LANGSMITH["LangSmith\n(OTEL bridge)"]
  end
 subgraph MCP["5 · FASTMCP SERVERS — app/mcp/"]
    direction TB
        MCP_SF["salesforce_server\n(accounts, users,\nopps, contracts)"]
        MCP_CLM["clm_server\n(contract lifecycle)"]
        MCP_NS["netsuite_server\n(invoices, payments)"]
        MCP_CUR["currency_server\n(FX conversion)"]
        MCP_PRV["provisioning_server\n(account activation)"]
        MCP_NOT["notifications_server\n(Slack, email)"]
        MCP_VAL["validation_server\n(business rules)"]
  end
 subgraph EXT["6 · EXTERNAL SYSTEMS — third-party integrations"]
    direction TB
        SF["fa:fa-cloud Salesforce CRM\n(Account · Opportunity\nUser · Contract)"]
        CLM_EXT["fa:fa-file-contract CLM\n(Contract Lifecycle Mgmt)"]
        NS["fa:fa-calculator NetSuite ERP\n(Invoices · Payments)"]
        FX["fa:fa-exchange Frankfurter API\n(ECB exchange rates)"]
        SLACK["fa:fa-comments Slack\n(Notifications)"]
        EMAIL_EXT["fa:fa-envelope Email\n(Welcome · CS alerts)"]
  end
    TRIGGERS -- account_id + correlation_id --> ENTRY
    ENTRY --> F_ACC
    F_ACC -- OwnerId --> F_USER
    F_ACC --> F_OPP & F_CON & F_CLM & F_INV
    FETCH --> V_BIZ
    V_BIZ --> V_FIN
    V_FIN -. if currencies differ .-> V_CUR
    VALIDATE --> DECIDE
    DECIDE -- errors or\nviolations --> ACT_B
    DECIDE -- "warnings only\n(non-critical)" --> ACT_E
    DECIDE -- all clear\n(no issues) --> ACT_P
    ACT_B --> OUTPUT
    ACT_E --> OUTPUT
    ACT_P --> OUTPUT
    OUTPUT --> REPORTS
    AGENT -.-> OBS
    AGENT -. every tool mirrored as FastMCP server .-> MCP
    MCP --> EXT

     WH:::trigger
     API:::trigger
     BATCH:::trigger
     F_USER:::fetch
     F_OPP:::fetch
     F_CON:::fetch
     F_CLM:::fetch
     F_INV:::fetch
     F_ACC:::fetch
     V_BIZ:::validate
     V_FIN:::validate
     V_CUR:::validate
     N_BLK:::block
     N_FIN:::block
     N_ESC:::escalate
     PROV:::proceed
     N_SUC:::proceed
     N_EMAIL:::proceed
     N_WEL:::proceed
     ENTRY:::entry
     DECIDE:::decision
     OUTPUT:::output
     R_MD:::report
     R_HTML:::report
     R_JSON:::report
     LOGFIRE:::obs
     LANGSMITH:::obs
     MCP_SF:::mcp
     MCP_CLM:::mcp
     MCP_NS:::mcp
     MCP_CUR:::mcp
     MCP_PRV:::mcp
     MCP_NOT:::mcp
     MCP_VAL:::mcp
     SF:::ext
     CLM_EXT:::ext
     NS:::ext
     FX:::ext
     SLACK:::ext
     EMAIL_EXT:::ext
    classDef trigger   fill:#fff3cd,stroke:#d4a017,stroke-width:2px,color:#1f2937
    classDef entry     fill:#e8f0ff,stroke:#5b8def,stroke-width:2px,color:#1f2937
    classDef fetch     fill:#e6f7ee,stroke:#2e9d69,stroke-width:1px,color:#1f2937
    classDef validate  fill:#f1ecff,stroke:#8b7cf6,stroke-width:1px,color:#1f2937
    classDef decision  fill:#fff7db,stroke:#d4a017,stroke-width:2px,color:#1f2937
    classDef block     fill:#fde8e8,stroke:#e5484d,stroke-width:1px,color:#1f2937
    classDef escalate  fill:#fff3cd,stroke:#d4a017,stroke-width:1px,color:#1f2937
    classDef proceed   fill:#e6f7ee,stroke:#2e9d69,stroke-width:1px,color:#1f2937
    classDef output    fill:#e8f0ff,stroke:#5b8def,stroke-width:2px,color:#1f2937
    classDef report    fill:#f5f5f5,stroke:#999,stroke-width:1px,color:#1f2937
    classDef mcp       fill:#f0f0f0,stroke:#888,stroke-width:1px,stroke-dasharray:5 5,color:#555
    classDef ext       fill:#dbeafe,stroke:#3b82f6,stroke-width:1px,color:#1f2937
    classDef obs       fill:#fef3c7,stroke:#d97706,stroke-width:1px,stroke-dasharray:5 5,color:#92400e
```

### Decision Logic

The agent makes decisions based on three factors:

1. **API Errors** (`api_errors`): System integration failures (auth, rate limits, server errors) → **BLOCK**
2. **Violations** (`violations`): Business rule failures (missing data, invalid states) → **BLOCK**
3. **Warnings** (`warnings`): Non-critical issues (missing optional fields, FX gaps, underpayment) → **ESCALATE**
4. **All Clear**: No errors, violations, or warnings → **PROCEED**

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- OpenAI API key (recommended; falls back to Ollama local model without it)
- LangSmith API key (optional — for tracing)
- Logfire token (optional — for Pydantic AI native tracing)

## 📦 Installation

### Option 1: Using `uv` (Recommended - Faster)

[`uv`](https://docs.astral.sh/uv/) is a fast Python package installer and environment manager.

**macOS / Linux**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell)**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Project setup**
```bash
# Initialize project and virtual environment
uv init

# Install dependencies
uv add -r requirements.txt

# Environment variables
cp .env.example .env
# Edit .env with your API keys
```

---

### Option 2: Using pip (Standard Python)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# macOS / Linux
source venv/bin/activate
# Windows
venv\Scripts\activate
```

```bash
# Install dependencies
pip install -r requirements.txt

# Environment variables
cp .env.example .env
# Edit .env with your API keys
```

---

### Environment Variables

Create a `.env` file in the project root (or copy from `.env.example`):

```env
# OpenAI (required for GPT-4o; falls back to Ollama if unset)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# LangSmith tracing (optional)
LANGCHAIN_API_KEY=ls-...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=onboarding-agent
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com

# Logfire tracing (optional — Pydantic AI native)
LOGFIRE_TOKEN=
LOGFIRE_ENVIRONMENT=development

# Logging
LOG_DIR=logs

# Environment
ENVIRONMENT=development
```

> **Note**: The agent works without tracing keys. OpenAI is recommended for best results; without it, the agent falls back to Ollama (requires a local Ollama server). Currency conversion uses the free Frankfurter API (ECB rates) — no key needed.

---

## ▶️ Running the Application

### Primary Entry Point (Recommended)

The application is designed to be started via `main.py`, which embeds the Uvicorn server programmatically.

```bash
# Using uv
uv run main.py
```

```bash
# Using standard Python
python main.py
```

The server will start on:

```
http://localhost:8000
```

Health check:
```
GET /health
```

Interactive API docs:
```
http://localhost:8000/docs
```

---

### Alternative: Uvicorn CLI (Optional)

If you prefer to run the server using the Uvicorn CLI:

```bash
uvicorn main:app --reload
```

> **Note**: `uvicorn` is still required as a dependency even when running `python main.py`, since it is imported programmatically.

---

## 📋 Demo Scenarios

### Normal Scenarios

| Account ID | Scenario | Expected Decision |
|------------|----------|-------------------|
| ACME-001 | Happy Path — Full Success | ✅ PROCEED |
| BETA-002 | Opportunity Not Won | 🚫 BLOCK |
| GAMMA-003 | Overdue Invoice | ⚠️ ESCALATE |
| DELETED-004 | Deleted Account | 🚫 BLOCK |
| MISSING-999 | Account Not Found | 🚫 BLOCK |
| FOREX-005 | FX Invoice Mismatch (CAD vs USD) | ⚠️ ESCALATE |
| PARTIAL-006 | Partial Payment Gap (5% underpayment) | ⚠️ ESCALATE |

**FOREX-005** demonstrates historical currency conversion: the invoice is in CAD ($145,000) while the opportunity is in USD ($100,000). The conversion uses the ECB rate from the invoice date (2024-03-01), not today's rate, ensuring financial accuracy. The resulting gap exceeds the 2% threshold, triggering escalation.

**PARTIAL-006** demonstrates underpayment detection: $190,000 paid of a $200,000 invoice (5% gap) exceeds the 2% financial alignment threshold.

### Error Simulation

Enable configurable error injection to test resilience:

```bash
# Enable 100% auth error rate
POST /demo/enable-random-errors?auth_rate=1.0

# Enable mixed error rates
POST /demo/enable-random-errors?auth_rate=0.1&rate_limit_rate=0.2&server_error_rate=0.05

# Check current simulator status
GET /demo/error-simulator-status

# Disable error simulation
POST /demo/disable-random-errors
```

| Error Type | Description | HTTP Code |
|------------|-------------|-----------|
| `auth_rate` | Authentication failures | 401 |
| `validation_rate` | Validation errors | 400 |
| `rate_limit_rate` | Rate limit exceeded | 429 |
| `server_error_rate` | Server errors | 500 |

## 🔌 API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/webhook/onboarding` | Main onboarding trigger |
| POST | `/debug/onboarding` | Test with custom data |

### Demo Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/demo/scenarios` | List all scenarios |
| POST | `/demo/run/{account_id}` | Run specific scenario |
| POST | `/demo/run-all` | Run all scenarios |
| POST | `/demo/run-with-reports` | Run all with report generation |

### Error Simulation Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/demo/enable-random-errors` | Enable error injection with configurable rates |
| POST | `/demo/disable-random-errors` | Disable error injection |
| GET | `/demo/error-simulator-status` | Check current simulator configuration |

### Report Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/demo/reports` | List generated reports |
| GET | `/demo/reports/{filename}` | Get report content (HTML returned as response body) |
| GET | `/demo/reports/{filename}/download` | Download report |

## 🔧 Error Handling Architecture

```mermaid
%%{
init: {
  "theme": "base",
  "themeVariables": {
    "background": "#ffffff",
    "primaryColor": "#f7f9fc",
    "primaryBorderColor": "#c7d0e0",
    "lineColor": "#6b7a90",
    "primaryTextColor": "#1f2937",
    "clusterBkg": "#f2f5fb",
    "clusterBorder": "#d6deeb",
    "fontSize": "14px"
  }
}
}%%

flowchart TD

%% ------------ INTEGRATIONS ------------
subgraph INT["🔌 Integration Layer"]
SF_CALL["Salesforce API Call"]
CLM_CALL["CLM API Call"]
NS_CALL["NetSuite API Call"]
end

%% ------------ ERROR SIMULATOR ------------
subgraph SIML["🎲 Error Simulation Layer"]
SIM["ERROR_SIMULATOR<br/>maybe_raise_error"]

AUTH["🔐 Auth Error"]
RATE["⏳ Rate Limit"]
VAL["⚠️ Validation Error"]
SRV["💥 Server Error"]
end

%% ------------ ERROR HANDLING ------------
subgraph ERR["🛡️ Error Handling Pipeline"]
CATCH_SPECIFIC["Catch Typed Errors"]
CATCH_API["Catch Generic APIError"]
PAYLOAD["Create Structured Error Payload"]
end

%% ------------ STATE ------------
subgraph STATE["🧠 Agent State"]
API_ERRORS["api_errors"]
VIOLATIONS["violations"]
DECISION{"Decision Engine"}
end

BLOCK["🚫 BLOCK"]

%% FLOWS
SF_CALL --> SIM
CLM_CALL --> SIM
NS_CALL --> SIM

SIM --> AUTH
SIM --> RATE
SIM --> VAL
SIM --> SRV

AUTH --> CATCH_SPECIFIC
RATE --> CATCH_SPECIFIC
VAL --> CATCH_SPECIFIC
SRV --> CATCH_SPECIFIC

CATCH_SPECIFIC --> CATCH_API --> PAYLOAD

PAYLOAD --> API_ERRORS
API_ERRORS --> DECISION
VIOLATIONS --> DECISION

DECISION -->|api_errors > 0| BLOCK

%% STYLES

classDef infra fill:#f1ecff,stroke:#8b7cf6,stroke-width:2px
classDef simulator fill:#fff4e5,stroke:#f59e0b,stroke-width:2px
classDef error fill:#fde8e8,stroke:#e5484d,stroke-width:2px
classDef handler fill:#e8f0ff,stroke:#5b8def,stroke-width:2px
classDef state fill:#e6f7ee,stroke:#2e9d69,stroke-width:2px
classDef decision fill:#fff7db,stroke:#d4a017,stroke-width:2px
classDef danger fill:#fde8e8,stroke:#e5484d,stroke-width:2px

class SF_CALL,CLM_CALL,NS_CALL infra
class SIM simulator
class AUTH,RATE,VAL,SRV error
class CATCH_SPECIFIC,CATCH_API,PAYLOAD handler
class API_ERRORS,VIOLATIONS state
class DECISION decision
class BLOCK danger
```

### Key Error Handling Features

1. **In-Place Error Simulator Modification**: The `ERROR_SIMULATOR` object is modified in-place when enabled, ensuring all modules reference the same instance.

2. **Comprehensive Error Catching**: Each integration module catches both specific error types AND generic `APIError` as a fallback.

3. **Error-Aware Decision Making**: The `make_decision` function checks `api_errors` first, ensuring system failures block onboarding.

4. **Error Details in Reports**: API errors are added to violations and appear in generated reports with full context.

## 📊 Generated Reports

The agent generates professional reports for each run:

- **HTML Email Templates** - Blocked notifications, escalation notifications, success notifications, welcome emails
- **Markdown Reports** - Complete run summary with violations, warnings, API errors, and actions
- **JSON Audit Logs** - Machine-readable audit trail with full state

## 📋 Onboarding Task Management

When an account is provisioned, the agent automatically creates a **granular onboarding task checklist** that tracks the CS workflow:

### Task Categories

| Category | Owner | Examples |
|----------|-------|----------|
| **Automated** | System | Create tenant, generate API credentials, send welcome email |
| **CS Action** | CS Team | Schedule kickoff call, configure SSO, create custom reports |
| **Customer Action** | Customer | Verify login, complete platform tour, invite team members |
| **Technical** | CS Team | SSO integration, API setup |

### Task Endpoints

| Method | Endpoint | Description |
|--------|-----------|-------------|
| GET | `/demo/tasks/{account_id}` | Retrieve all onboarding tasks for an account |
| GET | `/demo/tasks/{account_id}/pending?owner={owner}` | Get pending tasks (optionally filter by owner: `cs_team`, `customer`, `system`) |
| GET | `/demo/tasks/{account_id}/overdue` | Identify overdue tasks for proactive follow-up |
| GET | `/demo/tasks/{account_id}/next-actions` | Return the next actionable tasks in the workflow |
| PUT | `/demo/tasks/{account_id}/{task_id}?status=completed&completed_by={email}` | Update task status when completed |

### Example Task Flow

```
1. ✅ Create Tenant (system - auto-completed)
2. ✅ Generate API Credentials (system - auto-completed)
3. ✅ Send Welcome Email (system - auto-completed)
4. ✅ Send Training Materials (system - auto-completed)
5. ⏳ Schedule Kickoff Call (cs_team - pending, due in 1 day)
6. ⏳ Verify Login Access (customer - pending, due in 2 days)
7. ⏳ Conduct Kickoff Call (cs_team - pending, due in 3 days)
8. ⏳ Complete Platform Tour (customer - pending, due in 5 days)
...
14. ⏳ Onboarding Complete (cs_team - pending, due in 45 days)
```

## 📁 Project Structure

```
Enterprise-Agents-Solutions-Case-Study/
├── main.py                               # FastAPI application + tracing setup
│
├── solution_design/                      # Architecture & technical design assets
│   ├── Solution_Design_Document.pdf
│   └── ...
│
├── reports_output/                       # Generated reports directory
├── logs/                                 # Runtime logs
│
└── app/
    ├── agent/                            # Pydantic AI agent
    │   ├── __init__.py                   # run_onboarding_async() entry point
    │   ├── onboarding_agent.py           # Agent + 16 tools (system prompt, tool defs)
    │   ├── dependencies.py               # OnboardingDeps (runtime context)
    │   ├── models.py                     # OnboardingResult (structured output)
    │   ├── state_utils.py                # State manipulation utilities
    │   └── invariants/                   # Business rule validators
    │
    ├── mcp/                              # FastMCP server definitions
    │   ├── salesforce_server.py          # Salesforce tools as MCP
    │   ├── clm_server.py                 # CLM tools as MCP
    │   ├── netsuite_server.py            # NetSuite tools as MCP
    │   ├── currency_server.py            # Currency conversion as MCP
    │   ├── provisioning_server.py        # Provisioning tools as MCP
    │   ├── notifications_server.py       # Notification tools as MCP
    │   └── validation_server.py          # Validation tools as MCP
    │
    ├── api/                              # REST endpoints
    │   ├── demo.py                       # Demo endpoints (7 scenarios + error simulation)
    │   └── webhook.py                    # Webhook handlers
    │
    ├── integrations/                     # Mock API clients
    │   ├── salesforce.py                 # Salesforce CRM (accounts, opps, contracts)
    │   ├── clm.py                        # Contract Lifecycle Management
    │   ├── netsuite.py                   # NetSuite ERP (invoices)
    │   ├── currency.py                   # Currency conversion with historical rates (Frankfurter API)
    │   ├── provisioning.py               # SaaS tenant provisioning
    │   └── api_errors.py                 # Error hierarchy + simulator
    │
    ├── tracing.py                        # Dual tracing setup (Logfire + LangSmith)
    │
    ├── llm/                              # LLM integration
    │   └── risk_analyzer.py
    │
    ├── notifications/                    # Slack / Email
    ├── reports/                          # Report generation
    └── logging/                          # Structured logging
```

## 🔒 Security Patterns Demonstrated

All integrations in this project are mocked, but they demonstrate the following production security patterns:

- **OAuth simulation** with token expiry and refresh flows
- **Permission checking** before every API call (role-based access control)
- **Credential validation** with distinct error types for expired vs invalid tokens
- **Audit logging** with correlation IDs for end-to-end traceability
- **Error masking** — no sensitive data (tokens, secrets) exposed in API responses or reports

## 📊 Observability

The agent supports **dual tracing** — both are opt-in via environment variables and can run simultaneously:

**Pydantic Logfire** (set `LOGFIRE_TOKEN`):
- Native Pydantic AI agent tracing
- Full reasoning chain, tool calls with inputs/outputs, structured output validation
- Dashboard at [logfire.pydantic.dev](https://logfire.pydantic.dev)

**LangSmith** (set `LANGCHAIN_API_KEY`):
- Agent execution runs, tool invocations, LLM completions
- Viewable under the "onboarding-agent" project in the LangSmith dashboard
- Uses the OpenTelemetry bridge (`langsmith.integrations.otel`)

## 🚧 Areas for Improvement

The following features would enhance the agent for production use:

### Current Limitations

| Limitation | Current State | Production Enhancement |
|------------|---------------|----------------------|
| **Task monitoring is passive** | Must call `/tasks/{id}/overdue` endpoint manually | Add scheduled job to check hourly and send automatic Slack reminders |
| **No human-in-the-loop approval** | ESCALATE notifies but doesn't wait for approval | Add Slack interactive buttons for approve/reject before provisioning |
| **No escalation hierarchy** | Notifications go to CS team only | If no action taken within X days, escalate to CS Manager/Director |
| **Event-driven task completion** | Tasks must be manually marked complete via API | Integrate webhooks from SaaS platform to auto-complete when customer takes action |
| **No customer-facing portal** | Customer can't see their onboarding progress | Build React dashboard showing task checklist and status |
| **Single workflow execution** | Agent runs once per trigger | Add retry/resume capability for failed workflows |

### Proactive vs Passive Features

| Feature | Status | Notes |
|---------|--------|-------|
| Invoice overdue warning | ✅ Proactive | Detected during onboarding, triggers ESCALATE |
| FX mismatch detection | ✅ Proactive | Live currency conversion reveals deal-value discrepancies |
| Underpayment detection | ✅ Proactive | Financial alignment check flags gaps > 2% threshold |
| Contract pending signatures | ✅ Proactive | Warning generated, CS notified via Slack |
| Risk analysis recommendations | ✅ Proactive | LLM suggests actions before problems escalate |
| Task overdue detection | ⚠️ Passive | Endpoint exists but requires manual polling |
| Task due date reminders | ❌ Not implemented | Would need scheduled job |
| Customer action tracking | ❌ Not implemented | Would need SaaS platform webhooks |
| Escalation to management | ❌ Not implemented | Would need threshold-based escalation rules |

### Suggested Enhancements

For detailed production enhancements (23 items with implementation ideas, Salesforce/NetSuite API references, and decision logic), see the **[Production Roadmap](production_roadmap/)**.

| Category | Enhancements | Focus |
|----------|:---:|-------|
| **Workflow & Notifications** | 3 | Task monitoring, escalation hierarchy, approval workflows |
| **Event-Driven Integration** | 2 | Webhook-based task completion, optimized batch fetching |
| **Salesforce & CRM Scenarios** | 5 | Account hierarchies, multi-opportunity handling, owner validation, stale deal detection |
| **Invoice & Financial Scenarios** | 4 | Installments, credit memos, payment discounts, cross-system reconciliation (multi-currency with historical rates and underpayment detection now implemented) |
| **Frontend & Observability** | 1 | Real-time CS dashboard |
| **LLM Resilience & Multi-Model Fallback** | 2 | Secondary LLM providers, unified gateway via LiteLLM |
| **RAG & Context Engineering** | 2 | Vector-based retrieval for risk analysis, historical predictive scoring |
| **Multi-Agent Architecture** | 2 | MCP server integration with A2A protocol for agent-to-agent collaboration, and credential management and trust boundaries |