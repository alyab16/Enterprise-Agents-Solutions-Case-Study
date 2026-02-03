"""
Demo API endpoints for showcasing the agent.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, FileResponse
from app.agent import run_onboarding
from app.notifications import get_sent_notifications, clear_notifications
from app.integrations.provisioning import reset_all as reset_provisioning
from app.integrations.api_errors import enable_error_simulation, disable_error_simulation
from app.reports import generate_full_run_report, REPORTS_DIR
import os

router = APIRouter()

# All demo scenarios - both normal and error simulation
ALL_SCENARIOS = [
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
]


# Error simulation scenario IDs - these are not real accounts
ERROR_SIMULATION_IDS = {"AUTH-ERROR", "PERM-ERROR", "SERVER-ERROR", "RATE-ERROR", "VALIDATION-ERROR"}


def is_error_simulation_scenario(account_id: str) -> bool:
    """Check if an account_id is an error simulation scenario (not a real account)."""
    return account_id in ERROR_SIMULATION_IDS or account_id.endswith("-ERROR")


@router.get("/scenarios")
async def list_scenarios():
    """List available demo scenarios."""
    return {"scenarios": ALL_SCENARIOS}


@router.post("/run/{account_id}")
async def run_demo_scenario(account_id: str, generate_report: bool = False):
    """
    Run a specific demo scenario by account ID.
    
    Args:
        account_id: The scenario ID to run (e.g., ACME-001, AUTH-ERROR)
        generate_report: If true, also generates HTML/Markdown/JSON reports
                        (Note: Reports are NOT generated for error simulation scenarios)
    
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
    
    response = {
        "account_id": account_id,
        "decision": result.get("decision"),
        "stage": result.get("stage"),
        "risk_analysis": result.get("risk_analysis"),
        "violations": result.get("violations"),
        "warnings": result.get("warnings"),
        "actions_taken": result.get("actions_taken"),
        "notifications_sent": notifications,
        "provisioning": result.get("provisioning"),
        "summary": result.get("human_summary"),
    }
    
    # Optionally generate reports (but NOT for error simulation scenarios)
    if generate_report:
        if is_error_simulation_scenario(account_id):
            response["generated_reports"] = None
            response["report_skipped_reason"] = "Reports are not generated for error simulation scenarios"
        else:
            generated_files = generate_full_run_report(result)
            response["generated_reports"] = {
                k: os.path.basename(v) for k, v in generated_files.items()
            }
    
    return response


@router.post("/run-all")
async def run_all_scenarios(generate_reports: bool = False):
    """
    Run ALL demo scenarios (normal + error simulations) and return results.
    
    Args:
        generate_reports: If true, generates HTML/Markdown/JSON reports for each scenario
                         (Note: Reports are NOT generated for error simulation scenarios)
    
    Returns summary of all scenario executions.
    """
    # Reset state
    clear_notifications()
    reset_provisioning()
    
    results = []
    generated_reports = []
    
    for scenario in ALL_SCENARIOS:
        account_id = scenario["id"]
        
        result = run_onboarding(
            account_id=account_id,
            event_type="demo.batch",
        )
        
        scenario_result = {
            "account_id": account_id,
            "scenario_name": scenario["name"],
            "category": scenario["category"],
            "expected_decision": scenario["expected_decision"],
            "actual_decision": result.get("decision"),
            "passed": result.get("decision") == scenario["expected_decision"],
            "stage": result.get("stage"),
            "risk_level": result.get("risk_analysis", {}).get("risk_level"),
            "violation_count": sum(len(v) for v in result.get("violations", {}).values()),
            "warning_count": sum(len(v) for v in result.get("warnings", {}).values()),
            "api_error_count": len(result.get("api_errors", [])),
            "provisioned": result.get("provisioning") is not None,
        }
        
        # Add error details for error simulation scenarios
        if scenario["category"] == "error_simulation":
            scenario_result["error_type"] = scenario.get("error_type")
        
        results.append(scenario_result)
        
        # Generate reports if requested (but NOT for error simulation scenarios)
        if generate_reports and scenario["category"] != "error_simulation":
            files = generate_full_run_report(result)
            generated_reports.append({
                "account_id": account_id,
                "files": {k: os.path.basename(v) for k, v in files.items()}
            })
    
    # Summary statistics
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    
    response = {
        "summary": {
            "total_scenarios": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": f"{(passed/total)*100:.0f}%"
        },
        "results": results,
    }
    
    if generate_reports:
        response["generated_reports"] = generated_reports
        response["reports_note"] = "Reports are only generated for real account scenarios, not error simulations"
    
    return response


