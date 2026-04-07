"""
Streamlit UI for the Enterprise Onboarding Agent.

Provides three views:
1. Dashboard — all onboarding results with progress, health, and risks
2. Run Onboarding — trigger scenarios and view results
3. Chat with Agent — interactive CS assistant for monitoring and actions

Start with:
    streamlit run streamlit_app.py

Requires the FastAPI backend running on port 8000:
    python main.py
"""

import streamlit as st
import requests
import uuid

API_BASE = "http://localhost:8000/demo"

st.set_page_config(
    page_title="Enterprise Onboarding Agent",
    page_icon="🤖",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def api_get(path: str, timeout: int = 30):
    """GET request to the FastAPI backend."""
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=timeout)
        return r.json()
    except requests.ConnectionError:
        st.error("Cannot connect to API. Start the backend with `python main.py`.")
        return None
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def api_post(path: str, timeout: int = 120, **kwargs):
    """POST request to the FastAPI backend."""
    try:
        r = requests.post(f"{API_BASE}{path}", timeout=timeout, **kwargs)
        return r.json()
    except requests.ConnectionError:
        st.error("Cannot connect to API. Start the backend with `python main.py`.")
        return None
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def health_badge(status: str) -> str:
    """Return a colored badge for health status."""
    colors = {
        "on_track": "🟢", "at_risk": "🟡", "stalled": "🔴",
        "blocked": "🔴", "escalated": "🟡",
    }
    return f"{colors.get(status, '⚪')} {status.replace('_', ' ').title()}"


def decision_badge(decision: str) -> str:
    """Return a colored badge for decision."""
    icons = {"PROCEED": "✅", "BLOCK": "🚫", "ESCALATE": "⚠️"}
    return f"{icons.get(decision, '❓')} {decision}"


def decision_color(decision: str) -> str:
    """Return a color for the decision."""
    return {"PROCEED": "green", "BLOCK": "red", "ESCALATE": "orange"}.get(decision, "gray")


# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_session_id" not in st.session_state:
    st.session_state.chat_session_id = str(uuid.uuid4())[:8]
if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None
if "dismissed_actions" not in st.session_state:
    st.session_state.dismissed_actions = set()


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------

page = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Portfolio Overview", "Run Onboarding", "Chat with Agent"],
    index=0,
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Enterprise Onboarding Agent**")
st.sidebar.markdown("Pydantic AI + FastMCP")
st.sidebar.markdown(
    "[API Docs](http://localhost:8000/docs) | "
    "[GitHub](https://github.com/alyab16/Enterprise-Agents-Solutions-Case-Study)"
)


# ============================================================================
# PAGE 1: DASHBOARD
# ============================================================================

