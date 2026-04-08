#!/usr/bin/env python3
"""
Demo Runner Script for Enterprise Onboarding Agent

This script demonstrates the agent's capabilities by running through
multiple scenarios and displaying the results in a clear, visual format.

Usage:
    python -m app.scripts.demo_runner --scenario SCENARIO_ID
    python -m app.scripts.demo_runner --list
"""

import sys
import os
import argparse
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.agent import run_onboarding
from app.notifications import get_sent_notifications, clear_notifications
from app.integrations.provisioning import reset_all as reset_provisioning


# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    DIM = '\033[2m'


def print_header(text: str):
    """Print a formatted header."""
    width = 70
    print()
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * width}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(width)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * width}{Colors.ENDC}")
    print()


def print_section(text: str):
    """Print a section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}▶ {text}{Colors.ENDC}")
    print(f"{Colors.DIM}{'-' * 50}{Colors.ENDC}")


def print_decision(decision: str):
    """Print the decision with appropriate color."""
    if decision == "PROCEED":
        color = Colors.GREEN
        emoji = "✅"
    elif decision == "ESCALATE":
        color = Colors.YELLOW
        emoji = "⚠️"
    else:  # BLOCK
        color = Colors.RED
        emoji = "🚫"
    
    print(f"\n{Colors.BOLD}Decision: {color}{emoji} {decision}{Colors.ENDC}")


def print_risk_level(level: str):
    """Print risk level with color."""
    colors = {
        "low": Colors.GREEN,
        "medium": Colors.YELLOW,
        "high": Colors.RED,
        "critical": Colors.RED + Colors.BOLD,
    }
    color = colors.get(level, Colors.ENDC)
    print(f"Risk Level: {color}{level.upper()}{Colors.ENDC}")


def print_violations(violations: dict):
    """Print violations."""
    if not violations or all(not v for v in violations.values()):
        print(f"  {Colors.GREEN}None{Colors.ENDC}")
        return
    
    for domain, messages in violations.items():
        for msg in messages:
            print(f"  {Colors.RED}✗ [{domain}]{Colors.ENDC} {msg}")


def print_warnings(warnings: dict):
    """Print warnings."""
    if not warnings or all(not v for v in warnings.values()):
        print(f"  {Colors.GREEN}None{Colors.ENDC}")
        return
    
    for domain, messages in warnings.items():
        for msg in messages:
            print(f"  {Colors.YELLOW}⚠ [{domain}]{Colors.ENDC} {msg}")


def print_notifications(notifications: list):
    """Print notifications sent."""
    if not notifications:
        print(f"  {Colors.DIM}None{Colors.ENDC}")
        return
    
    for notif in notifications:
        channel = notif.get("channel", notif.get("to", "unknown"))
        notif_type = notif.get("type", "unknown")
        emoji = "💬" if notif_type == "slack" else "📧"
        print(f"  {emoji} {Colors.CYAN}{notif_type}{Colors.ENDC} → {channel}")


def print_actions(actions: list):
    """Print actions taken."""
    if not actions:
        print(f"  {Colors.DIM}None{Colors.ENDC}")
        return
    
    for action in actions:
        action_type = action.get("type", "unknown")
        print(f"  🔧 {Colors.GREEN}{action_type}{Colors.ENDC}: {action}")


def print_recommendations(recommendations: list):
    """Print recommended actions."""
    if not recommendations:
        print(f"  {Colors.DIM}No specific recommendations{Colors.ENDC}")
        return
    
    for i, rec in enumerate(recommendations, 1):
        if isinstance(rec, dict):
            action = rec.get("action", str(rec))
            owner = rec.get("owner", "")
            owner_str = f" ({Colors.CYAN}{owner}{Colors.ENDC})" if owner else ""
            print(f"  {i}. {action}{owner_str}")
        else:
            print(f"  {i}. {rec}")


def run_scenario(account_id: str, name: str, description: str):
    """Run a single demo scenario."""
    
    print_header(f"Scenario: {name}")
    print(f"{Colors.DIM}Account ID: {account_id}{Colors.ENDC}")
    print(f"{Colors.DIM}{description}{Colors.ENDC}")
    
    # Clear state for clean run
    clear_notifications()
    
    # Run the onboarding
    print(f"\n{Colors.DIM}Running onboarding workflow...{Colors.ENDC}")
    
    result = run_onboarding(
        account_id=account_id,
        event_type="demo.cli",
    )
    
    # Print results
    print_decision(result.get("decision", "UNKNOWN"))
    
    risk_analysis = result.get("risk_analysis", {})
    if risk_analysis.get("risk_level"):
        print_risk_level(risk_analysis.get("risk_level"))
    
    # Summary
    summary = risk_analysis.get("summary") or result.get("human_summary")
    if summary:
        print_section("Summary")
        print(f"  {summary}")
    
    # Violations
    print_section("Violations (Blocking)")
    print_violations(result.get("violations", {}))
    
    # Warnings
    print_section("Warnings (Non-blocking)")
    print_warnings(result.get("warnings", {}))
    
    # Recommended Actions
    print_section("Recommended Actions")
    recs = risk_analysis.get("recommended_actions", result.get("recommended_actions", []))
    print_recommendations(recs)
    
    # Actions Taken
    print_section("Actions Taken by Agent")
    print_actions(result.get("actions_taken", []))
    
    # Notifications
    print_section("Notifications Sent")
    notifications = get_sent_notifications(account_id)
    print_notifications(notifications)
    
    # Provisioning
    if result.get("provisioning"):
        print_section("Provisioning Result")
        prov = result.get("provisioning")
        print(f"  {Colors.GREEN}✓ Tenant ID:{Colors.ENDC} {prov.get('tenant_id')}")
        print(f"  {Colors.GREEN}✓ Status:{Colors.ENDC} {prov.get('status')}")
        print(f"  {Colors.GREEN}✓ Tier:{Colors.ENDC} {prov.get('tier')}")
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Demo Runner for Enterprise Onboarding Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m app.scripts.demo_runner --scenario ACME-001    Run specific scenario
    python -m app.scripts.demo_runner --list                 List available scenarios
        """
    )

    parser.add_argument(
        "--scenario", "-s",
        type=str,
        help="Run a specific scenario by account ID"
    )

    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available scenarios"
    )

    args = parser.parse_args()

    scenario_map = {
        "ACME-001": ("Happy Path - Full Success", "Enterprise customer with all data in order. Contract signed, invoice paid."),
        "BETA-002": ("Blocked - Opportunity Not Won", "Opportunity still in negotiation. Contract in draft. Cannot proceed."),
        "GAMMA-003": ("Escalation - Overdue Invoice", "Deal closed but invoice overdue. Needs finance review."),
        "DELETED-004": ("Blocked - Deleted Account", "Account marked as deleted in Salesforce."),
        "MISSING-999": ("Blocked - Account Not Found", "Account does not exist in any system."),
        "FOREX-005": ("Escalation - FX Invoice Mismatch", "Invoice in CAD vs USD opportunity. Currency conversion reveals gap beyond 2% threshold."),
        "PARTIAL-006": ("Escalation - Partial Payment Gap", "Invoice partially paid. 5% underpayment exceeds 2% threshold."),
        "STARTER-007": ("Proceed - Customer Not Logged In", "All checks pass, provisioned 5 days ago, but customer has not logged in yet."),
        "GROWTH-008": ("Proceed - Stalled Onboarding", "All checks pass, provisioned 10 days ago, kickoff not done, <30% completion."),
        "ENTERPRISE-009": ("Proceed - SSO & Blocked Tasks", "All checks pass, provisioned 8 days ago, SSO not configured, customer tasks overdue."),
    }

    if args.list:
        print_header("Available Demo Scenarios")
        for sid, (sname, sdesc) in scenario_map.items():
            print(f"  {Colors.CYAN}{sid:<18}{Colors.ENDC} {sname}")
        print()
        return

    if args.scenario:
        if args.scenario in scenario_map:
            name, desc = scenario_map[args.scenario]
            run_scenario(args.scenario, name, desc)
        else:
            print(f"{Colors.RED}Unknown scenario: {args.scenario}{Colors.ENDC}")
            print("Use --list to see available scenarios")
            sys.exit(1)
        return

    # Default: show usage
    parser.print_help()


if __name__ == "__main__":
    main()
