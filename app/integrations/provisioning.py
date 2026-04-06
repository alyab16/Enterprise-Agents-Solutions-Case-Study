"""
Mock SaaS provisioning system integration with onboarding task management.

This module handles:
1. Tenant provisioning (creating the customer's account)
2. Onboarding task tracking (the CS workflow items)
3. Task automation and status updates

In production, this would integrate with your product's provisioning API
and potentially a task management system like Asana, Monday, or internal tools.
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field, asdict


class TaskStatus(str, Enum):
    """Status of an onboarding task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class TaskCategory(str, Enum):
    """Category of onboarding task."""
    TECHNICAL = "technical"
    CUSTOMER_ACTION = "customer_action"
    CS_ACTION = "cs_action"
    AUTOMATED = "automated"


@dataclass
class OnboardingTask:
    """Represents a single onboarding task."""
    task_id: str
    name: str
    description: str
    category: TaskCategory
    owner: str  # "system", "cs_team", "customer"
    status: TaskStatus = TaskStatus.PENDING
    due_date: Optional[str] = None
    completed_at: Optional[str] = None
    completed_by: Optional[str] = None
    notes: Optional[str] = None
    depends_on: List[str] = field(default_factory=list)
    auto_complete: bool = False  # If True, system can auto-complete
    
    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "owner": self.owner,
            "status": self.status.value,
            "due_date": self.due_date,
            "completed_at": self.completed_at,
            "completed_by": self.completed_by,
            "notes": self.notes,
            "depends_on": self.depends_on,
            "auto_complete": self.auto_complete,
        }


# Track provisioned accounts
_PROVISIONED_ACCOUNTS: Dict[str, dict] = {}

# Track onboarding tasks per account
_ONBOARDING_TASKS: Dict[str, List[OnboardingTask]] = {}

MOCK_PROVISIONING_CONFIG = {
    "Enterprise": {
        "max_users": 100,
        "features": ["analytics", "api_access", "sso", "custom_reports", "dedicated_support"],
        "storage_gb": 500,
        "api_rate_limit": 10000,
    },
    "Growth": {
        "max_users": 25,
        "features": ["analytics", "api_access", "standard_reports"],
        "storage_gb": 100,
        "api_rate_limit": 5000,
    },
    "Starter": {
        "max_users": 5,
        "features": ["analytics", "basic_reports"],
        "storage_gb": 25,
        "api_rate_limit": 1000,
    },
}


