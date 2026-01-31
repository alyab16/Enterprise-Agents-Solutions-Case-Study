# Enterprise Onboarding Agent

An AI-powered customer onboarding automation agent built with LangGraph, demonstrating how autonomous agents can streamline enterprise SaaS onboarding workflows.

## 🎯 Overview

This agent automates the customer journey from **Sales → Contract → Invoice → Provisioning**, featuring:

- **Autonomous Decision Making**: PROCEED / ESCALATE / BLOCK based on business rules
- **LLM-Powered Risk Analysis**: Intelligent risk assessment with actionable recommendations
- **Multi-System Integration**: Salesforce, CLM, NetSuite, and SaaS provisioning (mocked)
- **Realistic Error Simulation**: Auth failures, permission errors, validation errors, server errors
- **Proactive Notifications**: Slack and email alerts to stakeholders
- **Report Generation**: HTML emails, Markdown reports, JSON audit logs
- **Full Observability**: LangSmith tracing, structured JSON logging, audit trails

## 📚 Documentation

- **[Solution Design Document](docs/SOLUTION_DESIGN.md)** - Full architecture, trade-offs, MCP collaboration overview

## 🏗️ Architecture

### High-Level Flow

```mermaid
flowchart TB
    subgraph Triggers["🔔 Trigger Layer"]
        SF[Salesforce Webhook]
        API[Manual API Call]
        CRON[Scheduled Job]
    end

    subgraph Agent["🤖 LangGraph Agent"]
        INIT[Initialize State]
        FETCH[Fetch Data]
        VALIDATE[Validate Rules]
        ANALYZE[Analyze Risks]
        DECIDE{Decision Router}
        
        INIT --> FETCH
        FETCH --> VALIDATE
        VALIDATE --> ANALYZE
        ANALYZE --> DECIDE
    end

    subgraph Actions["⚡ Actions"]
        BLOCK[🚫 BLOCK]
        ESCALATE[⚠️ ESCALATE]
        PROCEED[✅ PROCEED]
        
        NOTIFY[Send Notifications]
        PROVISION[Provision Account]
        SUMMARY[Generate Summary]
    end

    subgraph Integrations["🔌 Integrations"]
        CRM[(Salesforce CRM)]
        CLM[(CLM Contracts)]
        ERP[(NetSuite ERP)]
        SAAS[(SaaS Platform)]
        SLACK[Slack]
        EMAIL[Email]
    end

    SF --> INIT
    API --> INIT
    CRON --> INIT
    
    DECIDE -->|violations > 0| BLOCK
    DECIDE -->|warnings > 0| ESCALATE
    DECIDE -->|all clear| PROCEED
    
    BLOCK --> NOTIFY
    ESCALATE --> NOTIFY
    PROCEED --> PROVISION
    PROVISION --> NOTIFY
    NOTIFY --> SUMMARY
    
    FETCH <--> CRM
    FETCH <--> CLM
    FETCH <--> ERP
    PROVISION <--> SAAS
    NOTIFY <--> SLACK
    NOTIFY <--> EMAIL
```

### State Machine

```mermaid
stateDiagram-v2
    [*] --> Initializing: Webhook Received
    
    Initializing --> FetchingSalesforce: Create Correlation ID
    FetchingSalesforce --> FetchingCLM: Account Data
    FetchingCLM --> FetchingNetSuite: Contract Data
    FetchingNetSuite --> Validating: Invoice Data
    
    Validating --> AnalyzingRisks: Run Invariants
    AnalyzingRisks --> MakingDecision: LLM Analysis
    
    MakingDecision --> Blocking: Violations Found
    MakingDecision --> Escalating: Warnings Only
    MakingDecision --> Provisioning: All Clear
    
    Blocking --> SendingNotifications
    Escalating --> SendingNotifications
    Provisioning --> SendingNotifications
    
    SendingNotifications --> GeneratingSummary
    GeneratingSummary --> [*]: Complete
```

### Data Flow

```mermaid
sequenceDiagram
    participant W as Webhook
    participant A as Agent
    participant SF as Salesforce
    participant CLM as CLM
    participant NS as NetSuite
    participant LLM as OpenAI
    participant P as Provisioning
    participant N as Notifications

    W->>A: POST /webhook/onboarding
    
    rect rgb(240, 248, 255)
        Note over A,NS: Data Fetching Phase
        A->>SF: GET Account, Opportunity, Contract
        SF-->>A: Account Data
        A->>CLM: GET Contract Status
        CLM-->>A: Contract Data
        A->>NS: GET Invoice
        NS-->>A: Invoice Data
    end
    
    rect rgb(255, 248, 240)
        Note over A,LLM: Analysis Phase
        A->>A: Run Invariant Checks
        A->>LLM: Analyze Risks
        LLM-->>A: Risk Assessment
        A->>A: Make Decision
    end
    
    alt Decision = PROCEED
        rect rgb(240, 255, 240)
            A->>P: Create Tenant
            P-->>A: Tenant ID
            A->>N: Success Notification
        end
    else Decision = BLOCK/ESCALATE
        rect rgb(255, 240, 240)
            A->>N: Alert Notification
        end
    end
    
    A-->>W: OnboardingResponse
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- OpenAI API key (optional - uses rule-based fallback without it)
- LangSmith API key (optional - for tracing)

### Installation

```bash
cd onboarding-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your API keys
```

### Run the Demo

```bash
# Run standalone demo (no dependencies needed)
python demo_standalone.py

