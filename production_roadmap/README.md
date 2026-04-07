# Production Roadmap

The following enhancements would evolve the onboarding agent from a prototype into a production-grade system. Each section addresses a specific dimension of complexity that enterprise deployments require. This list is not exhaustive, real-world deployments would surface additional scenarios across compliance, data migration, internationalization, multi-tenant isolation, and other domains specific to the business.
---

## Workflow & Notifications

1. **~~Task Monitor Agent~~** ✅ **PARTIALLY IMPLEMENTED**: The `identify_onboarding_risks` tool detects overdue tasks, customer inactivity (no login after 3 days), SSO not configured after kickoff, blocked tasks, stalling onboardings (<30% after 7 days), and customer sentiment decline. The `send_task_reminder` tool sends reminders to task owners. The `check_onboarding_progress` tool provides a dashboard view with health status (on_track/at_risk/stalled). The CS assistant agent can be asked to check progress, identify risks, inspect sentiment, and take corrective action conversationally. See `app/integrations/provisioning.py`, `app/integrations/sentiment.py`, and `app/agent/onboarding_agent.py`. **Remaining enhancement**: Scheduled cron job for hourly automated checks without CS prompting.

2. **~~Escalation Hierarchy~~** ✅ **PARTIALLY IMPLEMENTED**: The `escalate_stalled_onboarding` tool posts to `#cs-onboarding-escalations` with a progress snapshot (completion %, days since provisioning, overdue/blocked counts). The CS assistant can trigger escalation conversationally, and the suggested-actions flow can now resolve blocked/escalated accounts and re-run onboarding into provisioning. See `app/integrations/provisioning.py`, `app/integrations/resolution.py`, and `app/api/demo.py`. **Remaining enhancement**: Time-based automatic escalation (Day 2 → CS Manager, Day 4 → CS Director) without manual trigger.
   ```
   Day 0: ESCALATE → Notify CS Team (#cs-onboarding)
   Day 2: No action → Notify CS Manager (@cs-manager)  ← not yet automated
   Day 4: Still unresolved → Notify CS Director (@cs-director)  ← not yet automated
   ```

3. **Approval Workflow**: For ESCALATE decisions, send Slack message with interactive buttons. The current prototype already supports approve/dismiss in Streamlit and executes real backend actions (reminders, escalations, remediation + re-run). A production workflow would externalize those approvals into Slack/Teams with identity, audit, and policy controls:
   ```
   ⚠️ ACME Corp needs review - Invoice overdue
   [Approve Provisioning] [Reject] [View Details]
   ```

---

## Event-Driven Integration

4. **Event-Driven Task Completion**: Webhooks from the SaaS platform to automatically mark tasks complete:
   ```
   Customer logs in → Mark "Verify Login Access" complete
   Customer completes tour → Mark "Complete Platform Tour" complete
   ```

5. **Optimized Data Fetching**: Batch API requests (Salesforce Composite API) and concurrent multithreaded calls with bounded retry logic to reduce latency.

---

## Salesforce & CRM Scenarios