def _create_onboarding_tasks(account_id: str, tenant_id: str, tier: str, customer_name: str) -> List[OnboardingTask]:
    """
    Create the standard onboarding task checklist for a new customer.
    
    This represents the granular steps during SaaS provisioning that the
    CS team tracks to ensure successful onboarding.
    """
    now = datetime.utcnow()
    
    tasks = [
        # ===== AUTOMATED TASKS (System completes immediately) =====
        OnboardingTask(
            task_id=f"{account_id}-T001",
            name="Create Tenant",
            description=f"Provision tenant {tenant_id} in the platform",
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
            description="Create API key and secret for programmatic access",
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
            description=f"Send welcome email to {customer_name} with login instructions",
            category=TaskCategory.AUTOMATED,
            owner="system",
            status=TaskStatus.COMPLETED,
            completed_at=now.isoformat(),
            completed_by="onboarding_agent",
            auto_complete=True,
            depends_on=[f"{account_id}-T001"],
        ),
        OnboardingTask(
            task_id=f"{account_id}-T004",
            name="Send Training Materials",
            description="Email getting started guides and video tutorials",
            category=TaskCategory.AUTOMATED,
            owner="system",
            status=TaskStatus.COMPLETED,
            completed_at=now.isoformat(),
            completed_by="onboarding_agent",
            auto_complete=True,
            depends_on=[f"{account_id}-T003"],
        ),
        
        # ===== CS TEAM TASKS =====
        OnboardingTask(
            task_id=f"{account_id}-T005",
            name="Schedule Kickoff Call",
            description="Reach out to customer to schedule initial kickoff meeting",
            category=TaskCategory.CS_ACTION,
            owner="cs_team",
            status=TaskStatus.PENDING,
            due_date=(now + timedelta(days=1)).strftime("%Y-%m-%d"),
            depends_on=[f"{account_id}-T003"],
        ),
        OnboardingTask(
            task_id=f"{account_id}-T006",
            name="Conduct Kickoff Call",
            description="30-min call to review goals, timeline, and success metrics",
            category=TaskCategory.CS_ACTION,
            owner="cs_team",
            status=TaskStatus.PENDING,
            due_date=(now + timedelta(days=3)).strftime("%Y-%m-%d"),
            depends_on=[f"{account_id}-T005"],
        ),
        OnboardingTask(
            task_id=f"{account_id}-T007",
            name="Configure SSO Integration",
            description="Work with customer IT to set up Single Sign-On" if tier == "Enterprise" else "SSO not included in this tier",
            category=TaskCategory.TECHNICAL,
            owner="cs_team",
            status=TaskStatus.PENDING if tier == "Enterprise" else TaskStatus.SKIPPED,
            due_date=(now + timedelta(days=7)).strftime("%Y-%m-%d") if tier == "Enterprise" else None,
            depends_on=[f"{account_id}-T006"],
            notes="Requires customer IT involvement" if tier == "Enterprise" else "Skipped - not in tier",
        ),
        OnboardingTask(
            task_id=f"{account_id}-T008",
            name="Create Custom Reports",
            description="Set up custom reporting dashboards per customer requirements" if tier in ["Enterprise", "Growth"] else "Custom reports not included",
            category=TaskCategory.CS_ACTION,
            owner="cs_team",
            status=TaskStatus.PENDING if tier in ["Enterprise", "Growth"] else TaskStatus.SKIPPED,
            due_date=(now + timedelta(days=10)).strftime("%Y-%m-%d") if tier in ["Enterprise", "Growth"] else None,
            depends_on=[f"{account_id}-T006"],
        ),
        
        # ===== CUSTOMER TASKS =====
        OnboardingTask(
            task_id=f"{account_id}-T009",
            name="Verify Login Access",
            description="Customer confirms they can log into the platform",
            category=TaskCategory.CUSTOMER_ACTION,
            owner="customer",
            status=TaskStatus.PENDING,
            due_date=(now + timedelta(days=2)).strftime("%Y-%m-%d"),
            depends_on=[f"{account_id}-T003"],
        ),
        OnboardingTask(
            task_id=f"{account_id}-T010",
            name="Complete Platform Tour",
            description="Customer completes the in-app guided tour",
            category=TaskCategory.CUSTOMER_ACTION,
            owner="customer",
            status=TaskStatus.PENDING,
            due_date=(now + timedelta(days=5)).strftime("%Y-%m-%d"),
            depends_on=[f"{account_id}-T009"],
        ),
        OnboardingTask(
            task_id=f"{account_id}-T011",
            name="Invite Team Members",
            description="Customer invites their team to the platform",
            category=TaskCategory.CUSTOMER_ACTION,
            owner="customer",
            status=TaskStatus.PENDING,
            due_date=(now + timedelta(days=7)).strftime("%Y-%m-%d"),
            depends_on=[f"{account_id}-T009"],
        ),
        OnboardingTask(
            task_id=f"{account_id}-T012",
            name="Create First Campaign",
            description="Customer creates their first campaign/project",
            category=TaskCategory.CUSTOMER_ACTION,
            owner="customer",
            status=TaskStatus.PENDING,
            due_date=(now + timedelta(days=14)).strftime("%Y-%m-%d"),
            depends_on=[f"{account_id}-T010"],
        ),
        
        # ===== MILESTONE TASKS =====
        OnboardingTask(
            task_id=f"{account_id}-T013",
            name="30-Day Check-in",
            description="CS reaches out to review progress and address any issues",
            category=TaskCategory.CS_ACTION,
            owner="cs_team",
            status=TaskStatus.PENDING,
            due_date=(now + timedelta(days=30)).strftime("%Y-%m-%d"),
            depends_on=[f"{account_id}-T006"],
        ),
        OnboardingTask(
            task_id=f"{account_id}-T014",
            name="Onboarding Complete",
            description="Mark onboarding as complete and transition to BAU support",
            category=TaskCategory.CS_ACTION,
            owner="cs_team",
            status=TaskStatus.PENDING,
            due_date=(now + timedelta(days=45)).strftime("%Y-%m-%d"),
            depends_on=[f"{account_id}-T012", f"{account_id}-T013"],
        ),
    ]
    
    return tasks