# Or start the API server
uvicorn main:app --reload

# Open API docs at http://localhost:8000/docs
```

## 📋 Demo Scenarios

### Normal Scenarios

| Account ID | Scenario | Expected Decision |
|------------|----------|-------------------|
| ACME-001 | Happy Path | ✅ PROCEED |
| BETA-002 | Opportunity Not Won | 🚫 BLOCK |
| GAMMA-003 | Overdue Invoice | ⚠️ ESCALATE |
| DELETED-004 | Deleted Account | 🚫 BLOCK |

### Error Simulation Scenarios

| Account ID | Simulated Error | Description |
|------------|-----------------|-------------|
| AUTH-ERROR | 401 Unauthorized | Invalid API credentials |
| PERM-ERROR | 403 Forbidden | Missing permissions |
| SERVER-ERROR | 500 Server Error | API server failure |

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
| POST | `/demo/run-all` | Run all normal scenarios |
| POST | `/demo/run-error-scenarios` | Run error scenarios |
| POST | `/demo/run-with-report/{account_id}` | Run and generate reports |

### Report Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/demo/reports` | List generated reports |
| GET | `/demo/reports/{filename}` | View report (renders HTML) |
| GET | `/demo/reports/{filename}/download` | Download report |

## 📧 Generated Reports

The agent generates professional reports for each run:

- **HTML Email Templates** - Blocked notifications, success notifications, welcome emails
- **Markdown Reports** - Complete run summary with violations, warnings, actions
- **JSON Audit Logs** - Machine-readable audit trail

## 🔧 Error Handling

```mermaid
flowchart LR
    subgraph Salesforce
        SF401[401 INVALID_SESSION_ID]
        SF403[403 INSUFFICIENT_ACCESS]
        SF400[400 VALIDATION_ERROR]
        SF429[429 RATE_LIMIT]
    end
    
    subgraph NetSuite
        NS401[401 INVALID_LOGIN]
        NS403[403 INSUFFICIENT_PERMISSION]
        NS400[400 INVALID_FIELD_VALUE]
        NS429[429 CONCURRENCY_LIMIT]
    end
    
    subgraph CLM
        CLM401[401 UNAUTHORIZED]
        CLM403[403 FORBIDDEN]
        CLM409[409 CONTRACT_LOCKED]
        CLM500[500 INTERNAL_ERROR]
    end
    
    SF401 --> WARN[Add Warning]
    SF403 --> VIOL[Add Violation]
    NS401 --> WARN
    NS403 --> VIOL
    CLM401 --> WARN
    CLM403 --> VIOL
```

## 📁 Project Structure

```
onboarding-agent/
├── main.py                      # FastAPI application
├── demo_standalone.py           # Standalone demo script
├── docs/
│   └── SOLUTION_DESIGN.md       # Full solution design document
├── reports_output/              # Generated reports directory
└── app/
    ├── agent/                   # LangGraph workflow
    │   ├── graph.py            # Workflow definition
    │   ├── nodes.py            # Processing steps
    │   ├── router.py           # Decision routing
    │   └── invariants/         # Business rules
    ├── api/                    # REST endpoints
    ├── integrations/           # Mock API clients
    │   ├── salesforce.py       # Salesforce CRM
    │   ├── clm.py              # Contract Lifecycle
    │   ├── netsuite.py         # NetSuite ERP
    │   ├── provisioning.py     # SaaS provisioning
    │   └── api_errors.py       # Shared error types
    ├── llm/                    # LLM integration
    ├── notifications/          # Slack/Email
    ├── reports/                # Report generation
    └── logging/                # Structured logging
```

## 🔒 Security Features

- OAuth simulation with token expiry
- Permission checking before API calls
- Credential validation
- Audit logging with correlation IDs
- Error masking (no sensitive data in responses)

## 📊 Observability

With LangSmith tracing enabled, you can:
- View full execution traces
- Debug agent decisions
- Monitor latency and token usage
- Analyze LLM calls

## 📄 License

MIT License - Built for StackAdapt Case Study
