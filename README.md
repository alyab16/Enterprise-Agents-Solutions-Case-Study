# Enterprise Onboarding Agent

An AI-powered customer onboarding automation agent built with LangGraph, demonstrating how autonomous agents can streamline enterprise SaaS onboarding workflows.

## 🎯 Overview

This agent automates the customer onboarding journey from **Sales → Contract → Invoice → Provisioning**, featuring:

- **Autonomous Decision Making**: PROCEED / ESCALATE / BLOCK based on business rules
- **LLM-Powered Risk Analysis**: Intelligent risk assessment with actionable recommendations
- **Multi-System Integration**: Salesforce, CLM, NetSuite, and SaaS provisioning (mocked)
- **Proactive Notifications**: Slack and email alerts for CS teams and stakeholders
- **Full Observability**: Structured logging and audit trail

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Webhook Trigger                                  │
│                    (Salesforce Opportunity.CloseWon)                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       LangGraph Agent Workflow                           │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐             │
│  │   Init   │ → │  Fetch   │ → │ Validate │ → │ Analyze  │             │
│  │          │   │   Data   │   │  Rules   │   │  Risks   │             │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘             │
│                                                      │                   │
│                                                      ▼                   │
│                                              ┌──────────────┐            │
│                                              │   Decision   │            │
│                                              │    Router    │            │
│                                              └──────────────┘            │
│                                               /     │     \              │
│                                              /      │      \             │
│                                             ▼       ▼       ▼            │
│                                          BLOCK  ESCALATE  PROCEED        │
│                                             │       │       │            │
│                                             └───────┴───────┘            │
│                                                     │                    │
│                                                     ▼                    │
│  ┌──────────────────┐    ┌──────────────────┐   ┌──────────────────┐   │
│  │  Notifications   │    │   Provisioning   │   │  Generate        │   │
│  │  (Slack/Email)   │    │   (if PROCEED)   │   │  Summary         │   │
│  └──────────────────┘    └──────────────────┘   └──────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          Integrations                                    │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────────────┐    │
│  │ Salesforce│  │    CLM    │  │  NetSuite │  │   Provisioning    │    │
│  │  (CRM)    │  │(Contracts)│  │ (Invoices)│  │   (SaaS Tenant)   │    │
│  └───────────┘  └───────────┘  └───────────┘  └───────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- OpenAI API key (optional - uses rule-based fallback without it)

### Installation

```bash
# Clone or navigate to the project
cd onboarding-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your OpenAI API key (optional)
```

### Run the Demo

```bash
# Run all demo scenarios
python -m app.scripts.demo_runner --all

# Run a specific scenario
python -m app.scripts.demo_runner --scenario ACME-001

# List available scenarios
python -m app.scripts.demo_runner --list
```

### Start the API Server

```bash
# Start FastAPI server
uvicorn main:app --reload

# Access endpoints:
# - Health check: http://localhost:8000/health
# - API docs: http://localhost:8000/docs
# - Demo scenarios: POST http://localhost:8000/demo/run/ACME-001
```

## 📋 Demo Scenarios

| Account ID | Scenario | Expected Decision | Description |
|------------|----------|-------------------|-------------|
| ACME-001 | Happy Path | ✅ PROCEED | All checks pass, account provisioned |
| BETA-002 | Blocked | 🚫 BLOCK | Opportunity not in "Closed Won" |
| GAMMA-003 | Escalation | ⚠️ ESCALATE | Overdue invoice needs finance review |
| DELETED-004 | Blocked | 🚫 BLOCK | Account deleted in Salesforce |
| MISSING-999 | Blocked | 🚫 BLOCK | Account not found |

## 🔧 Key Features

### 1. Invariant Validation System

Business rules are encoded as **invariants** with two tiers:
- **Tier 1 (Violations)**: Hard blockers that prevent onboarding
- **Tier 2 (Warnings)**: Issues requiring human review

```python
# Example: Contract must be activated
if status == "Activated" and not contract.get("ActivatedDate"):
    add_violation(state, "contract", "Activated contracts must have ActivatedDate")
```

### 2. LLM-Powered Risk Analysis

Uses OpenAI to generate:
- Human-readable risk summaries
- Business impact assessments
- Prioritized action recommendations

```json
{
    "summary": "Onboarding for ACME Corp is BLOCKED due to 2 critical issues",
    "risk_level": "high",
    "recommended_actions": [
        {"action": "Verify account in Salesforce", "owner": "Sales Ops", "priority": 1}
    ]
}
```

### 3. Notification Templates

Pre-built notifications for:
- 🚨 CS team alerts (blocked onboarding)
- ⚠️ Escalation requests
- ✅ Success notifications
- 💰 Finance alerts (overdue invoices)
- 📧 Customer welcome emails

### 4. Full Observability

Structured JSON logging with:
- State transitions
- Decision auditing
- Error tracking

## 📁 Project Structure

```
onboarding-agent/
├── main.py                      # FastAPI application
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment template
│
└── app/
    ├── agent/
    │   ├── graph.py            # LangGraph workflow definition
    │   ├── nodes.py            # Individual processing steps
    │   ├── router.py           # Conditional routing logic
    │   ├── state.py            # Agent state definition
    │   ├── state_utils.py      # State helpers
    │   └── invariants/         # Business rule validators
    │       ├── account.py
    │       ├── contract.py
    │       ├── opportunity.py
    │       ├── user.py
    │       └── invoice.py
    │
    ├── api/
    │   ├── webhook.py          # Webhook endpoints
    │   └── demo.py             # Demo API routes
    │
    ├── integrations/
    │   ├── salesforce.py       # Mock Salesforce
    │   ├── clm.py              # Mock CLM
    │   ├── netsuite.py         # Mock NetSuite
    │   └── provisioning.py     # Mock provisioning
    │
    ├── llm/
    │   └── risk_analyzer.py    # LLM risk analysis
    │
    ├── notifications/
    │   └── notifier.py         # Slack/Email notifications
    │
    ├── logging/
    │   └── logger.py           # Structured logging
    │
    └── scripts/
        └── demo_runner.py      # CLI demo script
```

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/webhook/onboarding` | Main onboarding trigger |
| POST | `/debug/onboarding` | Test with custom data |
| GET | `/demo/scenarios` | List demo scenarios |
| POST | `/demo/run/{account_id}` | Run specific scenario |
| POST | `/demo/run-all` | Run all scenarios |
| GET | `/demo/notifications` | View sent notifications |
| POST | `/demo/reset` | Reset demo state |

## 🛠️ Production Considerations

### Security
- Token-based authentication for webhooks
- Secrets management (Vault, AWS Secrets Manager)
- PII handling and data masking in logs

### Scalability
- Stateless design enables horizontal scaling
- Message queues for async processing (SQS, RabbitMQ)
- Caching for frequently accessed data

### Observability
- Distributed tracing (Jaeger, DataDog)
- Metrics collection (Prometheus)
- Alerting on SLA violations

### Governance
- Human-in-the-loop approval workflows
- Audit trail for compliance
- Rollback capabilities

## 📚 Extending the Agent

### Adding a New Integration

1. Create mock in `app/integrations/`
2. Add fetch node in `app/agent/nodes.py`
3. Add invariants in `app/agent/invariants/`
4. Update graph in `app/agent/graph.py`

### Adding New Business Rules

1. Add checks in appropriate invariant file
2. Use `add_violation()` for blockers
3. Use `add_warning()` for escalations

## 📄 License

MIT License - Built for StackAdapt Case Study