def provision_account(account_id: str, tier: str = "Starter", customer_name: str = "Customer") -> dict:
    """
    Provision a new tenant in the SaaS platform.
    Also creates the onboarding task checklist.
    
    Returns provisioning details including tasks.
    """
    if account_id in _PROVISIONED_ACCOUNTS:
        return _PROVISIONED_ACCOUNTS[account_id]
    
    config = MOCK_PROVISIONING_CONFIG.get(tier, MOCK_PROVISIONING_CONFIG["Starter"])
    
    tenant_id = f"TEN-{uuid.uuid4().hex[:8].upper()}"
    
    # Create onboarding tasks
    tasks = _create_onboarding_tasks(account_id, tenant_id, tier, customer_name)
    _ONBOARDING_TASKS[account_id] = tasks
    
    # Calculate task summary
    task_summary = _get_task_summary(tasks)
    
    provisioning_result = {
        "tenant_id": tenant_id,
        "account_id": account_id,
        "status": "ACTIVE",
        "tier": tier,
        "provisioned_at": datetime.utcnow().isoformat(),
        "config": config,
        "admin_url": f"https://app.stackadapt.demo/admin/{tenant_id}",
        "api_key": f"sk_live_{uuid.uuid4().hex}",
        "onboarding_tasks": task_summary,
    }
    
    _PROVISIONED_ACCOUNTS[account_id] = provisioning_result
    return provisioning_result


def _get_task_summary(tasks: List[OnboardingTask]) -> dict:
    """Generate a summary of onboarding tasks."""
    total = len(tasks)
    completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
    pending = sum(1 for t in tasks if t.status == TaskStatus.PENDING)
    in_progress = sum(1 for t in tasks if t.status == TaskStatus.IN_PROGRESS)
    blocked = sum(1 for t in tasks if t.status == TaskStatus.BLOCKED)
    
    # Find next action items
    next_actions = []
    for task in tasks:
        if task.status == TaskStatus.PENDING:
            # Check if dependencies are met
            deps_met = all(
                any(t.task_id == dep and t.status == TaskStatus.COMPLETED 
                    for t in tasks)
                for dep in task.depends_on
            ) if task.depends_on else True
            
            if deps_met:
                next_actions.append({
                    "task_id": task.task_id,
                    "name": task.name,
                    "owner": task.owner,
                    "due_date": task.due_date,
                })
    
    return {
        "total_tasks": total,
        "completed": completed,
        "pending": pending,
        "in_progress": in_progress,
        "blocked": blocked,
        "completion_percentage": round((completed / total) * 100) if total > 0 else 0,
        "next_actions": next_actions[:3],  # Top 3 next actions
    }


def get_onboarding_tasks(account_id: str) -> List[dict]:
    """Get all onboarding tasks for an account."""
    tasks = _ONBOARDING_TASKS.get(account_id, [])
    return [t.to_dict() for t in tasks]


def get_task_by_id(account_id: str, task_id: str) -> Optional[dict]:
    """Get a specific task by ID."""
    tasks = _ONBOARDING_TASKS.get(account_id, [])
    for task in tasks:
        if task.task_id == task_id:
            return task.to_dict()
    return None


