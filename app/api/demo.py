"""
Demo API endpoints for showcasing the onboarding agent.
"""

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from app.agent import run_onboarding_async
from app.notifications import get_sent_notifications, clear_notifications
from app.integrations.provisioning import reset_all as reset_provisioning
from app.integrations.resolution import reset_resolution_state, simulate_issue_resolution
from app.integrations.api_errors import enable_error_simulation, disable_error_simulation
from app.reports import generate_full_run_report, REPORTS_DIR
import os

router = APIRouter()

# All demo scenarios
ALL_SCENARIOS = [
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
    {
        "id": "FOREX-005",
        "name": "Escalation - FX Invoice Mismatch",
        "description": "Invoice in CAD vs USD opportunity. Currency conversion reveals gap beyond 2% threshold.",
        "expected_decision": "ESCALATE",
        "category": "normal",
    },
    {
        "id": "PARTIAL-006",
        "name": "Escalation - Partial Payment Gap",
        "description": "Invoice partially paid. 5% underpayment exceeds 2% threshold.",
        "expected_decision": "ESCALATE",
        "category": "normal",
    },
    {
        "id": "STARTER-007",
        "name": "Proceed - Customer Not Logged In",
        "description": "All checks pass, provisioned 5 days ago, but customer has not logged in yet.",
        "expected_decision": "PROCEED",
        "category": "normal",
    },
    {
        "id": "GROWTH-008",
        "name": "Proceed - Stalled Onboarding",
        "description": "All checks pass, provisioned 10 days ago, kickoff not done, <30% completion.",
        "expected_decision": "PROCEED",
        "category": "normal",
    },
    {
        "id": "ENTERPRISE-009",
        "name": "Proceed - SSO & Blocked Tasks",
        "description": "All checks pass, provisioned 8 days ago, SSO not configured, customer tasks overdue.",
        "expected_decision": "PROCEED",
        "category": "normal",
    },
]


ERROR_SIMULATION_IDS = {"AUTH-ERROR", "PERM-ERROR", "SERVER-ERROR", "RATE-ERROR", "VALIDATION-ERROR"}

# In-memory store for ALL onboarding run results (not just provisioned ones)
_ALL_RUN_RESULTS: dict[str, dict] = {}

def is_error_simulation_scenario(account_id: str) -> bool:
    return account_id in ERROR_SIMULATION_IDS or account_id.endswith("-ERROR")


@router.get("/scenarios")
async def list_scenarios():
    """List available demo scenarios."""
    return {"scenarios": ALL_SCENARIOS}


@router.post("/run/{account_id}")
async def run_demo_scenario(account_id: str, generate_report: bool = False):
    """Run a specific demo scenario by account ID."""
    clear_notifications()

    result = await run_onboarding_async(
        account_id=account_id,
        event_type="demo.trigger",
    )

    notifications = get_sent_notifications(account_id)

    # Look up scenario name for dashboard display
    scenario_name = ""
    for s in ALL_SCENARIOS:
        if s["id"] == account_id:
            scenario_name = s["name"]
            break

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
        "scenario_name": scenario_name,
    }

    # Store result for dashboard
    _ALL_RUN_RESULTS[account_id] = response

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


