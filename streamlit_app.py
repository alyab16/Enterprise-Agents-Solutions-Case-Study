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

def api_get(path: str):
    """GET request to the FastAPI backend."""
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=30)
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


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------

page = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Run Onboarding", "Chat with Agent"],
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
            st.rerun()

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
                        pc1, pc2, pc3 = st.columns(3)
                        pc1.metric("Completion", f"{o['completion_percentage']}%")
                        pc2.metric("Overdue Tasks", o["overdue_count"])
                        pc3.metric("Blocked Tasks", o["blocked_count"])

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
                                for msg in msgs:
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
                                for msg in msgs:
                                    st.warning(f"**{domain}**: {msg}")
                        st.markdown(f"Warning count: {o.get('warning_count', 0)}")

    else:
        st.info(
            "No onboarding results yet. Use the **Run Onboarding** page to "
            "process a scenario, then return here to see the dashboard."
        )


# ============================================================================
# PAGE 2: RUN ONBOARDING
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

            # Violations & Warnings
            tab_v, tab_w, tab_a, tab_p = st.tabs(
                ["Violations", "Warnings", "Actions", "Provisioning"]
            )

            with tab_v:
                violations = result.get("violations", {})
                if violations:
                    for domain, msgs in violations.items():
                        for msg in msgs:
                            st.error(f"**{domain}**: {msg}")
                else:
                    st.success("No violations")

            with tab_w:
                warnings = result.get("warnings", {})
                if warnings:
                    for domain, msgs in warnings.items():
                        for msg in msgs:
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

            with tab_p:
                prov = result.get("provisioning")
                if prov:
                    st.json(prov)
                else:
                    st.info("Not provisioned")

            # Raw result
            with st.expander("Raw API Response"):
                st.json(result)

    # Run All button
    st.markdown("---")
    if st.button("Run All Scenarios"):
        with st.spinner("Running all 7 scenarios (this may take a few minutes)..."):
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
# PAGE 3: CHAT WITH AGENT
# ============================================================================

elif page == "Chat with Agent":
    st.title("CS Assistant Chat")
    st.caption("Ask about onboarding status, risks, or request actions.")

    # Account context
    account_id = st.sidebar.text_input("Account Context", value="ACME-001")

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
    if st.sidebar.button("Clear Chat"):
        st.session_state.messages = []
        st.session_state.pending_prompt = None
        api_post(f"/chat/reset?session_id={st.session_state.chat_session_id}")
        st.session_state.chat_session_id = str(uuid.uuid4())[:8]
        st.rerun()