def update_task_status(
    account_id: str, 
    task_id: str, 
    status: str, 
    completed_by: Optional[str] = None,
    notes: Optional[str] = None
) -> Optional[dict]:
    """
    Update the status of an onboarding task.
    
    This would be called by:
    - The agent (for automated tasks)
    - CS team (via API/UI)
    - Webhooks from the platform (for customer actions)
    """
    tasks = _ONBOARDING_TASKS.get(account_id, [])
    for task in tasks:
        if task.task_id == task_id:
            task.status = TaskStatus(status)
            if status == TaskStatus.COMPLETED.value:
                task.completed_at = datetime.utcnow().isoformat()
                task.completed_by = completed_by or "unknown"
            if notes:
                task.notes = notes
            
            # Update the provisioning record's task summary
            if account_id in _PROVISIONED_ACCOUNTS:
                _PROVISIONED_ACCOUNTS[account_id]["onboarding_tasks"] = _get_task_summary(tasks)
            
            return task.to_dict()
    return None


def get_pending_tasks_by_owner(account_id: str, owner: str) -> List[dict]:
    """Get all pending tasks for a specific owner (cs_team, customer, system)."""
    tasks = _ONBOARDING_TASKS.get(account_id, [])
    return [
        t.to_dict() for t in tasks 
        if t.owner == owner and t.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]
    ]


def get_overdue_tasks(account_id: str) -> List[dict]:
    """Get all overdue tasks."""
    tasks = _ONBOARDING_TASKS.get(account_id, [])
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    return [
        t.to_dict() for t in tasks 
        if t.due_date and t.due_date < today and t.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]
    ]


def get_blocked_tasks(account_id: str) -> List[dict]:
    """Get all blocked tasks."""
    tasks = _ONBOARDING_TASKS.get(account_id, [])
    return [t.to_dict() for t in tasks if t.status == TaskStatus.BLOCKED]


def get_provisioning_status(account_id: str) -> dict:
    """Check if account is already provisioned."""
    if account_id in _PROVISIONED_ACCOUNTS:
        return _PROVISIONED_ACCOUNTS[account_id]
    return {"status": "NOT_PROVISIONED", "account_id": account_id}


def is_provisioned(account_id: str) -> bool:
    """Check if account has been provisioned."""
    return account_id in _PROVISIONED_ACCOUNTS


def deprovision_account(account_id: str) -> dict:
    """Deprovision an account (for testing/cleanup)."""
    if account_id in _PROVISIONED_ACCOUNTS:
        del _PROVISIONED_ACCOUNTS[account_id]
    if account_id in _ONBOARDING_TASKS:
        del _ONBOARDING_TASKS[account_id]
    return {"status": "DEPROVISIONED", "account_id": account_id}


def reset_all():
    """Reset all provisioned accounts (for testing)."""
    _PROVISIONED_ACCOUNTS.clear()
    _ONBOARDING_TASKS.clear()


