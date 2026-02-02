# Enterprise Onboarding Agent - Code Explanation

## Overview

This document explains the complete codebase for the Enterprise Customer Onboarding Agent, a production-minded AI system that automates SaaS customer onboarding from deal closure through provisioning and ongoing task management.

---

## Table of Contents

1. [Project Structure](#1-project-structure)
2. [Entry Points](#2-entry-points)
3. [Agent Core](#3-agent-core)
4. [Integrations](#4-integrations)
5. [LLM Integration](#5-llm-integration)
6. [Notifications](#6-notifications)
7. [Reports](#7-reports)
8. [API Layer](#8-api-layer)
9. [Data Flow Walkthrough](#9-data-flow-walkthrough)
10. [Key Design Patterns](#10-key-design-patterns)

---

## 1. Project Structure

```
onboarding-agent/
├── main.py                          # FastAPI application entry point
├── demo_standalone.py               # Standalone demo (no server needed)
├── README.md                        # Project documentation
├── docs/
│   ├── SOLUTION_DESIGN.md          # Architecture documentation
│   └── DEMO_WALKTHROUGH.md         # Demo script
└── app/
    ├── __init__.py                 # Package marker
    ├── agent/                      # 🧠 Core agent logic
    │   ├── __init__.py
    │   ├── graph.py               # LangGraph workflow definition
    │   ├── nodes.py               # Individual processing steps
    │   ├── router.py              # Decision routing logic
    │   ├── state.py               # State type definitions
    │   ├── state_utils.py         # State manipulation helpers
    │   └── invariants/            # Business rule validators
    │       ├── __init__.py
    │       ├── account.py
    │       ├── contract.py
    │       ├── invoice.py
    │       ├── opportunity.py
    │       └── user.py
    ├── api/                        # 🌐 REST API endpoints
    │   ├── __init__.py
    │   ├── demo.py                # Demo & testing endpoints
    │   └── webhook.py             # Production webhook handlers
    ├── integrations/              # 🔌 External system mocks
    │   ├── __init__.py
    │   ├── api_errors.py          # Error types & simulator
    │   ├── salesforce.py          # Salesforce CRM mock
    │   ├── clm.py                 # Contract Lifecycle mock
    │   ├── netsuite.py            # NetSuite ERP mock
    │   └── provisioning.py        # SaaS provisioning + tasks
    ├── llm/                       # 🤖 LLM integration
    │   ├── __init__.py
    │   └── risk_analyzer.py       # Risk analysis with fallback
    ├── notifications/             # 📧 Notification system
    │   ├── __init__.py
    │   └── notifier.py            # Slack & email notifications
    ├── reports/                   # 📄 Report generation
    │   ├── __init__.py
    │   └── generator.py           # HTML/Markdown/JSON reports
    ├── logging/                   # 📊 Structured logging
    │   ├── __init__.py
    │   └── logger.py              # JSON logging utilities
    ├── models/                    # 📦 Data models
    │   ├── __init__.py
    │   └── events.py              # Pydantic request/response models
    └── scripts/                   # 🔧 Utility scripts
        ├── __init__.py
        └── demo_runner.py         # Batch demo runner
```

---

## 2. Entry Points

### `main.py`

**Purpose:** FastAPI application entry point that assembles all routers.

**What it does:**
```python
from fastapi import FastAPI
from app.api import demo, webhook

app = FastAPI(
    title="Enterprise Onboarding Agent",
    description="AI-powered customer onboarding automation",
    version="1.0.0"
)

# Mount API routers
app.include_router(webhook.router)  # /webhook/* endpoints
app.include_router(demo.router, prefix="/demo")  # /demo/* endpoints

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

**Importance:** This is what `uvicorn main:app` runs. It's the HTTP interface to the agent.

---

### `demo_standalone.py`

**Purpose:** Run the agent without starting a web server - useful for testing and demos.

**What it does:**
```python
from app.agent import run_onboarding

# Run a scenario directly
result = run_onboarding(
    account_id="ACME-001",
    event_type="demo.standalone"
)

print(f"Decision: {result['decision']}")
print(f"Tasks Created: {result['provisioning']['onboarding_tasks']['total_tasks']}")
```

**Importance:** Allows testing the core agent logic without HTTP overhead.

---

## 3. Agent Core

### `app/agent/graph.py`

**Purpose:** Defines the LangGraph state machine - the "brain" of the agent.

**What it does:**

```python
from langgraph.graph import StateGraph, END
from app.agent.state import AgentState
from app.agent import nodes
from app.agent.router import route_decision

def create_graph() -> StateGraph:
    """Build the agent workflow graph."""
    
    graph = StateGraph(AgentState)
    
    # Add processing nodes (steps)
    graph.add_node("init", nodes.initialize)
    graph.add_node("fetch_salesforce", nodes.fetch_salesforce_data)
    graph.add_node("fetch_clm", nodes.fetch_clm_data)
    graph.add_node("fetch_netsuite", nodes.fetch_netsuite_data)
    graph.add_node("validate", nodes.validate_invariants)
    graph.add_node("analyze", nodes.analyze_risks)
    graph.add_node("decide", nodes.make_decision)
    graph.add_node("provision", nodes.provision_account)
    graph.add_node("notify", nodes.send_notifications)
    graph.add_node("summarize", nodes.generate_summary)
    
    # Define the flow (edges)
    graph.set_entry_point("init")
    graph.add_edge("init", "fetch_salesforce")
    graph.add_edge("fetch_salesforce", "fetch_clm")
    graph.add_edge("fetch_clm", "fetch_netsuite")
    graph.add_edge("fetch_netsuite", "validate")
    graph.add_edge("validate", "analyze")
    graph.add_edge("analyze", "decide")
    
    # Conditional routing based on decision
    graph.add_conditional_edges(
        "decide",
        route_decision,  # Function that returns next node name
        {
            "provision": "provision",  # PROCEED → provision
            "notify": "notify",         # BLOCK/ESCALATE → notify directly
        }
    )
    
    graph.add_edge("provision", "notify")
    graph.add_edge("notify", "summarize")
    graph.add_edge("summarize", END)
    
    return graph.compile()

# Create singleton graph instance
graph = create_graph()

def run_onboarding(account_id: str, event_type: str = "webhook") -> dict:
    """Execute the onboarding workflow for an account."""
    initial_state = {
        "account_id": account_id,
        "event_type": event_type,
        "correlation_id": str(uuid.uuid4()),
        "stage": "initializing",
        # ... other initial state fields
    }
    
    final_state = graph.invoke(initial_state)
    return final_state
```

**Importance:** This is the orchestration layer. It defines WHAT happens and in WHAT ORDER. The graph ensures consistent workflow execution with proper error handling at each step.

---

### `app/agent/nodes.py`

**Purpose:** Individual processing functions (nodes) that the graph executes.

**What it does:**

Each node is a function that:
1. Receives the current state
2. Performs an action
3. Updates and returns the state

```python
def initialize(state: AgentState) -> AgentState:
    """Initialize the agent state with correlation ID and timestamps."""
    state["correlation_id"] = str(uuid.uuid4())
    state["started_at"] = datetime.utcnow().isoformat()
    state["stage"] = "initializing"
    
    log_event("node.init", account_id=state["account_id"])
    return state


def fetch_salesforce_data(state: AgentState) -> AgentState:
    """Fetch account, user, and opportunity data from Salesforce."""
    account_id = state["account_id"]
    state["stage"] = "fetching_salesforce"
    
    # Call Salesforce mock API
    account = salesforce.get_account(account_id)
    
    # Check if we got an API error
    if account and account.get("status") == "API_ERROR":
        add_api_error(state, account)  # Record the error
        state["account"] = None
    else:
        state["account"] = account
        
        # Fetch related data
        if account:
            user_id = account.get("OwnerId")
            state["user"] = salesforce.get_user(user_id)
            
            opp_id = account.get("Primary_Opportunity__c")
            state["opportunity"] = salesforce.get_opportunity(opp_id)
    
    return state


def fetch_clm_data(state: AgentState) -> AgentState:
    """Fetch contract data from CLM system."""
    account_id = state["account_id"]
    state["stage"] = "fetching_clm"
    
    contract = clm.get_contract(account_id)
    
    if contract and contract.get("status") == "API_ERROR":
        add_api_error(state, contract)
        state["clm"] = None
    else:
        state["clm"] = contract
    
    return state


def fetch_netsuite_data(state: AgentState) -> AgentState:
    """Fetch invoice data from NetSuite."""
    # Similar pattern...
    return state


def validate_invariants(state: AgentState) -> AgentState:
    """Run all business rule validations."""
    state["stage"] = "validating"
    
    # Check each data domain
    account_violations, account_warnings = check_account_invariants(state.get("account"))
    user_violations, user_warnings = check_user_invariants(state.get("user"))
    opp_violations, opp_warnings = check_opportunity_invariants(state.get("opportunity"))
    contract_violations, contract_warnings = check_contract_invariants(state.get("clm"))
    invoice_violations, invoice_warnings = check_invoice_invariants(state.get("invoice"))
    
    # Aggregate results
    state["violations"] = {
        "account": account_violations,
        "user": user_violations,
        "opportunity": opp_violations,
        "contract": contract_violations,
        "invoice": invoice_violations,
    }
    
    state["warnings"] = {
        "account": account_warnings,
        "user": user_warnings,
        # ...
    }
    
    return state


def analyze_risks(state: AgentState) -> AgentState:
    """Use LLM to analyze risks and generate recommendations."""
    state["stage"] = "analyzing_risks"
    
    # Call LLM (or fallback to rule-based)
    analysis = risk_analyzer.analyze_risks(state)
    state["risk_analysis"] = analysis
    
    return state


def make_decision(state: AgentState) -> AgentState:
    """Determine BLOCK/ESCALATE/PROCEED based on all factors."""
    state["stage"] = "making_decision"
    
    api_errors = state.get("api_errors", [])
    violations = state.get("violations", {})
    warnings = state.get("warnings", {})
    
    api_error_count = len(api_errors)
    violation_count = sum(len(v) for v in violations.values())
    warning_count = sum(len(w) for w in warnings.values())
    
    # Priority: API errors > Violations > Warnings
    if api_error_count > 0:
        state["decision"] = "BLOCK"
        # Add API errors to violations for reporting
        for error in api_errors:
            key = error.get("system", "api")
            violations.setdefault(key, []).append(
                f"API Error ({error['error_type']}): {error['message']}"
            )
    elif violation_count > 0:
        state["decision"] = "BLOCK"
    elif warning_count > 0:
        state["decision"] = "ESCALATE"
    else:
        state["decision"] = "PROCEED"
    
    log_event("decision.made", 
              decision=state["decision"],
              api_errors=api_error_count,
              violations=violation_count,
              warnings=warning_count)
    
    return state


def provision_account(state: AgentState) -> AgentState:
    """Create tenant and onboarding tasks (only if PROCEED)."""
    if state.get("decision") != "PROCEED":
        return state  # Skip provisioning
    
    state["stage"] = "provisioning"
    
    account = state.get("account", {})
    customer_name = account.get("Name", state["account_id"])
    tier = state.get("clm", {}).get("key_terms", {}).get("sla_tier", "Starter")
    
    # Create tenant + 14 onboarding tasks
    result = provisioning.provision_account(
        account_id=state["account_id"],
        tier=tier,
        customer_name=customer_name
    )
    
    state["provisioning"] = result
    
    log_event("provisioning.complete",
              tenant_id=result["tenant_id"],
              tasks_created=result["onboarding_tasks"]["total_tasks"])
    
    return state


def send_notifications(state: AgentState) -> AgentState:
    """Send Slack and email notifications based on decision."""
    state["stage"] = "notifying"
    
    decision = state.get("decision")
    account_name = state.get("account", {}).get("Name", state["account_id"])
    
    if decision == "PROCEED":
        notifier.notify_cs_team_success(
            account_name=account_name,
            tenant_id=state["provisioning"]["tenant_id"],
            # ...
        )
        notifier.send_customer_welcome_email(...)
    elif decision == "BLOCK":
        notifier.notify_cs_team_blocked(
            account_name=account_name,
            violations=state["violations"],
            # ...
        )
    else:  # ESCALATE
        notifier.notify_cs_team_escalation(...)
    
    return state


def generate_summary(state: AgentState) -> AgentState:
    """Generate human-readable summary."""
    state["stage"] = "complete"
    
    analysis = state.get("risk_analysis", {})
    state["human_summary"] = analysis.get("summary", "Onboarding complete.")
    
    return state
```

**Importance:** Nodes are the actual "work" of the agent. Each is focused, testable, and handles its own errors gracefully.

---

### `app/agent/router.py`

**Purpose:** Conditional routing logic for the graph.

**What it does:**

```python
def route_decision(state: AgentState) -> str:
    """
    Route to next node based on decision.
    
    Returns:
        "provision" - if decision is PROCEED
        "notify" - if decision is BLOCK or ESCALATE
    """
    decision = state.get("decision", "BLOCK")
    
    if decision == "PROCEED":
        return "provision"
    else:
        return "notify"  # Skip provisioning, go straight to notifications
```

**Importance:** Enables conditional workflow paths. PROCEED goes through provisioning; BLOCK/ESCALATE skip directly to notifications.

---

### `app/agent/state.py`

**Purpose:** TypedDict definition for the agent state.

**What it does:**

```python
from typing import TypedDict, Optional, List, Dict, Any

class AgentState(TypedDict, total=False):
    # Identifiers
    account_id: str
    correlation_id: str
    event_type: str
    
    # Stage tracking
    stage: str
    started_at: str
    
    # Fetched data
    account: Optional[Dict[str, Any]]
    user: Optional[Dict[str, Any]]
    opportunity: Optional[Dict[str, Any]]
    clm: Optional[Dict[str, Any]]
    invoice: Optional[Dict[str, Any]]
    
    # Validation results
    violations: Dict[str, List[str]]
    warnings: Dict[str, List[str]]
    api_errors: List[Dict[str, Any]]
    
    # Analysis
    risk_analysis: Dict[str, Any]
    
    # Decision
    decision: str  # "PROCEED" | "ESCALATE" | "BLOCK"
    
    # Actions
    provisioning: Optional[Dict[str, Any]]
    notifications_sent: List[Dict[str, Any]]
    actions_taken: List[Dict[str, Any]]
    
    # Output
    human_summary: str
```

**Importance:** Provides type safety and documentation for the data flowing through the agent. LangGraph uses this to validate state transitions.

---

### `app/agent/state_utils.py`

**Purpose:** Helper functions for manipulating state.

**What it does:**

```python
def add_api_error(state: AgentState, error_payload: dict) -> None:
    """Record an API error in the state."""
    if "api_errors" not in state:
        state["api_errors"] = []
    
    state["api_errors"].append({
        "error_id": str(uuid.uuid4())[:12],
        "system": error_payload.get("system", "unknown"),
        "error_type": error_payload.get("error_type", "unknown"),
        "error_code": error_payload.get("error_code"),
        "message": error_payload.get("message"),
        "http_status": error_payload.get("http_status"),
        "stage": state.get("stage"),
        "timestamp": datetime.utcnow().isoformat(),
    })


def record_action(state: AgentState, action_type: str, details: dict) -> None:
    """Record an action taken by the agent."""
    if "actions_taken" not in state:
        state["actions_taken"] = []
    
    state["actions_taken"].append({
        "type": action_type,
        **details,
        "timestamp": datetime.utcnow().isoformat(),
    })


def record_notification(state: AgentState, channel: str, recipient: str, message: str) -> None:
    """Record a notification sent."""
    if "notifications_sent" not in state:
        state["notifications_sent"] = []
    
    state["notifications_sent"].append({
        "channel": channel,
        "recipient": recipient,
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
    })
```

**Importance:** Centralizes state manipulation logic, ensuring consistent error recording across all nodes.

---

### `app/agent/invariants/`

**Purpose:** Business rule validators - the "rules engine" of the agent.

**Structure:**
- `account.py` - Account validation rules
- `user.py` - User validation rules
- `opportunity.py` - Opportunity validation rules
- `contract.py` - Contract validation rules
- `invoice.py` - Invoice validation rules
- `__init__.py` - Exports all check functions

**Example (`account.py`):**

```python
from typing import Tuple, List, Optional, Dict, Any

def check_account_invariants(account: Optional[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    """
    Validate account data against business rules.
    
    Returns:
        (violations, warnings) - Lists of issue messages
    """
    violations = []
    warnings = []
    
    # BLOCKING: Account must exist
    if not account:
        violations.append("Account data missing")
        return violations, warnings
    
    # BLOCKING: Account must not be deleted
    if account.get("IsDeleted"):
        violations.append("Account is marked as deleted in Salesforce")
    
    # BLOCKING: Account must be active
    status = account.get("Status__c")
    if status and status.lower() in ["inactive", "churned", "suspended"]:
        violations.append(f"Account status is {status} - cannot onboard")
    
    # WARNING: Missing billing address
    if not account.get("BillingStreet"):
        warnings.append("Billing address is incomplete")
    
    # WARNING: Missing industry
    if not account.get("Industry"):
        warnings.append("Industry not specified - may affect onboarding flow")
    
    return violations, warnings
```

**Example (`opportunity.py`):**

```python
def check_opportunity_invariants(opportunity: Optional[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    violations = []
    warnings = []
    
    if not opportunity:
        violations.append("Opportunity data missing")
        return violations, warnings
    
    # BLOCKING: Must be Closed Won
    stage = opportunity.get("StageName", "")
    if stage != "Closed Won":
        violations.append(f"Opportunity stage is '{stage}' - must be 'Closed Won' to proceed")
    
    # BLOCKING: Amount must be positive
    amount = opportunity.get("Amount", 0)
    if amount <= 0:
        violations.append("Opportunity amount is zero or negative")
    
    # WARNING: Close date in past
    close_date = opportunity.get("CloseDate")
    if close_date:
        # Check if close date is more than 30 days ago
        # ...
        warnings.append("Opportunity closed more than 30 days ago")
    
    return violations, warnings
```

**Importance:** Invariants encode business rules as code. They're the guardrails that prevent bad data from causing provisioning issues. Violations BLOCK; Warnings ESCALATE.

---

## 4. Integrations

### `app/integrations/api_errors.py`

**Purpose:** Defines all API error types and the error simulator.

**What it does:**

```python
from enum import Enum
from dataclasses import dataclass
import random

class ErrorCategory(Enum):
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    NOT_FOUND = "not_found"
    RATE_LIMIT = "rate_limit"
    SERVER_ERROR = "server_error"


@dataclass
class APIError(Exception):
    """Base API error with structured data."""
    status_code: int
    error_code: str
    message: str
    category: ErrorCategory
    details: dict = None
    
    def to_dict(self) -> dict:
        return {
            "status_code": self.status_code,
            "error_code": self.error_code,
            "message": self.message,
            "category": self.category.value,
            "details": self.details,
        }


# Salesforce-specific errors
class SalesforceAuthenticationError(APIError):
    def __init__(self):
        super().__init__(
            status_code=401,
            error_code="INVALID_SESSION_ID",
            message="Session expired or invalid",
            category=ErrorCategory.AUTHENTICATION
        )

class SalesforceAuthorizationError(APIError):
    def __init__(self, resource: str, operation: str):
        super().__init__(
            status_code=403,
            error_code="INSUFFICIENT_ACCESS",
            message=f"Insufficient privileges to {operation} {resource}",
            category=ErrorCategory.AUTHORIZATION
        )

# Similar for NetSuite, CLM...


class ErrorSimulator:
    """
    Injects random errors for testing resilience.
    
    Rates are probabilities (0.0 to 1.0) for each error type.
    """
    
    def __init__(self):
        self.auth_error_rate = 0.0
        self.validation_error_rate = 0.0
        self.rate_limit_error_rate = 0.0
        self.server_error_rate = 0.0
        self.enabled = False
    
    def maybe_raise_error(self, api_type: str = "salesforce") -> None:
        """Possibly raise an error based on configured rates."""
        if not self.enabled:
            return
        
        roll = random.random()
        cumulative = 0.0
        
        # Check each error type
        cumulative += self.auth_error_rate
        if roll < cumulative:
            if api_type == "salesforce":
                raise SalesforceAuthenticationError()
            elif api_type == "netsuite":
                raise NetSuiteAuthenticationError()
            # ...
        
        cumulative += self.rate_limit_error_rate
        if roll < cumulative:
            raise SalesforceRateLimitError(limit=100000, reset_time=3600)
        
        # ... other error types


# Global singleton - modified in-place to ensure all modules reference same instance
ERROR_SIMULATOR = ErrorSimulator()


def enable_error_simulation(auth_rate=0.05, validation_rate=0.05, 
                            rate_limit_rate=0.02, server_error_rate=0.01):
    """Enable error injection with specified rates."""
    # IMPORTANT: Modify in-place, don't replace!
    ERROR_SIMULATOR.auth_error_rate = auth_rate
    ERROR_SIMULATOR.validation_error_rate = validation_rate
    ERROR_SIMULATOR.rate_limit_error_rate = rate_limit_rate
    ERROR_SIMULATOR.server_error_rate = server_error_rate
    ERROR_SIMULATOR.enabled = True


def disable_error_simulation():
    """Turn off error injection."""
    ERROR_SIMULATOR.enabled = False
```

**Importance:** 
1. Provides typed, structured errors matching real API responses
2. Error simulator enables chaos testing without modifying business logic
3. In-place modification ensures consistent behavior across all integration modules

---

### `app/integrations/salesforce.py`

**Purpose:** Mock Salesforce CRM API with realistic error handling.

**What it does:**

```python
from app.integrations.api_errors import (
    SalesforceError, SalesforceAuthenticationError, 
    SalesforceNotFoundError, ERROR_SIMULATOR, APIError
)

# Mock data store
MOCK_ACCOUNTS = {
    "ACME-001": {
        "Id": "0018Z00003ACMEQ",
        "Name": "ACME Corp",
        "OwnerId": "0058Z00000OWNER1",
        "Primary_Opportunity__c": "0068Z00001OPP001",
        "BillingCountry": "United States",
        "Industry": "Technology",
        "IsDeleted": False,
        # ...
    },
    "DELETED-004": {
        "Id": "0018Z00003DEL04",
        "Name": "Deleted Inc",
        "IsDeleted": True,  # This will cause a violation
    },
    # Error simulation scenarios
    "AUTH-ERROR": {"_simulate_error": "authentication"},
    "PERM-ERROR": {"_simulate_error": "authorization"},
}


class SalesforceClient:
    """Mock Salesforce REST API client."""
    
    def __init__(self, config=None):
        self.config = config or SalesforceConfig()
    
    def _check_auth(self):
        """Validate authentication - may raise simulated error."""
        ERROR_SIMULATOR.maybe_raise_error("salesforce")
    
    def _make_request(self, method, endpoint, object_type, operation="read"):
        """Simulate API request with full validation."""
        self._check_auth()
        self._check_permission(object_type, operation)
        self._check_rate_limit()
        return {"request_id": str(uuid.uuid4())[:8]}
    
    def get_account(self, account_id: str) -> dict:
        """GET /services/data/v59.0/sobjects/Account/{id}"""
        self._make_request("GET", f"/sobjects/Account/{account_id}", "Account")
        
        account = MOCK_ACCOUNTS.get(account_id)
        
        if not account:
            raise SalesforceNotFoundError("Account", account_id)
        
        # Handle error simulation scenarios
        if account.get("_simulate_error") == "authentication":
            raise SalesforceAuthenticationError()
        if account.get("_simulate_error") == "authorization":
            raise SalesforceAuthorizationError("Account", "read")
        
        return account


# High-level function used by the agent
def get_account(account_id: str) -> Optional[dict]:
    """
    Fetch account data, handling all errors gracefully.
    
    Returns:
        - Account dict on success
        - None if not found
        - API_ERROR payload on failure
    """
    client = SalesforceClient()
    
    try:
        return client.get_account(account_id)
    
    except SalesforceNotFoundError:
        log_event("salesforce.account.not_found", account_id=account_id)
        return None
    
    except SalesforceError as e:
        log_event("salesforce.account.error", error=str(e))
        return {
            "status": "API_ERROR",
            "system": "salesforce",
            "error_type": e.category.value,
            "error_code": e.error_code,
            "message": str(e),
            "http_status": e.status_code,
        }
    
    except APIError as e:
        # Catch simulated errors
        log_event("salesforce.account.simulated_error", error=str(e))
        return {
            "status": "API_ERROR",
            "system": "salesforce",
            "error_type": e.category.value if e.category else "unknown",
            "error_code": e.error_code,
            "message": str(e),
            "http_status": e.status_code,
        }
```

**Importance:** Demonstrates production-quality API integration patterns:
- Structured error handling
- Error categorization
- Graceful degradation (returns error payload instead of crashing)
- Simulates real Salesforce API behavior

---

### `app/integrations/clm.py`

**Purpose:** Mock Contract Lifecycle Management API.

**Similar structure to Salesforce, with CLM-specific:**
- Contract status checking
- Signatory tracking
- Document states (DRAFT, SENT, SIGNED, ACTIVATED)

---

### `app/integrations/netsuite.py`

**Purpose:** Mock NetSuite ERP API for invoice data.

**Key features:**
- Invoice status (OPEN, PAID, OVERDUE, VOIDED)
- Payment tracking
- Due date calculations

---

### `app/integrations/provisioning.py`

**Purpose:** SaaS tenant provisioning AND onboarding task management.

**What it does:**

```python
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class TaskCategory(str, Enum):
    AUTOMATED = "automated"
    CS_ACTION = "cs_action"
    CUSTOMER_ACTION = "customer_action"
    TECHNICAL = "technical"


@dataclass
class OnboardingTask:
    task_id: str
    name: str
    description: str
    category: TaskCategory
    owner: str  # "system", "cs_team", "customer"
    status: TaskStatus = TaskStatus.PENDING
    due_date: Optional[str] = None
    completed_at: Optional[str] = None
    completed_by: Optional[str] = None
    depends_on: List[str] = None
    auto_complete: bool = False


# Storage
_PROVISIONED_ACCOUNTS: Dict[str, dict] = {}
_ONBOARDING_TASKS: Dict[str, List[OnboardingTask]] = {}


def _create_onboarding_tasks(account_id: str, tenant_id: str, tier: str, customer_name: str) -> List[OnboardingTask]:
    """Create the 14-task onboarding checklist."""
    now = datetime.utcnow()
    
    tasks = [
        # AUTOMATED (Day 0) - System completes immediately
        OnboardingTask(
            task_id=f"{account_id}-T001",
            name="Create Tenant",
            description=f"Provision tenant {tenant_id}",
            category=TaskCategory.AUTOMATED,
            owner="system",
            status=TaskStatus.COMPLETED,
            completed_at=now.isoformat(),
            completed_by="onboarding_agent",
            auto_complete=True,
        ),
        OnboardingTask(
            task_id=f"{account_id}-T002",
            name="Generate API Credentials",
            description="Create API key for programmatic access",
            category=TaskCategory.AUTOMATED,
            owner="system",
            status=TaskStatus.COMPLETED,
            completed_at=now.isoformat(),
            completed_by="onboarding_agent",
            auto_complete=True,
            depends_on=[f"{account_id}-T001"],
        ),
        OnboardingTask(
            task_id=f"{account_id}-T003",
            name="Send Welcome Email",
            description=f"Send welcome email to {customer_name}",
            category=TaskCategory.AUTOMATED,
            owner="system",
            status=TaskStatus.COMPLETED,
            completed_at=now.isoformat(),
            completed_by="onboarding_agent",
            auto_complete=True,
        ),
        OnboardingTask(
            task_id=f"{account_id}-T004",
            name="Send Training Materials",
            description="Email getting started guides",
            category=TaskCategory.AUTOMATED,
            owner="system",
            status=TaskStatus.COMPLETED,
            completed_at=now.isoformat(),
            completed_by="onboarding_agent",
            auto_complete=True,
            depends_on=[f"{account_id}-T003"],
        ),
        
        # CS TEAM TASKS
        OnboardingTask(
            task_id=f"{account_id}-T005",
            name="Schedule Kickoff Call",
            description="Reach out to schedule initial meeting",
            category=TaskCategory.CS_ACTION,
            owner="cs_team",
            due_date=(now + timedelta(days=1)).strftime("%Y-%m-%d"),
            depends_on=[f"{account_id}-T003"],
        ),
        OnboardingTask(
            task_id=f"{account_id}-T006",
            name="Conduct Kickoff Call",
            description="30-min call to review goals and timeline",
            category=TaskCategory.CS_ACTION,
            owner="cs_team",
            due_date=(now + timedelta(days=3)).strftime("%Y-%m-%d"),
            depends_on=[f"{account_id}-T005"],
        ),
        # ... more CS tasks
        
        # CUSTOMER TASKS
        OnboardingTask(
            task_id=f"{account_id}-T009",
            name="Verify Login Access",
            description="Customer confirms login works",
            category=TaskCategory.CUSTOMER_ACTION,
            owner="customer",
            due_date=(now + timedelta(days=2)).strftime("%Y-%m-%d"),
            depends_on=[f"{account_id}-T003"],
        ),
        OnboardingTask(
            task_id=f"{account_id}-T010",
            name="Complete Platform Tour",
            description="Customer completes in-app tour",
            category=TaskCategory.CUSTOMER_ACTION,
            owner="customer",
            due_date=(now + timedelta(days=5)).strftime("%Y-%m-%d"),
            depends_on=[f"{account_id}-T009"],
        ),
        # ... more customer tasks
        
        # MILESTONE
        OnboardingTask(
            task_id=f"{account_id}-T014",
            name="Onboarding Complete",
            description="Mark onboarding complete, transition to BAU",
            category=TaskCategory.CS_ACTION,
            owner="cs_team",
            due_date=(now + timedelta(days=45)).strftime("%Y-%m-%d"),
            depends_on=[f"{account_id}-T012", f"{account_id}-T013"],
        ),
    ]
    
    return tasks


def provision_account(account_id: str, tier: str = "Starter", customer_name: str = "Customer") -> dict:
    """
    Provision tenant AND create onboarding task checklist.
    """
    if account_id in _PROVISIONED_ACCOUNTS:
        return _PROVISIONED_ACCOUNTS[account_id]
    
    tenant_id = f"TEN-{uuid.uuid4().hex[:8].upper()}"
    
    # Create the 14 tasks
    tasks = _create_onboarding_tasks(account_id, tenant_id, tier, customer_name)
    _ONBOARDING_TASKS[account_id] = tasks
    
    # Calculate progress summary
    task_summary = _get_task_summary(tasks)
    
    result = {
        "tenant_id": tenant_id,
        "account_id": account_id,
        "status": "ACTIVE",
        "tier": tier,
        "provisioned_at": datetime.utcnow().isoformat(),
        "config": TIER_CONFIGS[tier],
        "admin_url": f"https://app.stackadapt.demo/admin/{tenant_id}",
        "api_key": f"sk_live_{uuid.uuid4().hex}",
        "onboarding_tasks": task_summary,
    }
    
    _PROVISIONED_ACCOUNTS[account_id] = result
    return result


def get_onboarding_tasks(account_id: str) -> List[dict]:
    """Get all tasks for an account."""
    tasks = _ONBOARDING_TASKS.get(account_id, [])
    return [t.to_dict() for t in tasks]


def update_task_status(account_id: str, task_id: str, status: str, 
                       completed_by: str = None) -> Optional[dict]:
    """Update a task's status (called by CS team or webhooks)."""
    tasks = _ONBOARDING_TASKS.get(account_id, [])
    
    for task in tasks:
        if task.task_id == task_id:
            task.status = TaskStatus(status)
            if status == "completed":
                task.completed_at = datetime.utcnow().isoformat()
                task.completed_by = completed_by
            return task.to_dict()
    
    return None


def get_overdue_tasks(account_id: str) -> List[dict]:
    """Get tasks past due date - for proactive alerting."""
    tasks = _ONBOARDING_TASKS.get(account_id, [])
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    return [
        t.to_dict() for t in tasks
        if t.due_date and t.due_date < today 
        and t.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]
    ]
```

**Importance:** This is the key differentiator - it shows the granular CS workflow:
- Automated tasks complete immediately
- CS tasks have due dates and dependencies
- Customer tasks track their engagement
- Overdue detection enables proactive outreach

---

## 5. LLM Integration

### `app/llm/risk_analyzer.py`

**Purpose:** LLM-powered risk analysis with rule-based fallback.

**What it does:**

```python
import os
import json
from typing import Optional

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


RISK_ANALYSIS_SYSTEM_PROMPT = """You are an AI assistant helping Customer Success teams understand onboarding issues.

Analyze the current state and provide:
1. A clear, human-readable summary
2. Risk level assessment (low/medium/high/critical)
3. Specific, actionable recommendations with owners

Format response as JSON:
{
    "summary": "Brief overview",
    "risk_level": "low|medium|high|critical",
    "risks": [{"issue": "...", "impact": "...", "urgency": "..."}],
    "recommended_actions": [{"action": "...", "owner": "...", "priority": 1}],
    "estimated_resolution_time": "...",
    "can_proceed_with_warnings": true/false
}"""


def analyze_risks(state: dict) -> dict:
    """
    Main entry point for risk analysis.
    
    Tries LLM first, falls back to rule-based if unavailable.
    """
    context = _build_analysis_context(state)
    
    api_key = os.getenv("OPENAI_API_KEY")
    
    if api_key and OPENAI_AVAILABLE:
        try:
            return _llm_analyze(context, state)
        except Exception as e:
            log_event("llm.risk_analysis.error", error=str(e))
    
    # Fallback to rule-based
    return _rule_based_analyze(state)


def _build_analysis_context(state: dict) -> str:
    """Build context string for LLM prompt."""
    sections = []
    
    # Account info
    account = state.get("account")
    if account:
        sections.append(f"""ACCOUNT:
- Name: {account.get('Name', 'Unknown')}
- Industry: {account.get('Industry', 'Not specified')}
- Country: {account.get('BillingCountry', 'Not specified')}""")
    else:
        sections.append("ACCOUNT: Missing")
    
    # API Errors
    api_errors = state.get("api_errors", [])
    if api_errors:
        error_lines = []
        for err in api_errors:
            error_lines.append(f"- {err['system']}: {err['error_type']} - {err['message']}")
        sections.append(f"API ERRORS:\n" + "\n".join(error_lines))
    
    # Violations
    violations = state.get("violations", {})
    if any(violations.values()):
        sections.append("VIOLATIONS:")
        for category, issues in violations.items():
            for issue in issues:
                sections.append(f"- [{category}] {issue}")
    
    # Warnings
    warnings = state.get("warnings", {})
    if any(warnings.values()):
        sections.append("WARNINGS:")
        for category, issues in warnings.items():
            for issue in issues:
                sections.append(f"- [{category}] {issue}")
    
    return "\n\n".join(sections)


def _llm_analyze(context: str, state: dict) -> dict:
    """Call OpenAI API for analysis."""
    client = OpenAI()
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": RISK_ANALYSIS_SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyze this onboarding state:\n\n{context}"}
        ],
        temperature=0.3,
        response_format={"type": "json_object"}
    )
    
    result = json.loads(response.choices[0].message.content)
    
    log_event("llm.risk_analysis.success", 
              risk_level=result.get("risk_level"),
              tokens_used=response.usage.total_tokens)
    
    return result


def _rule_based_analyze(state: dict) -> dict:
    """
    Deterministic fallback when LLM is unavailable.
    
    Uses simple rules to generate analysis.
    """
    api_errors = state.get("api_errors", [])
    violations = state.get("violations", {})
    warnings = state.get("warnings", {})
    
    api_error_count = len(api_errors)
    violation_count = sum(len(v) for v in violations.values())
    warning_count = sum(len(w) for w in warnings.values())
    
    # Determine risk level
    if api_error_count > 0:
        risk_level = "critical"
    elif violation_count > 0:
        risk_level = "high"
    elif warning_count > 2:
        risk_level = "medium"
    elif warning_count > 0:
        risk_level = "low"
    else:
        risk_level = "low"
    
    # Build risks list
    risks = []
    
    for error in api_errors:
        risks.append({
            "issue": f"{error['system']} API Error: {error['error_type']}",
            "impact": "Cannot fetch required data - onboarding blocked",
            "urgency": "critical"
        })
    
    for category, issues in violations.items():
        for issue in issues:
            risks.append({
                "issue": issue,
                "impact": f"Blocks onboarding - {category} validation failed",
                "urgency": "high"
            })
    
    # Build recommendations
    recommendations = []
    priority = 1
    
    if api_error_count > 0:
        recommendations.append({
            "action": "Resolve API connectivity issues",
            "owner": "IT/Technical Support",
            "priority": priority
        })
        priority += 1
    
    if violation_count > 0:
        recommendations.append({
            "action": "Address data validation issues before proceeding",
            "owner": "Customer Success",
            "priority": priority
        })
    
    # Build summary
    if api_error_count > 0:
        summary = f"Onboarding blocked due to {api_error_count} API error(s). Technical intervention required."
    elif violation_count > 0:
        summary = f"Onboarding blocked due to {violation_count} validation issue(s)."
    elif warning_count > 0:
        summary = f"Onboarding can proceed with {warning_count} warning(s) requiring attention."
    else:
        summary = "Onboarding ready to proceed. All checks passed."
    
    return {
        "summary": summary,
        "risk_level": risk_level,
        "risks": risks,
        "recommended_actions": recommendations,
        "estimated_resolution_time": _estimate_resolution_time(api_error_count, violation_count),
        "can_proceed_with_warnings": violation_count == 0 and api_error_count == 0
    }


def _estimate_resolution_time(api_errors: int, violations: int) -> str:
    if api_errors > 0:
        return "1-4 hours (technical fix required)"
    elif violations > 2:
        return "1-2 weeks"
    elif violations > 0:
        return "2-3 days"
    else:
        return "Immediate"
```

**Importance:** 
- LLM provides intelligent, context-aware analysis
- Fallback ensures system works without OpenAI API key
- Both paths produce consistent output format

---

## 6. Notifications

### `app/notifications/notifier.py`

**Purpose:** Send Slack and email notifications.

**What it does:**

```python
from datetime import datetime
from typing import Optional, List

# In-memory store for sent notifications (for demo)
_SENT_NOTIFICATIONS: List[dict] = []


def notify_cs_team_success(account_name: str, account_id: str, 
                           tenant_id: str, correlation_id: str) -> dict:
    """Send success notification to Slack."""
    message = f"""✅ *Onboarding Complete* for {account_name}

The customer has been successfully provisioned and is ready to use the platform.

*Details:*
• Tenant ID: `{tenant_id}`
• Status: Active

*Next Steps:*
• Schedule kickoff call with customer
• Send welcome email with login credentials
• Assign to onboarding specialist

<https://app.demo/admin/{tenant_id}|View Tenant> | <https://agent.demo/runs/{correlation_id}|View Agent Run>
"""
    
    notification = {
        "type": "slack",
        "channel": "#cs-onboarding",
        "message": message,
        "urgency": "low",
        "account_id": account_id,
        "correlation_id": correlation_id,
        "sent_at": datetime.utcnow().isoformat(),
        "status": "sent"
    }
    
    _SENT_NOTIFICATIONS.append(notification)
    log_event("notification.slack.sent", channel="#cs-onboarding", account_id=account_id)
    
    return notification


def notify_cs_team_blocked(account_name: str, account_id: str,
                           violations: dict, api_errors: list,
                           correlation_id: str) -> dict:
    """Send BLOCK alert to Slack."""
    
    # Format violations
    violation_lines = []
    for category, issues in violations.items():
        for issue in issues:
            violation_lines.append(f"• [{category}] {issue}")
    
    # Format API errors
    error_lines = []
    for error in api_errors:
        error_lines.append(f"• {error['system']}: {error['message']}")
    
    message = f"""🚫 *Onboarding BLOCKED* for {account_name}

The onboarding cannot proceed due to critical issues.

*Violations:*
{chr(10).join(violation_lines) if violation_lines else "None"}

*API Errors:*
{chr(10).join(error_lines) if error_lines else "None"}

*Action Required:* Review and resolve issues before retrying.

<https://agent.demo/runs/{correlation_id}|View Details>
"""
    
    notification = {
        "type": "slack",
        "channel": "#cs-onboarding-alerts",
        "message": message,
        "urgency": "high",
        "account_id": account_id,
        "correlation_id": correlation_id,
        "sent_at": datetime.utcnow().isoformat(),
        "status": "sent"
    }
    
    _SENT_NOTIFICATIONS.append(notification)
    return notification


def send_customer_welcome_email(to_email: str, customer_name: str,
                                tenant_id: str, account_id: str) -> dict:
    """Send welcome email to customer."""
    
    subject = f"Welcome to StackAdapt, {customer_name}!"
    
    body = f"""Hi {customer_name},

Welcome to StackAdapt! Your account has been provisioned and you're ready to get started.

Here are your account details:
- Tenant ID: {tenant_id}
- Login URL: https://app.stackadapt.demo/login

Getting Started:
1. Log in using your email address
2. Complete the platform tour
3. Set up your first campaign

Your Customer Success Manager will reach out shortly to schedule a kickoff call.

If you have any questions, don't hesitate to reach out.

Best regards,
The StackAdapt Team
"""
    
    notification = {
        "type": "email",
        "to": to_email,
        "subject": subject,
        "body": body,
        "template": "customer_welcome",
        "account_id": account_id,
        "sent_at": datetime.utcnow().isoformat(),
        "status": "sent"
    }
    
    _SENT_NOTIFICATIONS.append(notification)
    return notification


def get_sent_notifications(account_id: str = None) -> List[dict]:
    """Get sent notifications, optionally filtered by account."""
    if account_id:
        return [n for n in _SENT_NOTIFICATIONS if n.get("account_id") == account_id]
    return _SENT_NOTIFICATIONS


def clear_notifications():
    """Clear all notifications (for testing)."""
    _SENT_NOTIFICATIONS.clear()
```

**Importance:** Demonstrates multi-channel notification with:
- Different urgency levels
- Context-rich messages with action links
- Separation of internal (Slack) vs external (email) communications

---

## 7. Reports

### `app/reports/generator.py`

**Purpose:** Generate professional HTML, Markdown, and JSON reports.

**What it does:**

```python
import os
from datetime import datetime
from typing import Dict, Any

REPORTS_DIR = os.path.abspath("reports_output")


def generate_run_report_markdown(state: dict) -> str:
    """Generate detailed Markdown report."""
    
    account_id = state.get("account_id", "Unknown")
    decision = state.get("decision", "Unknown")
    risk_analysis = state.get("risk_analysis", {})
    
    # Header
    md = f"""# Onboarding Run Report

## Summary

| Field | Value |
|-------|-------|
| **Account** | {state.get('account', {}).get('Name', account_id)} |
| **Correlation ID** | `{state.get('correlation_id')}` |
| **Decision** | {'✅' if decision == 'PROCEED' else '🚫' if decision == 'BLOCK' else '⚠️'} **{decision}** |
| **Risk Level** | {risk_analysis.get('risk_level', 'N/A').upper()} |

---

## Risk Analysis

### Summary
{risk_analysis.get('summary', 'No analysis available.')}

### Recommended Actions
"""
    
    # Add recommendations
    for i, action in enumerate(risk_analysis.get('recommended_actions', []), 1):
        md += f"{i}. {action.get('action')} _(Owner: {action.get('owner')})_\n"
    
    # Add violations
    md += "\n---\n\n## Validation Results\n\n"
    
    violations = state.get("violations", {})
    if any(violations.values()):
        md += "### Critical Violations (Blocking)\n"
        for category, issues in violations.items():
            for issue in issues:
                md += f"- **{category}**: {issue}\n"
    
    warnings = state.get("warnings", {})
    if any(warnings.values()):
        md += "\n### Warnings (Non-blocking)\n"
        for category, issues in warnings.items():
            for issue in issues:
                md += f"- **{category}**: {issue}\n"
    
    # Add provisioning info
    provisioning = state.get("provisioning")
    if provisioning:
        task_summary = provisioning.get("onboarding_tasks", {})
        md += f"""
---

## Provisioning

| Field | Value |
|-------|-------|
| **Tenant ID** | `{provisioning.get('tenant_id')}` |
| **Tier** | {provisioning.get('tier')} |
| **Tasks Created** | {task_summary.get('total_tasks', 0)} |
| **Completed** | {task_summary.get('completed', 0)} |
| **Progress** | {task_summary.get('completion_percentage', 0)}% |
"""
    
    # Footer
    md += f"""
---

## Audit Information

- **Run ID**: `{state.get('correlation_id')}`
- **Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

---

_This report was automatically generated by the Enterprise Onboarding Agent._
"""
    
    return md


def generate_blocked_email_html(state: dict) -> str:
    """Generate HTML email for BLOCKED scenarios."""
    # Returns styled HTML email template
    pass


def generate_success_email_html(state: dict) -> str:
    """Generate HTML email for successful onboarding."""
    pass


def generate_audit_json(state: dict) -> str:
    """Generate JSON audit log."""
    import json
    
    audit = {
        "run_id": state.get("correlation_id"),
        "account_id": state.get("account_id"),
        "decision": state.get("decision"),
        "timestamp": datetime.utcnow().isoformat(),
        "stages_completed": state.get("stage"),
        "api_errors": state.get("api_errors", []),
        "violations": state.get("violations", {}),
        "warnings": state.get("warnings", {}),
        "risk_analysis": state.get("risk_analysis", {}),
        "actions_taken": state.get("actions_taken", []),
        "provisioning": state.get("provisioning"),
    }
    
    return json.dumps(audit, indent=2)


def save_report_markdown(content: str, account_id: str) -> str:
    """Save Markdown report to file."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"run_report_{account_id}_{timestamp}.md"
    filepath = os.path.join(REPORTS_DIR, filename)
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    return filepath


def generate_full_run_report(state: dict) -> Dict[str, str]:
    """Generate all report types and save to files."""
    account_id = state.get("account_id", "unknown")
    
    generated_files = {}
    
    # Markdown report
    md_content = generate_run_report_markdown(state)
    generated_files["markdown"] = save_report_markdown(md_content, account_id)
    
    # HTML email
    decision = state.get("decision")
    if decision == "BLOCK":
        html_content = generate_blocked_email_html(state)
        generated_files["email_html"] = save_report_html(html_content, f"email_blocked_{account_id}")
    elif decision == "PROCEED":
        html_content = generate_success_email_html(state)
        generated_files["email_html"] = save_report_html(html_content, f"email_success_{account_id}")
    
    # JSON audit
    json_content = generate_audit_json(state)
    generated_files["audit_json"] = save_report_json(json_content, account_id)
    
    return generated_files
```

**Importance:** Professional reporting for:
- Human review (Markdown/HTML)
- Machine processing (JSON)
- Audit compliance (full state capture)

---

## 8. API Layer

### `app/api/demo.py`

**Purpose:** Demo and testing endpoints.

**Key endpoints:**

```python
from fastapi import APIRouter
from app.agent import run_onboarding
from app.integrations import provisioning
from app.integrations.api_errors import enable_error_simulation, disable_error_simulation

router = APIRouter(tags=["demo"])


# ============== SCENARIO RUNNING ==============

@router.post("/run/{account_id}")
async def run_demo_scenario(account_id: str, generate_report: bool = False):
    """Run a specific demo scenario."""
    result = run_onboarding(account_id=account_id, event_type="demo.trigger")
    
    response = {
        "account_id": account_id,
        "decision": result.get("decision"),
        "risk_analysis": result.get("risk_analysis"),
        "violations": result.get("violations"),
        "warnings": result.get("warnings"),
        "provisioning": result.get("provisioning"),
    }
    
    if generate_report and not is_error_simulation_scenario(account_id):
        files = generate_full_run_report(result)
        response["generated_reports"] = files
    
    return response


@router.post("/run-all")
async def run_all_scenarios(generate_reports: bool = False):
    """Run all demo scenarios and return summary."""
    results = []
    
    for scenario in ALL_SCENARIOS:
        result = run_onboarding(account_id=scenario["id"], event_type="demo.batch")
        results.append({
            "account_id": scenario["id"],
            "expected": scenario["expected_decision"],
            "actual": result.get("decision"),
            "passed": result.get("decision") == scenario["expected_decision"]
        })
    
    return {
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r["passed"]),
        },
        "results": results
    }


# ============== ERROR SIMULATION ==============

@router.post("/enable-random-errors")
async def enable_random_errors(
    auth_rate: float = 0.05,
    validation_rate: float = 0.05,
    rate_limit_rate: float = 0.02,
    server_error_rate: float = 0.01
):
    """Enable error injection for testing."""
    enable_error_simulation(
        auth_rate=auth_rate,
        validation_rate=validation_rate,
        rate_limit_rate=rate_limit_rate,
        server_error_rate=server_error_rate
    )
    return {"status": "enabled", "rates": {...}}


@router.post("/disable-random-errors")
async def disable_random_errors():
    """Disable error injection."""
    disable_error_simulation()
    return {"status": "disabled"}


# ============== TASK MANAGEMENT ==============

@router.get("/tasks/{account_id}")
async def get_onboarding_tasks(account_id: str):
    """Get all onboarding tasks for an account."""
    tasks = provisioning.get_onboarding_tasks(account_id)
    return {"account_id": account_id, "tasks": tasks}


@router.get("/tasks/{account_id}/overdue")
async def get_overdue_tasks(account_id: str):
    """Get overdue tasks for proactive alerting."""
    overdue = provisioning.get_overdue_tasks(account_id)
    return {
        "account_id": account_id,
        "overdue_count": len(overdue),
        "alert_level": "critical" if len(overdue) > 3 else "warning" if overdue else "ok",
        "tasks": overdue
    }


@router.put("/tasks/{account_id}/{task_id}")
async def update_task_status(account_id: str, task_id: str, status: str):
    """Update task status (CS team action)."""
    updated = provisioning.update_task_status(account_id, task_id, status)
    return {"task": updated}


# ============== REPORTS ==============

@router.get("/reports")
async def list_reports():
    """List all generated reports."""
    files = os.listdir(REPORTS_DIR)
    return {"reports": files}


@router.get("/reports/{filename}")
async def get_report(filename: str):
    """Get a specific report file."""
    # Returns HTML response for browser viewing
    pass
```

**Importance:** Provides the HTTP interface for:
- Running scenarios
- Testing error handling
- Managing onboarding tasks
- Viewing reports

---

### `app/api/webhook.py`

**Purpose:** Production webhook handlers.

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["webhooks"])


class TriggerEvent(BaseModel):
    account_id: str
    event_type: str = "webhook"
    source: str = "salesforce"
    payload: dict = {}


class OnboardingResponse(BaseModel):
    account_id: str
    decision: str
    correlation_id: str
    summary: str


@router.post("/webhook/onboarding", response_model=OnboardingResponse)
async def onboarding_webhook(event: TriggerEvent):
    """
    Main webhook for triggering onboarding.
    
    Called by Salesforce when Opportunity stage = Closed Won.
    """
    log_event("webhook.received", 
              account_id=event.account_id, 
              source=event.source)
    
    result = run_onboarding(
        account_id=event.account_id,
        event_type=event.event_type
    )
    
    return OnboardingResponse(
        account_id=event.account_id,
        decision=result.get("decision"),
        correlation_id=result.get("correlation_id"),
        summary=result.get("human_summary", "")
    )
```

**Importance:** Production-ready endpoint with:
- Pydantic validation
- Structured logging
- Typed responses

---

## 9. Data Flow Walkthrough

Let's trace a complete request through the system:

### Request: `POST /demo/run/ACME-001`

```
1. API LAYER (demo.py)
   └── run_demo_scenario("ACME-001")
       └── run_onboarding(account_id="ACME-001")

2. GRAPH INITIALIZATION (graph.py)
   └── graph.invoke(initial_state)
       initial_state = {
         "account_id": "ACME-001",
         "correlation_id": "abc-123",
         "stage": "initializing"
       }

3. NODE: initialize (nodes.py)
   └── Sets correlation_id, timestamps
   └── state["stage"] = "initializing"

4. NODE: fetch_salesforce_data
   └── salesforce.get_account("ACME-001")
       └── SalesforceClient._check_auth()
           └── ERROR_SIMULATOR.maybe_raise_error("salesforce")
               └── (no error if disabled)
       └── Returns MOCK_ACCOUNTS["ACME-001"]
   └── state["account"] = {...}
   └── salesforce.get_user(owner_id)
   └── salesforce.get_opportunity(opp_id)

5. NODE: fetch_clm_data
   └── clm.get_contract("ACME-001")
   └── state["clm"] = {...}

6. NODE: fetch_netsuite_data
   └── netsuite.get_invoice("ACME-001")
   └── state["invoice"] = {...}

7. NODE: validate_invariants
   └── check_account_invariants(state["account"])
       └── Returns ([], [])  # No violations, no warnings
   └── check_opportunity_invariants(...)
       └── Stage = "Closed Won" ✓
   └── check_contract_invariants(...)
   └── check_invoice_invariants(...)
   └── state["violations"] = {account: [], opportunity: [], ...}
   └── state["warnings"] = {...}

8. NODE: analyze_risks (risk_analyzer.py)
   └── _build_analysis_context(state)
   └── _llm_analyze(context) OR _rule_based_analyze(state)
   └── state["risk_analysis"] = {
         "summary": "Ready to proceed",
         "risk_level": "low",
         "can_proceed_with_warnings": true
       }

9. NODE: make_decision
   └── api_error_count = 0
   └── violation_count = 0
   └── warning_count = 0
   └── state["decision"] = "PROCEED"

10. ROUTER: route_decision (router.py)
    └── decision == "PROCEED" → return "provision"

11. NODE: provision_account
    └── provisioning.provision_account("ACME-001", "Enterprise", "ACME Corp")
        └── Creates tenant TEN-E2B91C6D
        └── Creates 14 onboarding tasks
        └── 4 auto-complete immediately
    └── state["provisioning"] = {
          "tenant_id": "TEN-E2B91C6D",
          "onboarding_tasks": {"total": 14, "completed": 4}
        }

12. NODE: send_notifications
    └── notifier.notify_cs_team_success(...)
        └── Sends to #cs-onboarding
    └── notifier.send_customer_welcome_email(...)
        └── Sends welcome email

13. NODE: generate_summary
    └── state["human_summary"] = "ACME Corp onboarding complete"
    └── state["stage"] = "complete"

14. RETURN TO API
    └── Returns final state as JSON response
```

---

## 10. Key Design Patterns

### Pattern 1: Error Payload Instead of Exception

```python
# Instead of letting exceptions bubble up:
try:
    account = client.get_account(id)
except SalesforceError as e:
    return {"status": "API_ERROR", "message": str(e), ...}

# This allows the workflow to continue and record the error
```

### Pattern 2: In-Place Singleton Modification

```python
# Wrong: Replacing the global breaks module references
ERROR_SIMULATOR = ErrorSimulator(enabled=True)  # Other modules still have old ref

# Right: Modify in place
ERROR_SIMULATOR.enabled = True
ERROR_SIMULATOR.auth_rate = 0.5
```

### Pattern 3: Tiered Validation

```python
# Violations BLOCK - these are critical
if not opportunity or opportunity.get("StageName") != "Closed Won":
    violations.append("Opportunity not won")

# Warnings ESCALATE - these need attention but don't block
if not account.get("BillingStreet"):
    warnings.append("Billing address incomplete")
```

### Pattern 4: LLM with Fallback

```python
def analyze(state):
    if llm_available():
        try:
            return llm_analyze(state)
        except:
            pass
    return rule_based_analyze(state)  # Always works
```

### Pattern 5: Task Dependencies

```python
# Tasks can depend on other tasks
OnboardingTask(
    task_id="T006",
    name="Conduct Kickoff Call",
    depends_on=["T005"],  # Must complete "Schedule Kickoff" first
)
```

---

## Summary

This codebase demonstrates a production-minded AI agent with:

1. **Clean Architecture**: Separation of concerns (agent, integrations, API, notifications)
2. **Robust Error Handling**: Errors are caught, recorded, and influence decisions
3. **LLM Integration**: With graceful fallback to rule-based logic
4. **Task Management**: Granular tracking of the CS workflow
5. **Full Observability**: Logging, tracing, and reporting at every step
6. **Testability**: Error simulation, mock APIs, standalone demo mode

The agent can be extended by:
- Adding new integration modules
- Creating additional invariant checks
- Expanding the task checklist
- Implementing real API connections
- Adding human-in-the-loop approval flows