@router.post("/enable-random-errors")
async def enable_random_errors(
    auth_rate: float = Query(default=0.05, ge=0.0, le=1.0, description="Authentication error probability (0-1)"),
    validation_rate: float = Query(default=0.05, ge=0.0, le=1.0, description="Validation error probability (0-1)"),
    rate_limit_rate: float = Query(default=0.02, ge=0.0, le=1.0, description="Rate limit error probability (0-1)"),
    server_error_rate: float = Query(default=0.01, ge=0.0, le=1.0, description="Server error probability (0-1)"),
):
    """Enable random error injection for stress testing."""
    enable_error_simulation(
        auth_rate=auth_rate,
        validation_rate=validation_rate,
        rate_limit_rate=rate_limit_rate,
        server_error_rate=server_error_rate
    )

    from app.integrations.api_errors import ERROR_SIMULATOR

    return {
        "status": "enabled",
        "message": "Error simulation is now ACTIVE.",
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
    """Reset demo state."""
    clear_notifications()
    reset_provisioning()
    reset_resolution_state()
    disable_error_simulation()
    _ALL_RUN_RESULTS.clear()
    _CHAT_SESSIONS.clear()

    if os.path.exists(REPORTS_DIR):
        for f in os.listdir(REPORTS_DIR):
            if f != ".gitkeep":
                try:
                    os.remove(os.path.join(REPORTS_DIR, f))
                except Exception:
                    pass

    return {"status": "reset", "message": "Demo state and reports cleared"}


# ============================================================================
# REPORT ENDPOINTS
# ============================================================================

@router.get("/reports")
async def list_reports():
    """List all generated reports."""
    os.makedirs(REPORTS_DIR, exist_ok=True)

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
    """Get a specific report file."""
    os.makedirs(REPORTS_DIR, exist_ok=True)

    filepath = os.path.join(REPORTS_DIR, filename)

    if not os.path.exists(filepath):
        available = os.listdir(REPORTS_DIR) if os.path.exists(REPORTS_DIR) else []
        return HTMLResponse(
            content=f"""
            <html>
            <head><title>Report Not Found</title></head>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h1 style="color: #dc3545;">Report Not Found</h1>
                <p>The file <code>{filename}</code> was not found.</p>
                <h3>Available reports ({len(available)}):</h3>
                <ul>
                    {"".join(f'<li><a href="/demo/reports/{f}">{f}</a></li>' for f in available if f != '.gitkeep') or '<li>No reports generated yet</li>'}
                </ul>
                <p>Run a scenario via <code>POST /demo/run/{'{account_id}'}</code> to generate reports.</p>
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
            <p><a href="/demo/reports">Back to Reports</a> | <a href="/demo/reports/{filename}/download">Download</a></p>
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
            <p style="font-family: sans-serif;"><a href="/demo/reports">Back to Reports</a> | <a href="/demo/reports/{filename}/download">Download</a></p>
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
        return {"error": "Report not found", "path": filepath}

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
    """Get all onboarding tasks for an account."""
    from app.integrations import provisioning

    if not provisioning.is_provisioned(account_id):
        return {
            "error": "Account not provisioned",
            "account_id": account_id,
            "message": "Run /demo/run/{account_id} first to provision the account"
        }

    tasks = provisioning.get_onboarding_tasks(account_id)
    prov_status = provisioning.get_provisioning_status(account_id)

    by_category = {}
    for task in tasks:
        cat = task.get("category", "other")
        by_category.setdefault(cat, []).append(task)

    by_status = {}
    for task in tasks:
        status = task.get("status", "unknown")
        by_status.setdefault(status, []).append(task)

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
    """Get pending onboarding tasks, optionally filtered by owner."""
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
    """Get overdue onboarding tasks."""
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
    """Update the status of an onboarding task."""
    from app.integrations import provisioning

    valid_statuses = ["pending", "in_progress", "completed", "blocked", "skipped"]
    if status not in valid_statuses:
        return {"error": "Invalid status", "valid_statuses": valid_statuses}

    if not provisioning.is_provisioned(account_id):
        return {"error": "Account not provisioned", "account_id": account_id}

    updated_task = provisioning.update_task_status(
        account_id, task_id, status,
        completed_by=completed_by, notes=notes
    )

    if not updated_task:
        return {"error": "Task not found", "task_id": task_id}

    prov_status = provisioning.get_provisioning_status(account_id)

    return {
        "message": f"Task {task_id} updated to {status}",
        "task": updated_task,
        "onboarding_progress": prov_status.get("onboarding_tasks", {}),
    }


# ============================================================================
# CS ASSISTANT / MONITORING ENDPOINTS
# ============================================================================

@router.get("/progress/{account_id}")
async def get_onboarding_progress(account_id: str):
    """Get onboarding progress dashboard for an account."""
    from app.integrations import provisioning
    return provisioning.check_onboarding_progress(account_id)


@router.get("/risks/{account_id}")
async def get_onboarding_risks(account_id: str):
    """Identify risks for an active onboarding."""
    from app.integrations import provisioning
    return provisioning.identify_onboarding_risks(account_id)


@router.post("/remind/{account_id}/{task_id}")
async def remind_task(account_id: str, task_id: str, recipient: str = "", message: str = ""):
    """Send a reminder about a pending task."""
    from app.integrations import provisioning
    return provisioning.send_task_reminder(account_id, task_id, recipient, message)


@router.post("/escalate/{account_id}")
async def escalate_onboarding(account_id: str, reason: str = ""):
    """Escalate a stalled onboarding to CS management."""
    from app.integrations import provisioning
    return provisioning.escalate_stalled_onboarding(account_id, reason)


def _build_proceed_entry(account_id: str, run: dict | None = None) -> dict:
    """Build a PROCEED onboarding entry from live provisioning state."""
    from app.integrations import provisioning

    progress = provisioning.check_onboarding_progress(account_id)
    return {
        "account_id": account_id,
        "decision": "PROCEED",
        "scenario_name": (run or {}).get("scenario_name", ""),
        "tenant_id": progress.get("tenant_id"),
        "tier": progress.get("tier"),
        "completion_percentage": progress.get("completion_percentage", 0),
        "health_status": progress.get("health_status", "on_track"),
        "days_since_provisioning": progress.get("days_since_provisioning", 0),
        "overdue_count": len(progress.get("overdue_tasks", [])),
        "blocked_count": progress.get("task_breakdown", {}).get("blocked", 0),
        "sentiment": progress.get("sentiment", {}),
        "summary": (run or {}).get("summary", ""),
    }


@router.get("/active-onboardings")
async def list_active_onboardings():
    """List all onboarding run results — provisioned AND blocked/escalated.

    Merges two sources so accounts onboarded via chat also appear:
    1. _ALL_RUN_RESULTS  — populated by /run/{account_id} and execute-action
    2. provisioning store — populated by the provision_account tool (any agent)
    """
    from app.integrations import provisioning

    seen: set[str] = set()
    results = []

    # 1) Accounts tracked in _ALL_RUN_RESULTS
    for account_id, run in _ALL_RUN_RESULTS.items():
        seen.add(account_id)
        decision = run.get("decision", "UNKNOWN")

        if decision == "PROCEED" or provisioning.is_provisioned(account_id):
            results.append(_build_proceed_entry(account_id, run))
        else:
            violations = run.get("violations", {})
            warnings = run.get("warnings", {})
            results.append({
                "account_id": account_id,
                "decision": decision,
                "scenario_name": run.get("scenario_name", ""),
                "tenant_id": None,
                "tier": None,
                "completion_percentage": 0,
                "health_status": "blocked" if decision == "BLOCK" else "escalated",
                "days_since_provisioning": 0,
                "overdue_count": 0,
                "blocked_count": 0,
                "violation_count": sum(len(v) if isinstance(v, list) else 1 for v in violations.values()),
                "warning_count": sum(len(v) if isinstance(v, list) else 1 for v in warnings.values()),
                "violations": violations,
                "warnings": warnings,
                "summary": run.get("summary", ""),
            })

    # 2) Provisioned accounts not in _ALL_RUN_RESULTS (e.g. onboarded via chat)
    for active in provisioning.get_all_active_onboardings():
        aid = active["account_id"]
        if aid not in seen:
            results.append(_build_proceed_entry(aid))

    return {"onboardings": results}


# ============================================================================
# SENTIMENT ANALYSIS
# ============================================================================

@router.get("/sentiment/{account_id}")
async def get_sentiment(account_id: str):
    """Get customer sentiment score, trend, and interaction details."""
    from app.integrations import sentiment

    score = sentiment.get_sentiment_score(account_id)
    trend = sentiment.get_sentiment_trend(account_id)
    return {**score, "trend": trend.get("trend", "stable"), "trend_detail": trend}


# ============================================================================
# PROACTIVE ALERTS, PORTFOLIO & SUGGESTED ACTIONS
# ============================================================================

@router.get("/alerts")
async def get_alerts():
    """Get aggregated risk alerts across all accounts (provisioned + blocked/escalated)."""
    from app.integrations import provisioning

    # Alerts from provisioned accounts (task-level risks)
    alerts = provisioning.get_all_alerts()

    # Alerts from blocked/escalated accounts (decision-level issues)
    for account_id, run in _ALL_RUN_RESULTS.items():
        decision = run.get("decision", "UNKNOWN")
        if decision == "BLOCK":
            violations = run.get("violations", {})
            for domain, msgs in violations.items():
                msg_list = msgs if isinstance(msgs, list) else [msgs]
                for msg in msg_list:
                    alerts.append({
                        "severity": "critical",
                        "account_id": account_id,
                        "risk": f"Onboarding blocked — {domain} violation",
                        "detail": str(msg),
                        "recommendation": f"Resolve the {domain} issue and re-run onboarding for {account_id}",
                    })
        elif decision == "ESCALATE" and not provisioning.is_provisioned(account_id):
            warnings = run.get("warnings", {})
            for domain, msgs in warnings.items():
                msg_list = msgs if isinstance(msgs, list) else [msgs]
                for msg in msg_list:
                    alerts.append({
                        "severity": "high",
                        "account_id": account_id,
                        "risk": f"Onboarding escalated — {domain} warning",
                        "detail": str(msg),
                        "recommendation": f"Review the {domain} issue and approve or resolve for {account_id}",
                    })

    # Re-sort by severity
    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    alerts.sort(key=lambda a: sev_order.get(a.get("severity", "low"), 4))
    return {"alert_count": len(alerts), "alerts": alerts}


@router.get("/portfolio-summary")
async def get_portfolio_summary():
    """Get aggregated portfolio stats + priority actions.

    Merges _ALL_RUN_RESULTS with the provisioning store so accounts
    onboarded via chat also appear in the portfolio view.
    """
    from app.integrations import provisioning

    health_dist: dict[str, int] = {
        "on_track": 0, "at_risk": 0, "stalled": 0,
        "blocked": 0, "escalated": 0,
    }
    accounts: list[dict] = []
    seen: set[str] = set()

    for account_id, run in _ALL_RUN_RESULTS.items():
        seen.add(account_id)
        decision = run.get("decision", "UNKNOWN")

        if decision == "PROCEED" or provisioning.is_provisioned(account_id):
            progress = provisioning.check_onboarding_progress(account_id)
            health = progress.get("health_status", "on_track")
            if health in health_dist:
                health_dist[health] += 1
            accounts.append({
                "account_id": account_id,
                "decision": "PROCEED",
                "tier": progress.get("tier"),
                "health_status": health,
                "completion_percentage": progress.get("completion_percentage", 0),
                "days_since_provisioning": progress.get("days_since_provisioning", 0),
                "overdue_count": len(progress.get("overdue_tasks", [])),
                "blocked_count": progress.get("task_breakdown", {}).get("blocked", 0),
                "scenario_name": run.get("scenario_name", ""),
            })
        elif decision in ("BLOCK", "ESCALATE"):
            status_key = "blocked" if decision == "BLOCK" else "escalated"
            health_dist[status_key] = health_dist.get(status_key, 0) + 1
            accounts.append({
                "account_id": account_id,
                "decision": decision,
                "health_status": status_key,
                "completion_percentage": 0,
                "days_since_provisioning": 0,
                "overdue_count": 0,
                "blocked_count": 0,
                "tier": None,
                "scenario_name": run.get("scenario_name", ""),
            })

    # Include provisioned accounts not in _ALL_RUN_RESULTS (e.g. via chat)
    for active in provisioning.get_all_active_onboardings():
        aid = active["account_id"]
        if aid not in seen:
            progress = provisioning.check_onboarding_progress(aid)
            health = progress.get("health_status", "on_track")
            if health in health_dist:
                health_dist[health] += 1
            accounts.append({
                "account_id": aid,
                "decision": "PROCEED",
                "tier": progress.get("tier"),
                "health_status": health,
                "completion_percentage": progress.get("completion_percentage", 0),
                "days_since_provisioning": progress.get("days_since_provisioning", 0),
                "overdue_count": len(progress.get("overdue_tasks", [])),
                "blocked_count": progress.get("task_breakdown", {}).get("blocked", 0),
                "scenario_name": "",
            })

    # Priority actions from provisioned accounts
    priority_actions = provisioning.get_all_alerts()[:5]

    return {
        "total_accounts": len(accounts),
        "health_distribution": health_dist,
        "accounts": accounts,
        "priority_actions": priority_actions,
    }


@router.get("/suggested-actions")
async def get_suggested_actions():
    """Get actionable suggestions derived from risks across all accounts.

    Returns one compound action per account, containing all sub-actions so the
    dashboard never shows duplicate cards for the same account.
    """
    from collections import OrderedDict
    from app.integrations import provisioning

    # Collect raw per-risk actions
    raw_actions: list[dict] = provisioning.get_all_suggested_actions()

    # Actions from blocked/escalated accounts (decision-level)
    for account_id, run in _ALL_RUN_RESULTS.items():
        decision = run.get("decision", "UNKNOWN")
        if decision == "BLOCK":
            violations = run.get("violations", {})
            top_domain = next(iter(violations), "unknown")
            raw_actions.append({
                "action_id": f"act-block-{account_id}",
                "action_type": "rerun_onboarding",
                "description": f"Simulate {top_domain} issue resolution and re-run onboarding for {account_id}",
                "account_id": account_id,
                "icon": "🔄",
                "severity": "critical",
                "task_id": "",
                "params": {},
            })
        elif decision == "ESCALATE" and not provisioning.is_provisioned(account_id):
            raw_actions.append({
                "action_id": f"act-esc-{account_id}",
                "action_type": "review_escalation",
                "description": f"Simulate warning resolution and re-run onboarding for {account_id}",
                "account_id": account_id,
                "icon": "👀",
                "severity": "high",
                "task_id": "",
                "params": {},
            })

    # Group by account — one compound entry per account
    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    by_account: OrderedDict[str, list[dict]] = OrderedDict()
    for act in raw_actions:
        by_account.setdefault(act["account_id"], []).append(act)

    grouped: list[dict] = []
    for account_id, sub_actions in by_account.items():
        sub_actions.sort(key=lambda a: sev_order.get(a.get("severity", "low"), 4))
        top_severity = sub_actions[0].get("severity", "low")
        top_icon = sub_actions[0].get("icon", "📋")
        descriptions = [a["description"] for a in sub_actions]
        grouped.append({
            "action_id": f"act-group-{account_id}",
            "account_id": account_id,
            "icon": top_icon,
            "severity": top_severity,
            "description": descriptions[0] if len(descriptions) == 1 else f"{len(descriptions)} actions needed",
            "sub_actions": sub_actions,
        })

    grouped.sort(key=lambda a: sev_order.get(a.get("severity", "low"), 4))
    return {"action_count": len(grouped), "actions": grouped}


class ExecuteActionRequest(BaseModel):
    action_type: str
    account_id: str
    task_id: str = ""
    params: dict = {}


@router.post("/execute-action")
async def execute_action(req: ExecuteActionRequest):
    """Execute a suggested action by type."""
    from app.integrations import provisioning

    if req.action_type == "send_login_reminder":
        task_id = req.task_id or f"{req.account_id}-T009"
        return provisioning.send_task_reminder(
            req.account_id, task_id,
            recipient="customer",
            message=req.params.get("message", "Please log in to complete setup."),
        )
    elif req.action_type == "send_task_reminder":
        return provisioning.send_task_reminder(
            req.account_id, req.task_id,
            recipient=req.params.get("recipient", ""),
            message=req.params.get("message", ""),
        )
    elif req.action_type in ("escalate", "escalate_blocked"):
        return provisioning.escalate_stalled_onboarding(
            req.account_id,
            reason=req.params.get("reason", "Suggested by proactive risk detection"),
        )
    elif req.action_type == "schedule_sso_followup":
        task_id = req.task_id or f"{req.account_id}-T007"
        return provisioning.update_task_status(
            req.account_id, task_id, "in_progress",
            completed_by="cs_manager",
            notes="SSO follow-up initiated via suggested action",
        )
    elif req.action_type == "rerun_onboarding":
        resolution = simulate_issue_resolution(req.account_id)
        result = await run_onboarding_async(
            account_id=req.account_id,
            event_type="demo.rerun",
        )
        _ALL_RUN_RESULTS[req.account_id] = {
            "account_id": req.account_id,
            "decision": result.get("decision"),
            "violations": result.get("violations"),
            "warnings": result.get("warnings"),
            "provisioning": result.get("provisioning"),
            "summary": result.get("human_summary"),
        }
        return {
            "status": "rerun_complete",
            "decision": result.get("decision"),
            "account_id": req.account_id,
            "resolution": resolution,
            "provisioning": result.get("provisioning"),
        }
    elif req.action_type == "schedule_sentiment_call":
        from app.integrations import sentiment
        # Simulate the call happening and customer responding positively
        sentiment.add_interaction(
            req.account_id, "call", "outbound", "cs_team",
            "Proactive check-in call to discuss onboarding experience and address concerns.",
        )
        sentiment.add_interaction(
            req.account_id, "call", "inbound", "customer",
            "Thank you for reaching out. We appreciate the follow-up. "
            "The issues have been noted and we are happy to continue.",
        )
        return {
            "status": "scheduled",
            "account_id": req.account_id,
            "message": f"Check-in call completed for {req.account_id}. Customer responded positively — sentiment improved.",
        }
    elif req.action_type == "review_escalation":
        resolution = simulate_issue_resolution(req.account_id)
        result = await run_onboarding_async(
            account_id=req.account_id,
            event_type="demo.review_escalation",
        )
        _ALL_RUN_RESULTS[req.account_id] = {
            "account_id": req.account_id,
            "decision": result.get("decision"),
            "violations": result.get("violations"),
            "warnings": result.get("warnings"),
            "provisioning": result.get("provisioning"),
            "summary": result.get("human_summary"),
        }
        return {
            "status": "review_complete",
            "account_id": req.account_id,
            "decision": result.get("decision"),
            "resolution": resolution,
            "provisioning": result.get("provisioning"),
            "message": f"Warnings were simulated as resolved and onboarding was re-run for {req.account_id}.",
        }
    else:
        return {"error": f"Unknown action type: {req.action_type}"}


class ChatRequest(BaseModel):
    message: str
    account_id: str = "ACME-001"
    session_id: str = "default"


# Server-side chat session storage: session_id -> message_history
_CHAT_SESSIONS: dict[str, list] = {}


@router.post("/chat")
async def chat_with_agent(req: ChatRequest):
    """Chat with the CS assistant agent (retains conversation history)."""
    from app.agent.onboarding_agent import cs_assistant_agent
    from app.agent.dependencies import OnboardingDeps
    from app.integrations import provisioning

    deps = OnboardingDeps(account_id=req.account_id)

    # Retrieve prior conversation history for this session
    message_history = _CHAT_SESSIONS.get(req.session_id)

    # Track whether the account was already provisioned before this turn
    was_provisioned = provisioning.is_provisioned(req.account_id)

    result = await cs_assistant_agent.run(
        req.message,
        deps=deps,
        message_history=message_history,
    )

    # Store updated history for next turn
    _CHAT_SESSIONS[req.session_id] = result.all_messages()

    # Sync dashboard: if the agent provisioned the account during this chat
    # turn, store in _ALL_RUN_RESULTS so Dashboard/Portfolio reflect it.
    # (Non-provisioned accounts are already picked up by active-onboardings
    # from the provisioning store.)
    if provisioning.is_provisioned(req.account_id) and not was_provisioned:
        scenario_name = ""
        for s in ALL_SCENARIOS:
            if s["id"] == req.account_id:
                scenario_name = s["name"]
                break
        _ALL_RUN_RESULTS[req.account_id] = {
            "account_id": req.account_id,
            "decision": "PROCEED",
            "summary": result.output[:200] if result.output else "",
            "scenario_name": scenario_name,
        }

    return {"response": result.output, "account_id": req.account_id}


@router.post("/chat/reset")
async def reset_chat(session_id: str = "default"):
    """Clear chat history for a session."""
    _CHAT_SESSIONS.pop(session_id, None)
    return {"status": "cleared", "session_id": session_id}


@router.get("/tasks/{account_id}/next-actions")
async def get_next_actions(account_id: str):
    """Get the next actionable tasks for CS team and customer."""
    from app.integrations import provisioning

    if not provisioning.is_provisioned(account_id):
        return {"error": "Account not provisioned", "account_id": account_id}

    prov_status = provisioning.get_provisioning_status(account_id)
    task_summary = prov_status.get("onboarding_tasks", {})

    cs_tasks = provisioning.get_pending_tasks_by_owner(account_id, "cs_team")
    customer_tasks = provisioning.get_pending_tasks_by_owner(account_id, "customer")

    return {
        "account_id": account_id,
        "completion_percentage": task_summary.get("completion_percentage", 0),
        "next_actions": task_summary.get("next_actions", []),
        "cs_team_tasks": cs_tasks[:3],
        "customer_tasks": customer_tasks[:3],
    }