def simulate_onboarding_progress(account_id: str, profile: str) -> None:
    """
    Simulate time passage and realistic risk conditions for a provisioned account.
    Called after provisioning to create varied risk states for demonstration.

    Profiles:
    - "no_login": 5 days ago, customer never logged in
    - "stalled": 10 days ago, kickoff not done, <30% completion
    - "blocked_sso": 8 days ago, kickoff done but SSO stuck, customer tasks overdue
    """
    if account_id not in _PROVISIONED_ACCOUNTS:
        return

    tasks = _ONBOARDING_TASKS.get(account_id, [])
    if not tasks:
        return

    now = datetime.utcnow()

    if profile == "no_login":
        # Backdate provisioning to 5 days ago
        _PROVISIONED_ACCOUNTS[account_id]["provisioned_at"] = (
            (now - timedelta(days=5)).isoformat()
        )
        # Adjust due dates to be relative to 5 days ago
        base = now - timedelta(days=5)
        for task in tasks:
            if task.due_date:
                offset_days = int(task.due_date.split("-")[-1]) if task.due_date else 0
                # Recalculate due dates from backdated provisioning
                pass
        # Customer login task is still pending — triggers "not logged in" risk
        # (T009 is already pending by default, just need the time gap)

    elif profile == "stalled":
        # Backdate provisioning to 10 days ago
        _PROVISIONED_ACCOUNTS[account_id]["provisioned_at"] = (
            (now - timedelta(days=10)).isoformat()
        )
        # Kickoff NOT scheduled — T005 still pending (overdue since day 1)
        # Everything after kickoff is stuck
        for task in tasks:
            if task.due_date:
                # Make due dates relative to 10 days ago
                original_offset = 0
                for t_def in [
                    ("T005", 1), ("T006", 3), ("T007", 7), ("T008", 10),
                    ("T009", 2), ("T010", 5), ("T011", 7), ("T012", 14),
                    ("T013", 30), ("T014", 45),
                ]:
                    if task.task_id.endswith(t_def[0]):
                        original_offset = t_def[1]
                        break
                if original_offset:
                    task.due_date = (now - timedelta(days=10) + timedelta(days=original_offset)).strftime("%Y-%m-%d")

    elif profile == "blocked_sso":
        # Backdate provisioning to 8 days ago
        base = now - timedelta(days=8)
        _PROVISIONED_ACCOUNTS[account_id]["provisioned_at"] = base.isoformat()

        for task in tasks:
            # Recalculate due dates from 8 days ago
            for t_def in [
                ("T005", 1), ("T006", 3), ("T007", 7), ("T008", 10),
                ("T009", 2), ("T010", 5), ("T011", 7), ("T012", 14),
                ("T013", 30), ("T014", 45),
            ]:
                if task.task_id.endswith(t_def[0]):
                    task.due_date = (base + timedelta(days=t_def[1])).strftime("%Y-%m-%d")
                    break

        # Simulate: kickoff was scheduled and done
        for task in tasks:
            if task.task_id.endswith("T005"):
                task.status = TaskStatus.COMPLETED
                task.completed_at = (base + timedelta(days=1)).isoformat()
                task.completed_by = "cs_team"
            elif task.task_id.endswith("T006"):
                task.status = TaskStatus.COMPLETED
                task.completed_at = (base + timedelta(days=3)).isoformat()
                task.completed_by = "cs_team"
            # SSO still pending (overdue — due day 7, now day 8)
            elif task.task_id.endswith("T007"):
                task.status = TaskStatus.BLOCKED
                task.notes = "Waiting on customer IT team for IdP metadata"
            # Customer logged in but tour not done (overdue)
            elif task.task_id.endswith("T009"):
                task.status = TaskStatus.COMPLETED
                task.completed_at = (base + timedelta(days=2)).isoformat()
                task.completed_by = "customer"
            elif task.task_id.endswith("T010"):
                pass  # Still pending, overdue (due day 5, now day 8)
            elif task.task_id.endswith("T011"):
                pass  # Still pending, overdue (due day 7, now day 8)


# ============================================================================
# MONITORING & CS ASSISTANT FUNCTIONS
# ============================================================================

def check_onboarding_progress(account_id: str) -> dict:
    """
    Get a dashboard-style view of onboarding progress for an account.

    Returns completion %, task breakdown by status, overdue/blocked counts,
    days since provisioning, and a health_status assessment.
    """
    if account_id not in _PROVISIONED_ACCOUNTS:
        return {"status": "NOT_PROVISIONED", "account_id": account_id}

    prov = _PROVISIONED_ACCOUNTS[account_id]
    tasks = _ONBOARDING_TASKS.get(account_id, [])
    today = datetime.utcnow()
    prov_date = datetime.fromisoformat(prov["provisioned_at"])
    days_since = (today - prov_date).days

    total = len(tasks)
    completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
    skipped = sum(1 for t in tasks if t.status == TaskStatus.SKIPPED)
    pending = sum(1 for t in tasks if t.status == TaskStatus.PENDING)
    in_progress = sum(1 for t in tasks if t.status == TaskStatus.IN_PROGRESS)
    blocked = sum(1 for t in tasks if t.status == TaskStatus.BLOCKED)

    actionable = total - skipped
    pct = round((completed / actionable) * 100) if actionable > 0 else 0

    overdue = get_overdue_tasks(account_id)

    # Health assessment
    if blocked > 0 or len(overdue) >= 3:
        health = "stalled"
    elif len(overdue) > 0 or (pct < 30 and days_since > 7):
        health = "at_risk"
    else:
        health = "on_track"

    return {
        "account_id": account_id,
        "tenant_id": prov.get("tenant_id"),
        "tier": prov.get("tier"),
        "days_since_provisioning": days_since,
        "completion_percentage": pct,
        "health_status": health,
        "task_breakdown": {
            "total": total,
            "completed": completed,
            "pending": pending,
            "in_progress": in_progress,
            "blocked": blocked,
            "skipped": skipped,
        },
        "overdue_tasks": overdue,
        "blocked_tasks": get_blocked_tasks(account_id),
        "next_actions": _get_task_summary(tasks).get("next_actions", []),
    }