6. **Account Hierarchy & Subsidiary Onboarding**: Salesforce [Accounts](https://developer.salesforce.com/docs/atlas.en-us.object_reference.meta/object_reference/sforce_api_objects_account.htm) support parent-child relationships via the `ParentId` field. Enterprise customers often have a parent account with multiple subsidiaries, each requiring their own tenant. The agent would detect child accounts under a parent, validate whether the contract covers subsidiaries, and either onboard them under a single master agreement or flag that separate contracts are needed per entity.

7. **Multi-Opportunity Handling**: A single Account can have multiple Closed Won [Opportunities](https://developer.salesforce.com/docs/atlas.en-us.object_reference.meta/object_reference/sforce_api_objects_opportunity.htm) representing upsells, renewals, or separate product lines. Rather than assuming one Opportunity per Account, the agent would fetch all Closed Won Opportunities, validate that each has a linked `ContractId`, and determine which Opportunity is driving the current onboarding, prioritizing by `CloseDate` or `Amount`, and warning CS if multiple Opportunities lack contract linkage.

8. **~~Opportunity Currency Mismatch Detection~~** ✅ **IMPLEMENTED**: The `check_financial_alignment` tool compares the Opportunity Amount against the Invoice total, converting currencies via live exchange rates (ExchangeRate API) when they differ. Gaps exceeding a 2% threshold trigger an ESCALATE warning. Demonstrated by the FOREX-005 scenario (CAD invoice vs USD opportunity). See `app/agent/onboarding_agent.py` (`check_financial_alignment` tool) and `app/integrations/currency.py`.

9. **Account Owner Validation & Reassignment Detection**: The agent currently validates the Account Owner (`OwnerId`) via the [User](https://developer.salesforce.com/docs/atlas.en-us.object_reference.meta/object_reference/sforce_api_objects_user.htm) object. In production, additional checks would include: whether the owner's `LastLoginDate` is recent (an owner who hasn't logged in for 90 days may have left the company), whether the owner's `ManagerId` is populated (for escalation routing), and whether the owner was recently reassigned (comparing `OwnerId` against `LastModifiedDate` on the Account) which could indicate a handoff that CS should be aware of.

10. **Stale Opportunity Detection**: Using the Opportunity's `AgeInDays` field and `LastActivityDate`, the agent would flag opportunities that closed a long time ago but were never onboarded - e.g., "This Opportunity closed 120 days ago with no provisioning activity." This catches deals that fell through the cracks, where the customer may have already churned or lost interest, and CS should confirm the customer still intends to proceed before provisioning.

---

## Invoice & Financial Scenarios

11. **~~Multi-Currency Invoice Handling~~** ✅ **IMPLEMENTED**: The agent now supports live currency conversion via the `convert_currency` tool (ExchangeRate API, no API key required). The `check_financial_alignment` tool automatically converts invoice totals to the opportunity's currency when they differ and flags discrepancies beyond 2%. The FOREX-005 scenario demonstrates a CAD $145,000 invoice against a USD $100,000 opportunity. See `app/integrations/currency.py` and `app/mcp/currency_server.py`. **Remaining enhancement**: Compare against the historical exchange rate on the invoice date to detect FX exposure drift, and support batch conversion for multi-invoice accounts.

12. **Payment Terms & Installment Validation**: NetSuite supports flexible payment [Terms](https://system.netsuite.com/help/helpcenter/en_US/APIs/REST_API_Browser/record/v1/2023.1/index.html#/definitions/term) (Net 30, Net 60, date-driven, early payment discounts) and [installment-based](https://system.netsuite.com/help/helpcenter/en_US/APIs/REST_API_Browser/record/v1/2023.1/index.html#/definitions/invoice-installmentElement) billing where the total is split across multiple scheduled payments. The agent would validate the term structure (`daysUntilNetDue`, `recurrenceCount`, `splitEvenly`) and check each installment element (`amount`, `amountDue`, `dueDate`) individually rather than treating the invoice as a single payment. This enables more nuanced decisions. For example, an ESCALATE if only the first installment is overdue versus a BLOCK if multiple installments are missed.

13. **Early Payment Discount Detection**: NetSuite Terms support early payment discounts (`discountPercent`, `daysUntilExpiry`). If the customer's invoice is within the discount window, the agent would add a note to the CS team's report highlighting the opportunity (e.g., "Customer is eligible for a 2% discount if payment is received within 5 days. Consider mentioning during kickoff call.") This turns the agent into a revenue-aware assistant, not just a blocker/escalator/approver.

14. **Credit Memo & Partial Payment Reconciliation**: In production, invoices rarely exist in isolation. A customer may have partial payments applied, outstanding credit memos from a previous billing dispute, or unapplied deposits. The agent would reconcile the invoice's `amountRemaining` against any linked credit memos and deposits to calculate the true outstanding balance. This prevents false escalations. For example, an invoice showing $25,000 outstanding shouldn't trigger an overdue warning if a $20,000 credit memo is pending application by the Finance team.

15. **Multi-Invoice Account Validation**: Enterprise customers often have multiple invoices at different stages, one paid, one current, one overdue from a previous contract period. Rather than checking a single invoice, the agent would fetch all open invoices for the account and apply tiered logic:
    ```
    All invoices paid         → PROCEED (no financial risk)
    Current invoices only     → PROCEED with note to CS
    One overdue < 30 days     → ESCALATE (warning to CS, recommend follow-up)
    One overdue > 30 days     → ESCALATE (urgent, notify Finance)
    Multiple overdue invoices → BLOCK (systemic payment issue, require Finance approval)
    Total overdue > contract value → BLOCK (high exposure, escalate to Finance Director)
    ```

16. **~~Revenue Recognition & Contract Value Alignment~~** ✅ **PARTIALLY IMPLEMENTED**: The `check_financial_alignment` tool cross-validates the invoice total against the Salesforce Opportunity `Amount` (with currency conversion when needed) and flags gaps exceeding a 2% threshold. The PARTIAL-006 scenario demonstrates underpayment detection ($190k paid of $200k total). See `app/agent/onboarding_agent.py` (`check_financial_alignment` tool). **Remaining enhancement**: Also compare against the CLM contract value, and differentiate between overbilling (ESCALATE to Finance + Account Owner) vs underbilling (warning to Revenue Operations).

---

## Frontend & Observability

17. **Real-Time Dashboard**: A Streamlit prototype (`streamlit_app.py`) demonstrates the UI concept with four pages: **Dashboard** — proactive alerts grouped by account, smart suggested actions with approve/dismiss buttons, and all onboarding results grouped by decision with health badges and expandable details; **Portfolio Overview** — aggregated health metrics (On Track/At Risk/Stalled/Blocked/Escalated), priority actions today, and sortable account table; **Run Onboarding** — scenario selector with tabbed results (including live provisioning progress) and batch run-all mode; **Chat with Agent** — interactive conversational interface with account dropdown, portfolio-level quick actions (Portfolio Summary, All Alerts, Send All Reminders), and per-account actions. Suggested actions now perform real state transitions: reminders change task state, escalations unblock blocked tasks, and blocked/escalated onboarding runs can be remediated and re-run. See `streamlit_app.py` and the `/demo/alerts`, `/demo/portfolio-summary`, `/demo/suggested-actions`, `/demo/execute-action`, `/demo/chat`, `/demo/active-onboardings` endpoints. **Production enhancement**: Migrate to a production-grade frontend framework (e.g., React, Next.js, or ASP.NET) for scalability, authentication, role-based access, and real-time WebSocket updates. Streamlit is effective for prototyping but not suited for multi-user production deployments.

---

## LLM Resilience & Multi-Model Fallback

18. **Multi-Model Fallback Chain**: The agent currently supports OpenAI GPT-4o (when `OPENAI_API_KEY` is set) with automatic fallback to Ollama local models (Llama 3.2). In production, a secondary cloud LLM provider (e.g., Claude via AWS Bedrock, or Gemini) would be inserted between them, creating a three-tier chain: **OpenAI → Secondary Cloud LLM → Ollama local**. Pydantic AI's model abstraction makes this straightforward — the `_select_model()` function in `app/agent/onboarding_agent.py` already handles provider selection. AWS Bedrock is particularly well-suited as a secondary provider since it offers multi-model access (Claude, Llama, Titan) within a single VPC with IAM-based authentication.

19. **Unified LLM Gateway via LiteLLM**: Rather than coding provider-specific API calls, a library like [LiteLLM](https://github.com/BerriAI/litellm) would provide a single interface across all LLM providers. Switching from OpenAI to Claude or Gemini becomes a configuration change, not a code change. LiteLLM also enables provider-level rate limit tracking, cost monitoring per model, automatic retries with fallback ordering, and consistent logging across providers - all of which simplify operations when running multiple models in production.

---

## RAG & Context Engineering

20. **RAG-Enriched Risk Analysis**: Add a retrieval-augmented generation pipeline at the risk analysis step, enriching the LLM prompt with context it couldn't otherwise know. The agent would query a vector store (e.g., PG Vector) before generating its assessment, retrieving relevant documents to ground the LLM's recommendations in real data rather than generic advice. Three data sources would be embedded:
    - **Past onboarding run summaries**: Final reports from completed runs, including what went wrong, the decision outcome, and how it was resolved. When a new onboarding starts, query by similarity to the current account profile (industry, deal size, contract type, region). The LLM then sees: "Here are 3 similar past onboardings - two had overdue invoices that resolved within a week, one escalated to finance and took 3 weeks."
    - **CS playbooks and knowledge base articles**: Internal how-to guides for handling specific scenarios like "customer in regulated industry needs DPA signed before provisioning" or "accounts under $10K use self-serve onboarding." Embedding these (typically from Confluence or Notion) lets the LLM reference actual company procedures.
    - **Customer communication history**: Recent Salesforce activity records or email logs. If the CS team has already been discussing the overdue invoice with the customer and a payment plan is in progress, the LLM should know that before recommending "escalate to finance immediately."

    The decisions themselves (PROCEED/ESCALATE/BLOCK) stay deterministic and rule-based - RAG doesn't change that. What changes is the quality of the LLM's recommendations and summaries. Instead of "Invoice is overdue, escalate to Finance," the agent could say "Invoice is overdue, but similar accounts in this industry typically resolve within 5 business days. The CS team last contacted the customer 2 days ago. Recommended action: follow up in 3 days before escalating to Finance."

21. **Historical Risk Scoring**: Using stored onboarding outcomes, build a lightweight predictive model (logistic regression or gradient boosted trees) trained on historical features (industry, deal size, contract type, days from close to contract execution) to score new accounts before the LLM analysis. The predictive score is injected into the LLM prompt as additional context (e.g., "Predictive model estimates 73% probability of escalation for this account based on historical patterns"), giving the LLM both the current state and a data-driven prior to reason from.

---

## Multi-Agent Architecture

22. **MCP and A2A Protocol Integration** ✅ **PARTIALLY IMPLEMENTED**: Each integration is now defined as a [FastMCP](https://github.com/jlowin/fastmcp) server in `app/mcp/` (Salesforce, CLM, NetSuite, Currency, Provisioning, Notifications, Validation, Sentiment — 8 servers total). These currently run in-process as tool definitions mirroring the agent's 26 `@agent.tool` decorators, but are structured for extraction to standalone MCP services. The Provisioning MCP server includes portfolio-level tools (`get_all_alerts`, `get_portfolio_summary`, `get_all_suggested_actions`). **Remaining enhancement**: Deploy as independent HTTP services, add the [A2A](https://a2a-protocol.org/) protocol for agent-to-agent collaboration (e.g., a Finance Agent that proactively flags credit risk, a Compliance Agent that validates data residency requirements before tenant provisioning).

23. **MCP Credential Management & Trust Boundaries**: Each MCP server manages its own credentials for its target system. The Salesforce MCP server holds Salesforce OAuth tokens, the NetSuite MCP server holds NetSuite Token-Based Authentication (TBA) credentials, and so on. The onboarding agent never sees or touches external system credentials, establishing two separate trust boundaries: agent-to-MCP and MCP-to-external API. Key production concerns include:
    - **Agent-to-MCP authentication**: Short-lived tokens issued by an internal identity provider, mutual TLS, or API keys rotated through a secrets manager. Accessing the Salesforce MCP server doesn't give you Salesforce credentials, it only gives you access to a controlled, audited interface.
    - **External credential management**: Each MCP server handles its own token lifecycle (refresh flows, expiry detection, retry on 401). Credentials are stored in AWS Secrets Manager or HashiCorp Vault, never in environment variables or config files.
    - **Permission scoping**: Per-consumer access control on each MCP server. The onboarding agent might only need read access to Salesforce Account and Opportunity, while a different agent might need write access. This prevents accidental or unauthorized data modification.
    - **Audit trail**: Every call through an MCP server is logged with the caller identity, operation requested, and correlation ID, providing end-to-end visibility into which agent accessed which system, when, and why.