if page == "Dashboard":
    st.title("Onboarding Dashboard")

    col_refresh, col_reset = st.columns([1, 1])
    with col_refresh:
        refresh = st.button("Refresh", use_container_width=True)
    with col_reset:
        if st.button("Reset All", use_container_width=True):
            api_post("/reset")
            st.session_state.dismissed_actions = set()
            st.rerun()

    # --- Proactive Alerts Panel (grouped by account) ---
    alerts_data = api_get("/alerts")
    if alerts_data and alerts_data.get("alert_count", 0) > 0:
        # Group alerts by account
        from collections import OrderedDict
        alerts_by_account: dict[str, list] = OrderedDict()
        for alert in alerts_data["alerts"]:
            aid = alert["account_id"]
            alerts_by_account.setdefault(aid, []).append(alert)

        account_count = len(alerts_by_account)
        st.subheader(f"Alerts & Actions Needed ({account_count} accounts)")
        for aid, account_alerts in alerts_by_account.items():
            # Highest severity for this account
            top_sev = account_alerts[0].get("severity", "low")
            sev_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}.get(top_sev, "⚪")
            with st.expander(f"{sev_icon} **{aid}** — {len(account_alerts)} alert(s)"):
                for alert in account_alerts:
                    item_sev = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}.get(
                        alert.get("severity", ""), "⚪"
                    )
                    st.markdown(
                        f"{item_sev} **{alert['risk']}**  \n"
                        f"{alert['detail']}  \n"
                        f"*Recommended:* {alert['recommendation']}"
                    )
                    st.markdown("")
        st.markdown("---")

    # --- Smart Suggested Actions (grouped by account) ---
    actions_data = api_get("/suggested-actions")
    if actions_data and actions_data.get("action_count", 0) > 0:
        visible_actions = [
            a for a in actions_data["actions"]
            if a.get("action_id") not in st.session_state.dismissed_actions
        ]
        if visible_actions:
            st.subheader(f"Suggested Actions ({len(visible_actions)} accounts)")
            for action in visible_actions:
                sub_actions = action.get("sub_actions", [])
                account_id = action["account_id"]

                # Build per-sub-action detail lines
                detail_lines = []
                for sub in sub_actions:
                    action_type = sub.get("action_type", "")
                    if action_type == "send_login_reminder":
                        detail_lines.append(
                            "Customer has not logged in since provisioning — send a reminder email."
                        )
                    elif action_type == "send_task_reminder":
                        detail_lines.append(
                            "An onboarding task is overdue — send a reminder to the task owner."
                        )
                    elif action_type == "escalate":
                        detail_lines.append(
                            "Onboarding has stalled with low completion — escalate to CS management."
                        )
                    elif action_type == "escalate_blocked":
                        detail_lines.append(
                            "A task is blocked and preventing progress — escalate for investigation."
                        )
                    elif action_type == "schedule_sso_followup":
                        detail_lines.append(
                            "SSO integration not configured after kickoff — start follow-up with customer IT."
                        )
                    elif action_type == "rerun_onboarding":
                        detail_lines.append(
                            "Onboarding was previously blocked — re-run to check if issues are resolved."
                        )
                    elif action_type == "review_escalation":
                        detail_lines.append(
                            "Onboarding was escalated due to warnings — mark as reviewed."
                        )
                    elif action_type == "schedule_sentiment_call":
                        detail_lines.append(
                            "Customer sentiment is negative — schedule a proactive check-in call."
                        )
                    else:
                        detail_lines.append(sub["description"])

                with st.container():
                    st.markdown(
                        f"{action.get('icon', '📋')} **{account_id}**: "
                        f"{action['description']}"
                    )
                    if len(detail_lines) == 1:
                        st.caption(detail_lines[0])
                    else:
                        for i, line in enumerate(detail_lines, 1):
                            st.caption(f"{i}. {line}")

                    col_approve, col_dismiss, col_spacer = st.columns([1, 1, 6])
                    with col_approve:
                        if st.button("Approve All" if len(sub_actions) > 1 else "Approve",
                                     key=f"approve_{action['action_id']}", type="primary"):
                            for sub in sub_actions:
                                api_post("/execute-action", json={
                                    "action_type": sub["action_type"],
                                    "account_id": sub["account_id"],
                                    "task_id": sub.get("task_id", ""),
                                    "params": sub.get("params", {}),
                                })
                            st.toast(f"{'All actions' if len(sub_actions) > 1 else 'Action'} executed for {account_id}")
                            st.rerun()
                    with col_dismiss:
                        if st.button("Dismiss", key=f"dismiss_{action['action_id']}"):
                            st.session_state.dismissed_actions.add(action["action_id"])
                            st.rerun()
                    st.markdown("")
            st.markdown("---")

    data = api_get("/active-onboardings")
    if data and data.get("onboardings"):
        onboardings = data["onboardings"]

        # Count by decision
        proceed_count = sum(1 for o in onboardings if o.get("decision") == "PROCEED")
        block_count = sum(1 for o in onboardings if o.get("decision") == "BLOCK")
        escalate_count = sum(1 for o in onboardings if o.get("decision") == "ESCALATE")

        # Metric cards
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Processed", len(onboardings))
        c2.metric("Proceeded", proceed_count)
        c3.metric("Blocked", block_count)
        c4.metric("Escalated", escalate_count)

        st.markdown("---")

        # Group by decision for clarity
        for decision_group, label in [("PROCEED", "Provisioned"), ("ESCALATE", "Escalated"), ("BLOCK", "Blocked")]:
            group = [o for o in onboardings if o.get("decision") == decision_group]
            if not group:
                continue

            st.subheader(f"{decision_badge(decision_group)} {label} ({len(group)})")

            for o in group:
                account_id = o["account_id"]
                scenario = o.get("scenario_name", "")

                if decision_group == "PROCEED":
                    with st.expander(
                        f"{health_badge(o['health_status'])}  **{account_id}** — "
                        f"{o['completion_percentage']}% complete  |  "
                        f"{o.get('tier', '')}  |  Day {o['days_since_provisioning']}"
                    ):
                        pc1, pc2, pc3, pc4 = st.columns(4)
                        pc1.metric("Completion", f"{o['completion_percentage']}%")
                        pc2.metric("Overdue Tasks", o["overdue_count"])
                        pc3.metric("Blocked Tasks", o["blocked_count"])
                        # Sentiment indicator
                        sent = o.get("sentiment", {})
                        sent_label = sent.get("label", "neutral")
                        sent_icon = {"positive": "😊", "neutral": "😐", "negative": "😟"}.get(sent_label, "😐")
                        sent_trend = sent.get("trend", "stable")
                        trend_arrow = {"improving": " ↑", "declining": " ↓", "stable": ""}.get(sent_trend, "")
                        pc4.metric("Sentiment", f"{sent_icon} {sent_label.title()}{trend_arrow}")

                        if o.get("summary"):
                            st.markdown(f"**Summary:** {o['summary']}")

                        # Progress detail
                        progress = api_get(f"/progress/{account_id}")
                        if progress and progress.get("next_actions"):
                            st.markdown("**Next Actions:**")
                            for action in progress["next_actions"]:
                                st.markdown(
                                    f"- `{action['task_id']}` {action['name']} "
                                    f"(owner: {action['owner']}, due: {action.get('due_date', 'N/A')})"
                                )

                        # Risks
                        risks = api_get(f"/risks/{account_id}")
                        if risks and risks.get("risk_count", 0) > 0:
                            st.markdown("**Risks:**")
                            for risk in risks["risks"]:
                                sev = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(risk["severity"], "⚪")
                                st.markdown(f"- {sev} **{risk['risk']}**: {risk['detail']}")

                elif decision_group == "BLOCK":
                    with st.expander(f"🚫  **{account_id}** — {scenario}"):
                        if o.get("summary"):
                            st.markdown(f"**Summary:** {o['summary']}")
                        violations = o.get("violations", {})
                        if violations:
                            st.markdown("**Violations:**")
                            for domain, msgs in violations.items():
                                msg_list = msgs if isinstance(msgs, list) else [msgs]
                                for msg in msg_list:
                                    st.error(f"**{domain}**: {msg}")
                        st.markdown(f"Violation count: {o.get('violation_count', 0)}")

                elif decision_group == "ESCALATE":
                    with st.expander(f"⚠️  **{account_id}** — {scenario}"):
                        if o.get("summary"):
                            st.markdown(f"**Summary:** {o['summary']}")
                        warnings = o.get("warnings", {})
                        if warnings:
                            st.markdown("**Warnings:**")
                            for domain, msgs in warnings.items():
                                msg_list = msgs if isinstance(msgs, list) else [msgs]
                                for msg in msg_list:
                                    st.warning(f"**{domain}**: {msg}")
                        st.markdown(f"Warning count: {o.get('warning_count', 0)}")

    else:
        st.info(
            "No onboarding results yet. Use the **Run Onboarding** page to "
            "process a scenario, then return here to see the dashboard."
        )