def identify_onboarding_risks(account_id: str) -> dict:
    """
    Detect risks and problems that need CS attention.

    Checks for: customer not logging in, SSO not configured after kickoff,
    tasks blocked, onboarding stalling, customer actions overdue.
    """
    if account_id not in _PROVISIONED_ACCOUNTS:
        return {"status": "NOT_PROVISIONED", "account_id": account_id}

    prov = _PROVISIONED_ACCOUNTS[account_id]
    tasks = _ONBOARDING_TASKS.get(account_id, [])
    today = datetime.utcnow()
    prov_date = datetime.fromisoformat(prov["provisioned_at"])
    days_since = (today - prov_date).days
    risks = []

    # Risk: customer hasn't verified login within 3 days
    login_task = next((t for t in tasks if "Verify Login" in t.name), None)
    if login_task and login_task.status == TaskStatus.PENDING and days_since >= 3:
        risks.append({
            "severity": "high",
            "risk": "Customer has not logged in",
            "detail": f"{days_since} days since provisioning, login not verified",
            "task_id": login_task.task_id,
            "recommendation": "Send reminder email and Slack DM to account owner",
        })

    # Risk: SSO not configured after kickoff (Enterprise only)
    sso_task = next((t for t in tasks if "SSO" in t.name and t.status != TaskStatus.SKIPPED), None)
    kickoff_task = next((t for t in tasks if "Conduct Kickoff" in t.name), None)
    if sso_task and kickoff_task and kickoff_task.status == TaskStatus.COMPLETED and sso_task.status == TaskStatus.PENDING:
        risks.append({
            "severity": "medium",
            "risk": "SSO not configured after kickoff",
            "detail": "Kickoff complete but SSO integration not started",
            "task_id": sso_task.task_id,
            "recommendation": "Follow up with customer IT team about SSO requirements",
        })

    # Risk: tasks blocked
    blocked = [t for t in tasks if t.status == TaskStatus.BLOCKED]
    for t in blocked:
        risks.append({
            "severity": "high",
            "risk": f"Task blocked: {t.name}",
            "detail": t.notes or "No details",
            "task_id": t.task_id,
            "recommendation": "Investigate blocker and unblock or escalate",
        })

    # Risk: onboarding stalling (<30% complete after 7 days)
    total = len(tasks)
    completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
    skipped = sum(1 for t in tasks if t.status == TaskStatus.SKIPPED)
    actionable = total - skipped
    pct = (completed / actionable * 100) if actionable > 0 else 0
    if pct < 30 and days_since > 7:
        risks.append({
            "severity": "high",
            "risk": "Onboarding stalling",
            "detail": f"Only {pct:.0f}% complete after {days_since} days",
            "recommendation": "Escalate to CS management — customer may need additional support",
        })

    # Risk: customer actions overdue
    today_str = today.strftime("%Y-%m-%d")
    overdue_customer = [
        t for t in tasks
        if t.owner == "customer"
        and t.due_date and t.due_date < today_str
        and t.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]
    ]
    for t in overdue_customer:
        risks.append({
            "severity": "medium",
            "risk": f"Customer action overdue: {t.name}",
            "detail": f"Due {t.due_date}, still {t.status.value}",
            "task_id": t.task_id,
            "recommendation": "Send task reminder to customer contact",
        })

    return {
        "account_id": account_id,
        "risk_count": len(risks),
        "risks": risks,
    }


