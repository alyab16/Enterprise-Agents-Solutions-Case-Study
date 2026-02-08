# Enterprise Onboarding Agent

An AI-powered customer onboarding automation agent built with LangGraph, demonstrating how autonomous agents can streamline enterprise SaaS onboarding workflows.

## 🎯 Overview

This agent automates the customer journey from **Sales → Contract → Invoice → Provisioning**, featuring:

- **Autonomous Decision Making**: PROCEED / ESCALATE / BLOCK based on business rules and API errors
- **LLM-Powered Risk Analysis**: Intelligent risk assessment with actionable recommendations
- **Multi-System Integration**: Salesforce, CLM, NetSuite, and SaaS provisioning (mocked)
- **Configurable Error Simulation**: Auth failures, permission errors, validation errors, rate limits, server errors with adjustable probabilities
- **Comprehensive Error Handling**: API errors are properly caught, recorded, and influence decisions
- **Proactive Notifications**: Slack and email alerts to stakeholders
- **Report Generation**: HTML emails, Markdown reports, JSON audit logs
- **Full Observability**: LangSmith tracing, structured JSON logging, audit trails

## 🎥 Video Demo Walkthrough

Watch the full solution walkthrough here:

👉 **[View Demo Video](https://drive.google.com/file/d/1m-0gMy5IV1vH42WWg4bLWKed_17RzZn-/view)**


## 🏗️ Architecture

### High-Level Flow

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

flowchart TB

%% ------------ TRIGGERS ------------
subgraph T["🔔 Trigger Layer"]
direction LR
SF["📡 Salesforce<br/>Webhook"]
API["🔧 Manual REST API"]
CRON["⏰ Cron Job Scheduler"]
end

%% ------------ AGENT ------------
subgraph A["🤖 Autonomous Onboarding Orchestrator"]
direction TB
INIT["Initialize State"]
FETCH["Fetch External Data"]
VALIDATE["Business Rules Engine"]
ANALYZE["LLM Risk Analysis"]
DECIDE{"Decision Router"}

INIT --> FETCH --> VALIDATE --> ANALYZE --> DECIDE
end

%% ------------ ACTIONS ------------
subgraph AC["⚡ Action Execution"]
direction TB
BLOCK["🚫 Block"]
ESCALATE["⚠️ Escalate"]
PROCEED["✅ Proceed"]

PROVISION["🚀 Provision Tenant"]
NOTIFY["📢 Notify Stakeholders"]
SUMMARY["📊 Generate Audit Report"]
end

%% ------------ INTEGRATIONS ------------
subgraph I["🔌 Integration Layer"]
direction LR
CRM[("Salesforce CRM")]
CLM[("CLM Contracts")]
ERP[("NetSuite ERP")]
SAAS[("SaaS Platform")]
SLACK[("Slack")]
EMAIL[("Email")]
end

%% FLOWS
SF -.-> INIT
API -.-> INIT
CRON -.-> INIT

DECIDE -->|violations > 0 OR api_errors > 0| BLOCK
DECIDE -->|warnings > 0| ESCALATE
DECIDE -->|all clear| PROCEED

BLOCK --> NOTIFY
ESCALATE --> NOTIFY
PROCEED --> PROVISION --> NOTIFY --> SUMMARY

FETCH <-->|REST API| CRM
FETCH <-->|REST API| CLM
FETCH <-->|REST API| ERP
PROVISION <-->|Create Tenant| SAAS
NOTIFY <-->|Message| SLACK
NOTIFY <-->|Send| EMAIL

%% STYLES

classDef agent fill:#e8f0ff,stroke:#5b8def,stroke-width:2px
classDef decision fill:#fff4e5,stroke:#f59e0b,stroke-width:2px
classDef action fill:#e6f7ee,stroke:#2e9d69,stroke-width:2px
classDef danger fill:#fde8e8,stroke:#e5484d,stroke-width:2px
classDef warn fill:#fff7db,stroke:#d4a017,stroke-width:2px
classDef success fill:#e6f9f0,stroke:#2fb171,stroke-width:2px
classDef infra fill:#f1ecff,stroke:#8b7cf6,stroke-width:2px

class INIT,FETCH,VALIDATE,ANALYZE agent
class DECIDE decision
class BLOCK danger
class ESCALATE warn
class PROCEED success
class PROVISION,NOTIFY,SUMMARY action
class CRM,CLM,ERP,SAAS,SLACK,EMAIL infra
```

### Decision Logic

The agent makes decisions based on three factors:

1. **API Errors** (`api_errors`): System integration failures (auth, rate limits, server errors) → **BLOCK**
2. **Violations** (`violations`): Business rule failures (missing data, invalid states) → **BLOCK**  
3. **Warnings** (`warnings`): Non-critical issues (missing optional fields, pending payments) → **ESCALATE**
4. **All Clear**: No errors, violations, or warnings → **PROCEED**

### State Machine

```mermaid
stateDiagram-v2
    [*] --> Initializing: Webhook Received
    
    Initializing --> FetchingSalesforce: Create Correlation ID
    FetchingSalesforce --> FetchingCLM: Account Data (or API Error)
    FetchingCLM --> FetchingNetSuite: Contract Data (or API Error)
    FetchingNetSuite --> Validating: Invoice Data (or API Error)
    
    Validating --> AnalyzingRisks: Run Invariants
    AnalyzingRisks --> MakingDecision: LLM/Rule-Based Analysis
    
    MakingDecision --> Blocking: API Errors OR Violations Found
    MakingDecision --> Escalating: Warnings Only
    MakingDecision --> Provisioning: All Clear
    
    Blocking --> SendingNotifications
    Escalating --> SendingNotifications
    Provisioning --> SendingNotifications
    
    SendingNotifications --> GeneratingSummary
    GeneratingSummary --> [*]: Complete
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- OpenAI API key (Recommended - uses rule-based fallback without it)
- LangSmith API key (optional - for tracing)

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
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# LangSmith tracing
LANGCHAIN_API_KEY=ls-...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=onboarding-agent
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com

# Logging
LOG_DIR=logs

# Environment
ENVIRONMENT=development
```

> **Note**: The agent works fully without any API keys. OpenAI enables LLM-powered risk analysis (instead of the rule-based fallback), and LangSmith enables execution tracing.

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

## 🧪 Optional: Standalone Demo Script

The standalone demo script can be used to exercise agent logic **without starting an API server**.

```bash
python demo_standalone.py
```

This script is optional and intended for:
- Local testing
- Agent behavior exploration
- Debugging without running FastAPI
---

## 📋 Demo Scenarios

### Normal Scenarios

| Account ID | Scenario | Expected Decision |
|------------|----------|-------------------|
| ACME-001 | Happy Path | ✅ PROCEED |
| BETA-002 | Opportunity Not Won | 🚫 BLOCK |
| GAMMA-003 | Overdue Invoice | ⚠️ ESCALATE |
| DELETED-004 | Deleted Account | 🚫 BLOCK |
| MISSING-999 | Account Not Found | 🚫 BLOCK |

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
├── main.py                          # FastAPI application
├── demo_standalone.py               # Standalone demo script
│
├── solution_design/        # Architecture & technical design assets
│   ├── 01_architecture.png
│   ├── 02_decision.png
│   ├── 03_mcp_architecture.png
│   ├── 04_state_machine.png
│   ├── Solution_Design_Document.tex
│   └── Solution_Design_Document.pdf
│
├── reports_output/                  # Generated reports directory
├── logs/                           # Runtime logs
│
└── app/
    ├── agent/                      # LangGraph workflow
    │   ├── graph.py                # Workflow definition
    │   ├── nodes.py                # Processing steps
    │   ├── router.py               # Decision routing
    │   ├── state.py                # State definition
    │   ├── state_utils.py          # State manipulation utilities
    │   └── invariants/             # Business rules
    │
    ├── api/                        # REST endpoints
    │   ├── demo.py                 # Demo endpoints with error simulation
    │   └── webhook.py              # Webhook handlers
    │
    ├── integrations/               # Mock API clients
    │   ├── salesforce.py
    │   ├── clm.py
    │   ├── netsuite.py
    │   ├── provisioning.py
    │   └── api_errors.py
    │
    ├── llm/                        # LLM integration
    │   └── risk_analyzer.py
    │
    ├── notifications/              # Slack / Email
    ├── reports/                    # Report generation
    └── logging/                    # Structured logging
```

## 🔒 Security Patterns Demonstrated

All integrations in this project are mocked, but they demonstrate the following production security patterns:

- **OAuth simulation** with token expiry and refresh flows
- **Permission checking** before every API call (role-based access control)
- **Credential validation** with distinct error types for expired vs invalid tokens
- **Audit logging** with correlation IDs for end-to-end traceability
- **Error masking** — no sensitive data (tokens, secrets) exposed in API responses or reports

## 📊 Observability

With LangSmith tracing enabled, you can:
- View full execution traces
- Debug agent decisions
- Monitor latency and token usage
- Analyze LLM calls

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
| Contract pending signatures | ✅ Proactive | Warning generated, CS notified via Slack |
| Risk analysis recommendations | ✅ Proactive | LLM suggests actions before problems escalate |
| Task overdue detection | ⚠️ Passive | Endpoint exists but requires manual polling |
| Task due date reminders | ❌ Not implemented | Would need scheduled job |
| Customer action tracking | ❌ Not implemented | Would need SaaS platform webhooks |
| Escalation to management | ❌ Not implemented | Would need threshold-based escalation rules |

### Suggested Enhancements

#### Workflow & Notifications

1. **Task Monitor Agent**: Scheduled job that runs hourly to detect overdue tasks and send proactive Slack reminders to CS team.

2. **Escalation Hierarchy**: If CS team doesn't act on an ESCALATE notification within a threshold (e.g., 48 hours), automatically notify CS Manager. If still unresolved after another threshold, escalate to CS Director.
   ```
   Day 0: ESCALATE → Notify CS Team (#cs-onboarding)
   Day 2: No action → Notify CS Manager (@cs-manager)
   Day 4: Still unresolved → Notify CS Director (@cs-director)
   ```

3. **Approval Workflow**: For ESCALATE decisions, send Slack message with interactive buttons:
   ```
   ⚠️ ACME Corp needs review - Invoice overdue
   [Approve Provisioning] [Reject] [View Details]
   ```

#### Event-Driven Integration

4. **Event-Driven Task Completion**: Webhooks from the SaaS platform to automatically mark tasks complete:
   ```
   Customer logs in → Mark "Verify Login Access" complete
   Customer completes tour → Mark "Complete Platform Tour" complete
   ```

5. **Optimized Data Fetching**: Batch API requests (Salesforce Composite API) and concurrent multithreaded calls with bounded retry logic to reduce latency.

#### Salesforce & CRM Scenarios

6. **Account Hierarchy & Subsidiary Onboarding**: Salesforce Accounts support parent-child relationships via the [`ParentId`](https://developer.salesforce.com/docs/atlas.en-us.object_reference.meta/object_reference/sforce_api_objects_account.htm) field. Enterprise customers often have a parent account with multiple subsidiaries, each requiring their own tenant. The agent would detect child accounts under a parent, validate whether the contract covers subsidiaries, and either onboard them under a single master agreement or flag that separate contracts are needed per entity.

7. **Multi-Opportunity Handling**: A single Account can have multiple Closed Won [Opportunities](https://developer.salesforce.com/docs/atlas.en-us.object_reference.meta/object_reference/sforce_api_objects_opportunity.htm) representing upsells, renewals, or separate product lines. Rather than assuming one Opportunity per Account, the agent would fetch all Closed Won Opportunities, validate that each has a linked `ContractId`, and determine which Opportunity is driving the current onboarding, prioritizing by `CloseDate` or `Amount`, and warning CS if multiple Opportunities lack contract linkage.

8. **Opportunity Currency Mismatch Detection**: Salesforce Opportunities support multi-currency via the `CurrencyIsoCode` field. The agent would cross-validate that the Opportunity currency matches the linked NetSuite Invoice currency. A mismatch (e.g., Opportunity in USD but Invoice in CAD) could indicate a billing setup error that should be flagged to Revenue Operations before provisioning.

9. **Account Owner Validation & Reassignment Detection**: The agent currently validates the Account Owner (`OwnerId`) via the [User](https://developer.salesforce.com/docs/atlas.en-us.object_reference.meta/object_reference/sforce_api_objects_user.htm) object. In production, additional checks would include: whether the owner's `LastLoginDate` is recent (an owner who hasn't logged in for 90 days may have left the company), whether the owner's `ManagerId` is populated (for escalation routing), and whether the owner was recently reassigned (comparing `OwnerId` against `LastModifiedDate` on the Account) which could indicate a handoff that CS should be aware of.

10. **Stale Opportunity Detection**: Using the Opportunity's `AgeInDays` field and `LastActivityDate`, the agent would flag opportunities that closed a long time ago but were never onboarded - e.g., "This Opportunity closed 120 days ago with no provisioning activity." This catches deals that fell through the cracks, where the customer may have already churned or lost interest, and CS should confirm the customer still intends to proceed before provisioning.

#### Invoice & Financial Scenarios

11. **Multi-Currency Invoice Handling**: Support invoices in foreign currencies by validating against NetSuite's [Currency](https://system.netsuite.com/help/helpcenter/en_US/APIs/REST_API_Browser/record/v1/2023.1/index.html#/definitions/currency) and [Invoice](https://system.netsuite.com/help/helpcenter/en_US/APIs/REST_API_Browser/record/v1/2023.1/index.html#/definitions/invoice) objects. The agent would fetch the invoice's currency (`symbol`, `exchangeRate`), convert outstanding amounts to the base currency (CAD) using the exchange rate effective on the invoice date, and flag discrepancies where the rate has shifted significantly since the invoice was issued, thus, alerting Finance to potential forex exposure before provisioning.

12. **Payment Terms & Installment Validation**: NetSuite supports flexible payment [Terms](https://system.netsuite.com/help/helpcenter/en_US/APIs/REST_API_Browser/record/v1/2023.1/index.html#/definitions/term) (Net 30, Net 60, date-driven, early payment discounts) and [installment-based](https://system.netsuite.com/help/helpcenter/en_US/APIs/REST_API_Browser/record/v1/2023.1/index.html#/definitions/invoice-installmentElement) billing where the total is split across multiple scheduled payments. The agent would validate the term structure (`daysUntilNetDue`, `recurrenceCount`, `splitEvenly`) and check each installment element (`amount`, `amountDue`, `dueDate`) individually rather than treating the invoice as a single payment. This enables more nuanced decisions. For example, an ESCALATE if only the first installment is overdue versus a BLOCK if multiple installments are missed.

13. **Early Payment Discount Detection**: NetSuite Terms support early payment discounts (`discountPercent`, `daysUntilExpiry`). If the customer's invoice is within the discount window, the agent would add a note to the CS team's report highlighting the opportunity (e.g., "Customer is eligible for a 2% discount if payment is received within 5 days. Consider mentioning during kickoff call.") This turns the agent into a revenue-aware assistant, not just a blocker/escalator/approver.

14. **Credit Memo & Partial Payment Reconciliation**: In production, invoices rarely exist in isolation. A customer may have partial payments applied, outstanding credit memos from a previous billing dispute, or unapplied deposits. The agent would reconcile the invoice's `amountRemaining` against any linked credit memos and deposits to calculate the true outstanding balance. This prevents false escalations. For example, an invoice showing $25,000 outstanding shouldn't trigger an overdue warning if a $20,000 credit memo is pending application by the Finance team.

15. **Multi-Invoice Account Validation**: Enterprise customers often have multiple invoices at different stages, one paid, one current, one overdue from a previous contract period. Rather than checking a single invoice, the agent would fetch all open invoices for the account and apply tiered logic:
    ```
    All invoices paid         → PROCEED (no financial risk)
    Current invoices only     → PROCEED with note to CS
    One overdue < 30 days     → ESCALATE (warning to CS, recommend follow-up)
    One overdue > 30 days     → ESCALATE (urgent, notify Finance)
    Multiple overdue invoices → BLOCK (systemic payment issue, require Finance approval)
    Total overdue > contract value → BLOCK (high exposure, escalate to Finance Director)
    ```

16. **Revenue Recognition & Contract Value Alignment**: Cross-validate the invoice total against the Salesforce Opportunity `Amount` and the CLM contract value. If the invoice total exceeds the contracted amount, potentially indicating a billing error or unapproved scope change, the agent would ESCALATE to both Finance and the Account Owner. Conversely, if the invoice is significantly below the contract value, it may indicate a missing invoice or phased billing that hasn't been fully set up, warranting a warning to Revenue Operations.

#### Frontend & Observability

17. **Real-Time Dashboard**: React frontend showing:
     - Active onboardings with status
     - Task checklists with progress bars
     - Overdue alerts and escalation status
     - One-click actions for CS team

#### Multi-Agent Architecture

18. **MCP and A2A Protocol Integration**: Each integration (Salesforce, CLM, NetSuite, Tasks) could be wrapped in a dedicated [MCP](https://modelcontextprotocol.io/) server, standardizing how the onboarding agent accesses external tools and data through a single protocol. If those MCP servers evolve into autonomous agents with their own decision-making. For example, a Finance Agent that proactively flags credit risk rather than just fetching invoices, or a Compliance Agent that validates data residency requirements before tenant provisioning. Then Google's [Agent2Agent (A2A)](https://a2a-protocol.org/) protocol could enable peer-to-peer collaboration between them. MCP handles the agent-to-tool layer, while A2A handles the agent-to-agent layer.
