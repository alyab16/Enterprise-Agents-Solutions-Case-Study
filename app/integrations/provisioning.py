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
