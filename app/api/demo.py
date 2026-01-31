"""
Demo API endpoints for showcasing the agent.
"""

from fastapi import APIRouter
from app.agent import run_onboarding
from app.notifications import get_sent_notifications, clear_notifications
from app.integrations.provisioning import reset_all as reset_provisioning

router = APIRouter()


@router.get("/scenarios")
async def list_scenarios():
    """List available demo scenarios."""
    return {
        "scenarios": [
            {
                "id": "ACME-001",
                "name": "Happy Path - Full Success",
                "description": "Complete onboarding with no issues. Account provisioned.",
                "expected_decision": "PROCEED",
            },
            {
                "id": "BETA-002", 
                "name": "Blocked - Opportunity Not Won",
                "description": "Opportunity still in negotiation stage. Cannot proceed.",
                "expected_decision": "BLOCK",
            },
            {
                "id": "GAMMA-003",
                "name": "Escalation - Overdue Invoice",
                "description": "Overdue invoice triggers finance escalation.",
                "expected_decision": "ESCALATE",
            },
            {
                "id": "DELETED-004",
                "name": "Blocked - Invalid Account",
                "description": "Account marked as deleted in Salesforce.",
                "expected_decision": "BLOCK",
            },
            {
                "id": "MISSING-999",
                "name": "Blocked - Account Not Found",
                "description": "Account does not exist in any system.",
                "expected_decision": "BLOCK",
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


@router.get("/notifications")
async def get_notifications():
    """Get all notifications sent during demo runs."""
    return {"notifications": get_sent_notifications()}


@router.post("/reset")
async def reset_demo():
    """Reset demo state (clear notifications and provisioning)."""
    clear_notifications()
    reset_provisioning()
    return {"status": "reset", "message": "Demo state cleared"}