# ============================================================================
# PAGE 2: PORTFOLIO OVERVIEW
# ============================================================================

elif page == "Portfolio Overview":
    st.title("Portfolio Overview")

    data = api_get("/portfolio-summary")
    if not data or not data.get("accounts"):
        st.info(
            "No accounts in portfolio yet. Use the **Run Onboarding** page "
            "to process scenarios, then return here."
        )
    else:
        # Row 1: Health distribution metrics
        dist = data.get("health_distribution", {})
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("On Track", dist.get("on_track", 0))
        c2.metric("At Risk", dist.get("at_risk", 0))
        c3.metric("Stalled", dist.get("stalled", 0))
        c4.metric("Blocked", dist.get("blocked", 0))
        c5.metric("Escalated", dist.get("escalated", 0))

        st.markdown("---")

        # Row 2: Priority Action Queue
        priority = data.get("priority_actions", [])
        if priority:
            st.subheader("Priority Actions Today")
            for i, action in enumerate(priority[:5], 1):
                sev_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡"}.get(
                    action.get("severity", ""), "⚪"
                )
                st.markdown(
                    f"{i}. {sev_icon} **{action['account_id']}**: "
                    f"{action.get('recommendation', action.get('risk', ''))}"
                )
            st.markdown("---")

        # Row 3: Account summary table
        st.subheader(f"All Accounts ({data['total_accounts']})")
        import pandas as pd

        accounts = data["accounts"]
        df = pd.DataFrame(accounts)
        display_cols = [
            "account_id", "decision", "health_status", "completion_percentage",
            "days_since_provisioning", "overdue_count", "tier",
        ]
        available_cols = [c for c in display_cols if c in df.columns]
        if available_cols:
            st.dataframe(
                df[available_cols].rename(columns={
                    "account_id": "Account",
                    "decision": "Decision",
                    "health_status": "Health",
                    "completion_percentage": "Completion %",
                    "days_since_provisioning": "Days",
                    "overdue_count": "Overdue",
                    "tier": "Tier",
                }),
                use_container_width=True,
                hide_index=True,
            )


