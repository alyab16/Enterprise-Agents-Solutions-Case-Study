from .generator import (
    generate_email_html,
    generate_blocked_notification_email,
    generate_escalation_notification_email,   # <-- ADD THIS
    generate_success_notification_email,
    generate_customer_welcome_email,
    generate_api_error_notification_email,
    generate_run_report_markdown,
    generate_full_run_report,
    save_email_html,
    save_report_markdown,
    save_audit_json,
    REPORTS_DIR,
)

__all__ = [
    "generate_email_html",
    "generate_blocked_notification_email",
    "generate_escalation_notification_email",   # <-- ADD THIS
    "generate_success_notification_email",
    "generate_customer_welcome_email",
    "generate_api_error_notification_email",
    "generate_run_report_markdown",
    "generate_full_run_report",
    "save_email_html",
    "save_report_markdown",
    "save_audit_json",
    "REPORTS_DIR",
]