def send_task_reminder(
    account_id: str,
    task_id: str,
    recipient: str = "",
    message: str = "",
) -> dict:
    """
    Send a reminder about a pending onboarding task.

    In production this would send an email/Slack message. For the mock,
    it records the reminder as a note on the task.
    """
    tasks = _ONBOARDING_TASKS.get(account_id, [])
    task = next((t for t in tasks if t.task_id == task_id), None)

    if not task:
        return {"status": "NOT_FOUND", "task_id": task_id}

    reminder_note = (
        f"Reminder sent to {recipient or task.owner} "
        f"at {datetime.utcnow().isoformat()}: {message or task.description}"
    )
    task.notes = (task.notes + " | " + reminder_note) if task.notes else reminder_note

    return {
        "status": "SENT",
        "task_id": task_id,
        "task_name": task.name,
        "recipient": recipient or task.owner,
        "message": message or f"Reminder: {task.name} is {task.status.value} (due {task.due_date})",
        "channel": "email" if "@" in (recipient or "") else "slack",
    }


def escalate_stalled_onboarding(account_id: str, reason: str = "") -> dict:
    """
    Escalate a stalled onboarding to CS management.

    Posts to #cs-onboarding-escalations with progress details.
    """
    progress = check_onboarding_progress(account_id)
    if progress.get("status") == "NOT_PROVISIONED":
        return {"status": "NOT_PROVISIONED", "account_id": account_id}

    return {
        "status": "ESCALATED",
        "account_id": account_id,
        "channel": "#cs-onboarding-escalations",
        "reason": reason or "Onboarding stalled — needs management attention",
        "progress_snapshot": {
            "completion": progress["completion_percentage"],
            "health": progress["health_status"],
            "days_since_provisioning": progress["days_since_provisioning"],
            "overdue_count": len(progress["overdue_tasks"]),
            "blocked_count": progress["task_breakdown"]["blocked"],
        },
        "escalated_at": datetime.utcnow().isoformat(),
    }


def get_all_active_onboardings() -> List[dict]:
    """
    Get summary of all currently active onboardings.
    Used by the Streamlit dashboard.
    """
    results = []
    for account_id, prov in _PROVISIONED_ACCOUNTS.items():
        progress = check_onboarding_progress(account_id)
        results.append({
            "account_id": account_id,
            "tenant_id": prov.get("tenant_id"),
            "tier": prov.get("tier"),
            "completion_percentage": progress.get("completion_percentage", 0),
            "health_status": progress.get("health_status", "unknown"),
            "days_since_provisioning": progress.get("days_since_provisioning", 0),
            "overdue_count": len(progress.get("overdue_tasks", [])),
            "blocked_count": progress.get("task_breakdown", {}).get("blocked", 0),
        })
    return results


# ---------------------------------------------------------------------------
# Proactive Alerts & Portfolio (Enhancements 1-3)
# ---------------------------------------------------------------------------

def get_all_alerts() -> List[dict]:
    """
    Scan ALL provisioned accounts and aggregate risks into a single
    alert list, sorted by severity (critical > high > medium > low).
    """
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    all_alerts: List[dict] = []

    for account_id in list(_PROVISIONED_ACCOUNTS.keys()):
        risks = identify_onboarding_risks(account_id)
        for risk in risks.get("risks", []):
            alert = dict(risk)
            alert["account_id"] = account_id
            all_alerts.append(alert)

    all_alerts.sort(key=lambda a: severity_order.get(a.get("severity", "low"), 4))
    return all_alerts