# ============================================================================
# PAGE 3: RUN ONBOARDING
# ============================================================================

elif page == "Run Onboarding":
    st.title("Run Onboarding Scenario")

    scenarios = api_get("/scenarios")
    if not scenarios:
        st.stop()

    scenario_list = scenarios.get("scenarios", [])
    options = {f"{s['id']} — {s['name']}": s for s in scenario_list}

    selected = st.selectbox("Select Scenario", list(options.keys()))
    scenario = options[selected]

    st.markdown(f"**Description:** {scenario['description']}")
    st.markdown(f"**Expected Decision:** `{scenario['expected_decision']}`")

    generate_report = st.checkbox("Generate reports", value=False)

    if st.button("Run Onboarding", type="primary", use_container_width=True):
        with st.spinner(f"Running onboarding for {scenario['id']}..."):
            result = api_post(
                f"/run/{scenario['id']}?generate_report={'true' if generate_report else 'false'}"
            )

        if result:
            decision = result.get("decision", "UNKNOWN")
            color = decision_color(decision)

            st.markdown(f"### Decision: :{color}[{decision}]")
            st.markdown(f"**Summary:** {result.get('summary', 'N/A')}")

            # Violations, warnings, execution actions, live risks, provisioning
            tab_v, tab_w, tab_a, tab_r, tab_p = st.tabs(
                ["Violations", "Warnings", "Actions", "Risks", "Provisioning"]
            )

            with tab_v:
                violations = result.get("violations", {})
                if violations:
                    for domain, msgs in violations.items():
                        msg_list = msgs if isinstance(msgs, list) else [msgs]
                        for msg in msg_list:
                            st.error(f"**{domain}**: {msg}")
                else:
                    st.success("No violations")

            with tab_w:
                warnings = result.get("warnings", {})
                if warnings:
                    for domain, msgs in warnings.items():
                        msg_list = msgs if isinstance(msgs, list) else [msgs]
                        for msg in msg_list:
                            st.warning(f"**{domain}**: {msg}")
                else:
                    st.success("No warnings")

            with tab_a:
                actions = result.get("actions_taken", [])
                if actions:
                    for action in actions:
                        st.markdown(f"- {action}")
                else:
                    st.info("No actions taken")

            with tab_r:
                if decision == "PROCEED":
                    sentiment_data = api_get(f"/sentiment/{scenario['id']}", timeout=90)
                    risks = api_get(f"/risks/{scenario['id']}", timeout=90)
                    suggested = api_get("/suggested-actions", timeout=90)

                    # Sentiment section (available even before provisioning)
                    if sentiment_data and sentiment_data.get("interaction_count", 0) > 0:
                        st.markdown("**Customer Sentiment**")
                        sc1, sc2, sc3, sc4 = st.columns(4)
                        sc1.metric("Score", sentiment_data.get("score", 0.0))
                        sc2.metric("Label", sentiment_data.get("label", "neutral").title())
                        sc3.metric("Trend", sentiment_data.get("trend", "stable").replace("_", " ").title())
                        sc4.metric("Model", "DistilBERT" if "distilbert" in sentiment_data.get("model", "") else "Keyword")
                        if sentiment_data.get("summary"):
                            st.caption(sentiment_data["summary"])
                        st.divider()

                    # Post-provisioning risks (only when account is provisioned)
                    if risks and risks.get("status") == "NOT_PROVISIONED":
                        st.info("Post-provisioning risk monitoring will be available once the account is provisioned")
                    elif risks and risks.get("risk_count", 0) > 0:
                        st.markdown("**Detected Risks:**")
                        for risk in risks["risks"]:
                            sev = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                                risk.get("severity", ""), "⚪"
                            )
                            st.markdown(
                                f"- {sev} **{risk['risk']}**: {risk['detail']}  \n"
                                f"  Recommended: {risk['recommendation']}"
                            )
                    else:
                        st.success("No live post-provisioning risks detected")

                    if suggested and suggested.get("actions"):
                        account_actions = [
                            action for action in suggested["actions"]
                            if action.get("account_id") == scenario["id"]
                        ]
                        if account_actions:
                            st.markdown("**Suggested Actions:**")
                            for action in account_actions:
                                st.markdown(
                                    f"- {action.get('icon', '📋')} **{action['description']}**"
                                )
                                for sub in action.get("sub_actions", []):
                                    st.caption(
                                        f"{sub.get('action_type', 'action')}: {sub.get('description', '')}"
                                    )
                else:
                    st.info("Risk monitoring is only available after provisioning")

            with tab_p:
                if decision == "PROCEED":
                    # Fetch live provisioning progress (simulation may have updated state)
                    progress = api_get(f"/progress/{scenario['id']}", timeout=90)
                    if progress and progress.get("status") not in ("error", "NOT_PROVISIONED"):
                        live_risks = api_get(f"/risks/{scenario['id']}", timeout=90)
                        pc1, pc2, pc3 = st.columns(3)
                        pc1.metric("Completion", f"{progress.get('completion_percentage', 0)}%")
                        pc2.metric("Health", progress.get("health_status", "N/A").replace("_", " ").title())
                        pc3.metric("Day", progress.get("days_since_provisioning", 0))

                        sentiment = progress.get("sentiment", {})
                        if sentiment:
                            st.caption(
                                f"Sentiment: {sentiment.get('label', 'neutral').title()} "
                                f"({sentiment.get('score', 0.0)}), trend: "
                                f"{str(sentiment.get('trend', 'stable')).replace('_', ' ').title()}"
                            )

                        if live_risks and live_risks.get("risk_count", 0) > 0:
                            st.markdown("**Current Risks:**")
                            for risk in live_risks["risks"]:
                                sev = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                                    risk.get("severity", ""), "⚪"
                                )
                                st.markdown(
                                    f"- {sev} **{risk['risk']}**: {risk['detail']}"
                                )
                        else:
                            st.success("No current post-provisioning risks detected")

                        tb = progress.get("task_breakdown", {})
                        tc1, tc2, tc3, tc4 = st.columns(4)
                        tc1.metric("Completed", tb.get("completed", 0))
                        tc2.metric("In Progress", tb.get("in_progress", 0))
                        tc3.metric("Pending", tb.get("pending", 0))
                        tc4.metric("Blocked", tb.get("blocked", 0))

                        if progress.get("overdue_tasks"):
                            st.markdown("**Overdue Tasks:**")
                            for t in progress["overdue_tasks"]:
                                st.warning(f"`{t['task_id']}` {t['name']} — owner: {t['owner']}, due: {t.get('due_date', 'N/A')}")

                        if progress.get("next_actions"):
                            st.markdown("**Next Actions:**")
                            for a in progress["next_actions"]:
                                st.markdown(f"- `{a['task_id']}` {a['name']} (owner: {a['owner']})")
                    else:
                        prov = result.get("provisioning")
                        if prov:
                            st.json(prov)
                        else:
                            st.info("Provisioning completed — details not available")
                else:
                    st.info("Not provisioned — decision was " + decision)

            # Raw result
            with st.expander("Raw API Response"):
                st.json(result)

    # Run All button
    st.markdown("---")
    if st.button("Run All Scenarios"):
        with st.spinner("Running all 10 scenarios (this may take a few minutes)..."):
            result = api_post("/run-all", timeout=600)

        if result:
            summary = result.get("summary", {})
            st.markdown(
                f"### Results: {summary.get('passed', 0)}/{summary.get('total_scenarios', 0)} passed "
                f"({summary.get('success_rate', 'N/A')})"
            )

            for r in result.get("results", []):
                icon = "✅" if r["passed"] else "❌"
                st.markdown(
                    f"{icon} **{r['account_id']}** ({r['scenario_name']}) — "
                    f"Expected: `{r['expected_decision']}`, "
                    f"Got: `{r['actual_decision']}`"
                )


