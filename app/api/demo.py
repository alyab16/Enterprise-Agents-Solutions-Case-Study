"""
Demo API endpoints for showcasing the agent.
"""

from fastapi import APIRouter
from app.agent import run_onboarding
from app.notifications import get_sent_notifications, clear_notifications
from app.integrations.provisioning import reset_all as reset_provisioning
from app.integrations.api_errors import enable_error_simulation, disable_error_simulation

router = APIRouter()


@router.get("/scenarios")
async def list_scenarios():
    """List available demo scenarios."""
    return {
        "scenarios": [
            # ===== NORMAL SCENARIOS =====
            {
                "id": "ACME-001",
                "name": "Happy Path - Full Success",
                "description": "Complete onboarding with no issues. Account provisioned.",
                "expected_decision": "PROCEED",
                "category": "normal",
            },
            {
                "id": "BETA-002", 
                "name": "Blocked - Opportunity Not Won",
                "description": "Opportunity still in negotiation stage. Cannot proceed.",
                "expected_decision": "BLOCK",
                "category": "normal",
            },
            {
                "id": "GAMMA-003",
                "name": "Escalation - Overdue Invoice",
                "description": "Overdue invoice triggers finance escalation.",
                "expected_decision": "ESCALATE",
                "category": "normal",
            },
            {
                "id": "DELETED-004",
                "name": "Blocked - Invalid Account",
                "description": "Account marked as deleted in Salesforce.",
                "expected_decision": "BLOCK",
                "category": "normal",
            },
            {
                "id": "MISSING-999",
                "name": "Blocked - Account Not Found",
                "description": "Account does not exist in any system.",
                "expected_decision": "BLOCK",
                "category": "normal",
            },
            # ===== ERROR SIMULATION SCENARIOS =====
            {
                "id": "AUTH-ERROR",
                "name": "API Authentication Failure",
                "description": "Simulates Salesforce session expired or invalid credentials.",
                "expected_decision": "BLOCK",
                "category": "error_simulation",
                "error_type": "authentication",
            },
            {
                "id": "PERM-ERROR",
                "name": "API Permission Denied",
                "description": "Simulates user lacking permissions to access Salesforce objects.",
                "expected_decision": "BLOCK",
                "category": "error_simulation",
                "error_type": "authorization",
            },
            {
                "id": "SERVER-ERROR",
                "name": "API Server Error",
                "description": "Simulates Salesforce/NetSuite server returning 500 error.",
                "expected_decision": "BLOCK",
                "category": "error_simulation",
                "error_type": "server",
            },
        ]
    }


@router.post("/run/{account_id}")
async def run_demo_scenario(account_id: str):
    """
    Run a specific demo scenario by account ID.
    
    Returns the full agent execution result.
    """
    # Clear previous notifications for clean demo
    clear_notifications()
    
    # Run the onboarding
    result = run_onboarding(
        account_id=account_id,
        event_type="demo.trigger",
    )
    
    # Get notifications that were sent
    notifications = get_sent_notifications(account_id)
    
    return {
        "account_id": account_id,
        "decision": result.get("decision"),
        "stage": result.get("stage"),
        "risk_analysis": result.get("risk_analysis"),
        "violations": result.get("violations"),
        "warnings": result.get("warnings"),
        "actions_taken": result.get("actions_taken"),
        "notifications_sent": notifications,
        "provisioning": result.get("provisioning"),
        "recommended_actions": result.get("recommended_actions"),
    }


@router.post("/run-all")
async def run_all_scenarios():
    """Run all demo scenarios and return results."""
    
    # Reset state
    clear_notifications()
    reset_provisioning()
    
    scenarios = ["ACME-001", "BETA-002", "GAMMA-003", "DELETED-004", "MISSING-999"]
    results = []
    
    for account_id in scenarios:
        result = run_onboarding(
            account_id=account_id,
            event_type="demo.batch",
        )
        
        results.append({
            "account_id": account_id,
            "decision": result.get("decision"),
            "stage": result.get("stage"),
            "risk_level": result.get("risk_analysis", {}).get("risk_level"),
            "violation_count": sum(len(v) for v in result.get("violations", {}).values()),
            "warning_count": sum(len(v) for v in result.get("warnings", {}).values()),
            "provisioned": result.get("provisioning") is not None,
        })
    
    return {"results": results}


@router.post("/run-error-scenarios")
async def run_error_scenarios():
    """Run all error simulation scenarios."""
    
    clear_notifications()
    reset_provisioning()
    
    # Error simulation scenarios
    error_scenarios = ["AUTH-ERROR", "PERM-ERROR", "SERVER-ERROR"]
    results = []
    
    for account_id in error_scenarios:
        result = run_onboarding(
            account_id=account_id,
            event_type="demo.error_test",
        )
        
        results.append({
            "account_id": account_id,
            "decision": result.get("decision"),
            "stage": result.get("stage"),
            "violations": result.get("violations"),
            "warnings": result.get("warnings"),
            "error_details": {
                "category": "error_simulation",
                "description": f"Simulated API error for {account_id}",
            }
        })
    
    return {"results": results}


@router.post("/enable-random-errors")
async def enable_random_errors(
    auth_rate: float = 0.05,
    validation_rate: float = 0.05,
    rate_limit_rate: float = 0.02,
    server_error_rate: float = 0.01
):
    """
    Enable random error injection for stress testing.
    
    Rates are probabilities (0.0 to 1.0) for each error type.
    
    Example: auth_rate=0.1 means 10% of requests will get auth errors.
    """
    enable_error_simulation(
        auth_rate=auth_rate,
        validation_rate=validation_rate,
        rate_limit_rate=rate_limit_rate,
        server_error_rate=server_error_rate
    )
    return {
        "status": "enabled",
        "rates": {
            "authentication": auth_rate,
            "validation": validation_rate,
            "rate_limit": rate_limit_rate,
            "server_error": server_error_rate,
        }
    }


@router.post("/disable-random-errors")
async def disable_random_errors():
    """Disable random error injection."""
    disable_error_simulation()
    return {"status": "disabled"}


@router.get("/notifications")
async def get_notifications():
    """Get all notifications sent during demo runs."""
    return {"notifications": get_sent_notifications()}


@router.post("/reset")
async def reset_demo():
    """Reset demo state (clear notifications and provisioning)."""
    clear_notifications()
    reset_provisioning()
    disable_error_simulation()
    return {"status": "reset", "message": "Demo state cleared"}