def get_portfolio_summary() -> dict:
    """
    Aggregate portfolio-level stats across ALL provisioned accounts.
    Returns health distribution, account list, and top priority actions.
    """
    health_dist: Dict[str, int] = {
        "on_track": 0, "at_risk": 0, "stalled": 0,
    }
    accounts: List[dict] = []

    for account_id, prov in _PROVISIONED_ACCOUNTS.items():
        progress = check_onboarding_progress(account_id)
        health = progress.get("health_status", "unknown")
        if health in health_dist:
            health_dist[health] += 1

        accounts.append({
            "account_id": account_id,
            "decision": "PROCEED",
            "tier": prov.get("tier"),
            "health_status": health,
            "completion_percentage": progress.get("completion_percentage", 0),
            "days_since_provisioning": progress.get("days_since_provisioning", 0),
            "overdue_count": len(progress.get("overdue_tasks", [])),
            "blocked_count": progress.get("task_breakdown", {}).get("blocked", 0),
        })

    # Top 5 priority actions from alerts
    priority_actions = get_all_alerts()[:5]

    return {
        "total_accounts": len(accounts),
        "health_distribution": health_dist,
        "accounts": accounts,
        "priority_actions": priority_actions,
    }


def generate_suggested_actions(account_id: str) -> List[dict]:
    """
    Map identified risks for an account to concrete executable actions.
    Each action has a type, description, and the params needed to execute it.
    """
    risks = identify_onboarding_risks(account_id)
    actions: List[dict] = []
    action_counter = 0

    for risk in risks.get("risks", []):
        risk_text = risk.get("risk", "")
        task_id = risk.get("task_id", "")
        severity = risk.get("severity", "medium")
        action_counter += 1
        action_id = f"act-{account_id}-{action_counter}"

        if "not logged in" in risk_text.lower():
            actions.append({
                "action_id": action_id,
                "action_type": "send_login_reminder",
                "description": f"Send login reminder to {account_id} customer",
                "account_id": account_id,
                "icon": "📧",
                "severity": severity,
                "task_id": task_id or f"{account_id}-T009",
                "params": {
                    "recipient": "customer",
                    "message": "Please log in to your new account to continue onboarding setup.",
                },
            })
        elif "overdue" in risk_text.lower() and "customer" in risk_text.lower():
            actions.append({
                "action_id": action_id,
                "action_type": "send_task_reminder",
                "description": f"Send reminder for overdue task to {account_id}",
                "account_id": account_id,
                "icon": "⏰",
                "severity": severity,
                "task_id": task_id,
                "params": {
                    "recipient": "customer",
                    "message": f"Reminder: Your onboarding task is overdue. Please complete it to proceed.",
                },
            })
        elif "stalling" in risk_text.lower():
            actions.append({
                "action_id": action_id,
                "action_type": "escalate",
                "description": f"Escalate {account_id} — onboarding stalled",
                "account_id": account_id,
                "icon": "🚨",
                "severity": severity,
                "task_id": "",
                "params": {
                    "reason": "Onboarding stalled — proactive escalation by risk detection",
                },
            })
        elif "blocked" in risk_text.lower():
            actions.append({
                "action_id": action_id,
                "action_type": "escalate_blocked",
                "description": f"Escalate blocked task for {account_id}",
                "account_id": account_id,
                "icon": "🚧",
                "severity": severity,
                "task_id": task_id,
                "params": {
                    "reason": f"Task {task_id} is blocked — needs investigation",
                },
            })
        elif "sso" in risk_text.lower():
            actions.append({
                "action_id": action_id,
                "action_type": "schedule_sso_followup",
                "description": f"Start SSO follow-up for {account_id}",
                "account_id": account_id,
                "icon": "🔐",
                "severity": severity,
                "task_id": task_id or f"{account_id}-T007",
                "params": {},
            })

    return actions


def get_all_suggested_actions() -> List[dict]:
    """Get suggested actions across all provisioned accounts, sorted by severity."""
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    all_actions: List[dict] = []

    for account_id in list(_PROVISIONED_ACCOUNTS.keys()):
        all_actions.extend(generate_suggested_actions(account_id))

    all_actions.sort(key=lambda a: severity_order.get(a.get("severity", "low"), 4))
    return all_actions