@router.post("/run-with-reports")
async def run_all_with_reports():
    """
    Run all scenarios and generate full reports for each.
    
    Convenience endpoint that calls run-all with generate_reports=True.
    """
    return await run_all_scenarios(generate_reports=True)


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
    
    Example: auth_rate=1.0 means 100% of requests will get auth errors.
    
    Note: Rates are cumulative - if auth_rate=0.5 and validation_rate=0.5,
    50% of requests get auth errors, and the remaining 50% get validation errors.
    """
    enable_error_simulation(
        auth_rate=auth_rate,
        validation_rate=validation_rate,
        rate_limit_rate=rate_limit_rate,
        server_error_rate=server_error_rate
    )
    
    # Import the actual ERROR_SIMULATOR to confirm it's enabled
    from app.integrations.api_errors import ERROR_SIMULATOR
    
    return {
        "status": "enabled",
        "message": "Error simulation is now ACTIVE. API calls will fail according to configured rates.",
        "rates": {
            "authentication": auth_rate,
            "validation": validation_rate,
            "rate_limit": rate_limit_rate,
            "server_error": server_error_rate,
        },
        "simulator_state": {
            "enabled": ERROR_SIMULATOR.enabled,
            "auth_error_rate": ERROR_SIMULATOR.auth_error_rate,
            "validation_error_rate": ERROR_SIMULATOR.validation_error_rate,
            "rate_limit_error_rate": ERROR_SIMULATOR.rate_limit_error_rate,
            "server_error_rate": ERROR_SIMULATOR.server_error_rate,
        }
    }


@router.post("/disable-random-errors")
async def disable_random_errors():
    """Disable random error injection."""
    disable_error_simulation()
    return {"status": "disabled", "message": "Error simulation is now DISABLED."}


@router.get("/error-simulator-status")
async def get_error_simulator_status():
    """Check the current state of the error simulator."""
    from app.integrations.api_errors import ERROR_SIMULATOR
    
    return {
        "enabled": ERROR_SIMULATOR.enabled,
        "rates": {
            "auth_error_rate": ERROR_SIMULATOR.auth_error_rate,
            "validation_error_rate": ERROR_SIMULATOR.validation_error_rate,
            "rate_limit_error_rate": ERROR_SIMULATOR.rate_limit_error_rate,
            "server_error_rate": ERROR_SIMULATOR.server_error_rate,
        }
    }


@router.get("/notifications")
async def get_notifications():
    """Get all notifications sent during demo runs."""
    return {"notifications": get_sent_notifications()}


@router.post("/reset")
async def reset_demo():
    """Reset demo state (clear notifications, provisioning, and reports)."""
    clear_notifications()
    reset_provisioning()
    disable_error_simulation()
    
    # Optionally clear old reports
    if os.path.exists(REPORTS_DIR):
        for f in os.listdir(REPORTS_DIR):
            if f != ".gitkeep":
                try:
                    os.remove(os.path.join(REPORTS_DIR, f))
                except:
                    pass
    
    return {"status": "reset", "message": "Demo state and reports cleared"}


# ============================================================================
# REPORT ENDPOINTS
# ============================================================================

@router.get("/reports")
async def list_reports():
    """List all generated reports."""
    # Ensure directory exists
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    if not os.path.exists(REPORTS_DIR):
        return {"reports_directory": REPORTS_DIR, "reports": {"html_emails": [], "markdown_reports": [], "audit_logs": []}}
    
    files = [f for f in os.listdir(REPORTS_DIR) if f != ".gitkeep"]
    
    reports = {
        "html_emails": sorted([f for f in files if f.endswith(".html")], reverse=True),
        "markdown_reports": sorted([f for f in files if f.endswith(".md")], reverse=True),
        "audit_logs": sorted([f for f in files if f.endswith(".json")], reverse=True),
    }
    
    return {
        "reports_directory": REPORTS_DIR,
        "total_reports": len(files),
        "reports": reports,
        "view_url_template": "/demo/reports/{filename}",
        "download_url_template": "/demo/reports/{filename}/download",
    }


@router.get("/reports/{filename}", response_class=HTMLResponse)
async def get_report(filename: str):
    """
    Get a specific report file.
    
    HTML files are rendered directly in browser.
    Markdown and JSON are wrapped in HTML for viewing.
    """
    # Ensure directory exists
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    filepath = os.path.join(REPORTS_DIR, filename)
    
    if not os.path.exists(filepath):
        # List available files for debugging
        available = os.listdir(REPORTS_DIR) if os.path.exists(REPORTS_DIR) else []
        return HTMLResponse(
            content=f"""
            <html>
            <head><title>Report Not Found</title></head>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h1 style="color: #dc3545;">Report Not Found</h1>
                <p>The file <code>{filename}</code> was not found.</p>
                <p>Reports directory: <code>{REPORTS_DIR}</code></p>
                <h3>Available reports ({len(available)}):</h3>
                <ul>
                    {"".join(f'<li><a href="/demo/reports/{f}">{f}</a></li>' for f in available if f != '.gitkeep') or '<li>No reports generated yet</li>'}
                </ul>
                <p><a href="/demo/run-with-reports">Run all scenarios with reports</a></p>
            </body>
            </html>
            """,
            status_code=404
        )
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if filename.endswith(".html"):
        return HTMLResponse(content=content)
    elif filename.endswith(".md"):
        # Wrap markdown in styled HTML for viewing
        return HTMLResponse(content=f"""
        <html>
        <head>
            <title>{filename}</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 20px; max-width: 900px; margin: 0 auto; }}
                pre {{ background: #f6f8fa; padding: 16px; border-radius: 6px; overflow-x: auto; white-space: pre-wrap; word-wrap: break-word; }}
                a {{ color: #0366d6; }}
            </style>
        </head>
        <body>
            <p><a href="/demo/reports">← Back to Reports</a> | <a href="/demo/reports/{filename}/download">Download</a></p>
            <pre>{content}</pre>
        </body>
        </html>
        """)
    elif filename.endswith(".json"):
        return HTMLResponse(content=f"""
        <html>
        <head>
            <title>{filename}</title>
            <style>
                body {{ font-family: monospace; padding: 20px; }}
                pre {{ background: #f6f8fa; padding: 16px; border-radius: 6px; overflow-x: auto; }}
                a {{ color: #0366d6; font-family: sans-serif; }}
            </style>
        </head>
        <body>
            <p style="font-family: sans-serif;"><a href="/demo/reports">← Back to Reports</a> | <a href="/demo/reports/{filename}/download">Download</a></p>
            <pre>{content}</pre>
        </body>
        </html>
        """)
    else:
        return HTMLResponse(content=content)


@router.get("/reports/{filename}/download")
async def download_report(filename: str):
    """Download a report file."""
    filepath = os.path.join(REPORTS_DIR, filename)
    
    if not os.path.exists(filepath):
        return {"error": "Report not found", "path": filepath, "reports_dir": REPORTS_DIR}
    
    # Determine media type
    if filename.endswith(".html"):
        media_type = "text/html"
    elif filename.endswith(".md"):
        media_type = "text/markdown"
    elif filename.endswith(".json"):
        media_type = "application/json"
    else:
        media_type = "text/plain"
    
    return FileResponse(filepath, filename=filename, media_type=media_type)


# ============================================================================
# ONBOARDING TASK MANAGEMENT ENDPOINTS
# ============================================================================

@router.get("/tasks/{account_id}")
async def get_onboarding_tasks(account_id: str):
    """
    Get all onboarding tasks for an account.
    
    Returns the full task checklist with status, owners, due dates, and dependencies.
    
    This shows the granular steps during SaaS provisioning:
    - Automated tasks (system-completed)
    - CS team tasks (schedule kickoff, configure SSO, etc.)
    - Customer tasks (verify login, complete tour, etc.)
    """
    from app.integrations import provisioning
    
    if not provisioning.is_provisioned(account_id):
        return {
            "error": "Account not provisioned",
            "account_id": account_id,
            "message": "Run /demo/run/{account_id} first to provision the account and create tasks"
        }
    
    tasks = provisioning.get_onboarding_tasks(account_id)
    prov_status = provisioning.get_provisioning_status(account_id)
    
    # Group tasks by category
    by_category = {}
    for task in tasks:
        cat = task.get("category", "other")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(task)
    
    # Group tasks by status
    by_status = {}
    for task in tasks:
        status = task.get("status", "unknown")
        if status not in by_status:
            by_status[status] = []
        by_status[status].append(task)
    
    return {
        "account_id": account_id,
        "tenant_id": prov_status.get("tenant_id"),
        "tier": prov_status.get("tier"),
        "task_summary": prov_status.get("onboarding_tasks", {}),
        "tasks": {
            "all": tasks,
            "by_category": by_category,
            "by_status": by_status,
        }
    }


@router.get("/tasks/{account_id}/pending")
async def get_pending_tasks(account_id: str, owner: str = None):
    """
    Get pending onboarding tasks, optionally filtered by owner.
    
    Owners can be: "cs_team", "customer", "system"
    """
    from app.integrations import provisioning
    
    if not provisioning.is_provisioned(account_id):
        return {"error": "Account not provisioned", "account_id": account_id}
    
    if owner:
        tasks = provisioning.get_pending_tasks_by_owner(account_id, owner)
    else:
        all_tasks = provisioning.get_onboarding_tasks(account_id)
        tasks = [t for t in all_tasks if t.get("status") in ["pending", "in_progress"]]
    
    return {
        "account_id": account_id,
        "filter": {"owner": owner} if owner else None,
        "pending_count": len(tasks),
        "tasks": tasks,
    }


@router.get("/tasks/{account_id}/overdue")
async def get_overdue_tasks(account_id: str):
    """
    Get overdue onboarding tasks.
    
    These are tasks that have passed their due date but are not yet completed.
    The agent can use this to proactively alert the CS team.
    """
    from app.integrations import provisioning
    
    if not provisioning.is_provisioned(account_id):
        return {"error": "Account not provisioned", "account_id": account_id}
    
    overdue = provisioning.get_overdue_tasks(account_id)
    
    return {
        "account_id": account_id,
        "overdue_count": len(overdue),
        "alert_level": "critical" if len(overdue) > 3 else "warning" if len(overdue) > 0 else "ok",
        "tasks": overdue,
    }


@router.put("/tasks/{account_id}/{task_id}")
async def update_task_status(
    account_id: str, 
    task_id: str, 
    status: str,
    completed_by: str = None,
    notes: str = None
):
    """
    Update the status of an onboarding task.
    
    Valid statuses: pending, in_progress, completed, blocked, skipped
    
    This would be called by:
    - CS team marking tasks complete
    - Webhooks from the platform (when customer completes actions)
    - Automated monitoring jobs
    """
    from app.integrations import provisioning
    
    valid_statuses = ["pending", "in_progress", "completed", "blocked", "skipped"]
    if status not in valid_statuses:
        return {
            "error": "Invalid status",
            "valid_statuses": valid_statuses,
        }
    
    if not provisioning.is_provisioned(account_id):
        return {"error": "Account not provisioned", "account_id": account_id}
    
    updated_task = provisioning.update_task_status(
        account_id, 
        task_id, 
        status,
        completed_by=completed_by,
        notes=notes
    )
    
    if not updated_task:
        return {"error": "Task not found", "task_id": task_id}
    
    # Get updated summary
    prov_status = provisioning.get_provisioning_status(account_id)
    
    return {
        "message": f"Task {task_id} updated to {status}",
        "task": updated_task,
        "onboarding_progress": prov_status.get("onboarding_tasks", {}),
    }


@router.get("/tasks/{account_id}/next-actions")
async def get_next_actions(account_id: str):
    """
    Get the next actionable tasks for CS team and customer.
    
    Returns tasks that:
    - Have all dependencies completed
    - Are still pending
    - Grouped by owner for easy assignment
    """
    from app.integrations import provisioning
    
    if not provisioning.is_provisioned(account_id):
        return {"error": "Account not provisioned", "account_id": account_id}
    
    prov_status = provisioning.get_provisioning_status(account_id)
    task_summary = prov_status.get("onboarding_tasks", {})
    
    # Get pending tasks by owner
    cs_tasks = provisioning.get_pending_tasks_by_owner(account_id, "cs_team")
    customer_tasks = provisioning.get_pending_tasks_by_owner(account_id, "customer")
    
    return {
        "account_id": account_id,
        "completion_percentage": task_summary.get("completion_percentage", 0),
        "next_actions": task_summary.get("next_actions", []),
        "cs_team_tasks": cs_tasks[:3],  # Top 3
        "customer_tasks": customer_tasks[:3],  # Top 3
    }