# ============================================================================
# PAGE 4: CHAT WITH AGENT
# ============================================================================

elif page == "Chat with Agent":
    st.title("CS Assistant Chat")
    st.caption("Ask about onboarding status, risks, or request actions.")

    # Account context — dropdown from known scenarios
    _scenario_ids = [
        "ACME-001", "BETA-002", "GAMMA-003", "DELETED-004", "MISSING-999",
        "FOREX-005", "PARTIAL-006", "STARTER-007", "GROWTH-008", "ENTERPRISE-009",
    ]
    account_id = st.sidebar.selectbox("Account Context", _scenario_ids, index=0)

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ---- Handle pending prompt from quick action buttons ----
    def _send_prompt(prompt: str):
        """Send a prompt to the agent and store the response."""
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                result = api_post(
                    "/chat",
                    json={
                        "message": prompt,
                        "account_id": account_id,
                        "session_id": st.session_state.chat_session_id,
                    },
                )

            if result and "response" in result:
                response = result["response"]
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            elif result and "error" in result:
                st.error(f"Error: {result['error']}")
            else:
                st.error("No response from agent. Is the API running?")

    # Process pending prompt from quick action buttons
    if st.session_state.pending_prompt is not None:
        prompt = st.session_state.pending_prompt
        st.session_state.pending_prompt = None
        _send_prompt(prompt)

    # Chat input
    if prompt := st.chat_input("Ask the CS assistant..."):
        _send_prompt(prompt)

    # Quick action buttons
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Quick Actions**")
    if st.sidebar.button("Check Progress"):
        st.session_state.pending_prompt = f"What's the onboarding progress for {account_id}?"
        st.rerun()
    if st.sidebar.button("Identify Risks"):
        st.session_state.pending_prompt = f"Are there any risks with {account_id}'s onboarding?"
        st.rerun()
    if st.sidebar.button("Discuss Decision"):
        # Fetch the run result for this account and build a contextual prompt
        run_data = api_get("/active-onboardings")
        account_run = None
        if run_data and run_data.get("onboardings"):
            account_run = next(
                (o for o in run_data["onboardings"] if o["account_id"] == account_id),
                None,
            )
        if account_run:
            decision = account_run.get("decision", "UNKNOWN")
            issues = []
            for domain, msgs in account_run.get("violations", {}).items():
                for msg in msgs:
                    issues.append(f"- [Violation] {domain}: {msg}")
            for domain, msgs in account_run.get("warnings", {}).items():
                for msg in msgs:
                    issues.append(f"- [Warning] {domain}: {msg}")
            summary = account_run.get("summary", "")

            if issues:
                issue_text = "\n".join(issues)
                st.session_state.pending_prompt = (
                    f"The onboarding for {account_id} was decided as {decision}. "
                    f"Here are the issues found:\n{issue_text}\n\n"
                    f"For each issue, explain why it matters, what the root cause likely is, "
                    f"who should fix it, and what specific steps they should take to resolve it "
                    f"so the onboarding can proceed."
                )
            else:
                st.session_state.pending_prompt = (
                    f"The onboarding for {account_id} was decided as {decision}. "
                    f"Summary: {summary}. "
                    f"Explain what this decision means and what the next steps are."
                )
            st.rerun()
        else:
            st.sidebar.warning(f"No run result for {account_id}. Run the scenario first.")
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Portfolio Actions**")
    if st.sidebar.button("Portfolio Summary"):
        st.session_state.pending_prompt = "Give me a daily summary of all my accounts."
        st.rerun()
    if st.sidebar.button("All Alerts"):
        st.session_state.pending_prompt = "What are all the current alerts across my portfolio?"
        st.rerun()
    if st.sidebar.button("Send All Reminders"):
        st.session_state.pending_prompt = "Send reminders to all customers with overdue tasks."
        st.rerun()
    st.sidebar.markdown("---")
    if st.sidebar.button("Clear Chat"):
        st.session_state.messages = []
        st.session_state.pending_prompt = None
        api_post(f"/chat/reset?session_id={st.session_state.chat_session_id}")
        st.session_state.chat_session_id = str(uuid.uuid4())[:8]
        st.rerun()
