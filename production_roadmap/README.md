# Production Roadmap

The following enhancements would evolve the onboarding agent from a prototype into a production-grade system. Each section addresses a specific dimension of complexity that enterprise deployments require. This list is not exhaustive, real-world deployments would surface additional scenarios across compliance, data migration, internationalization, multi-tenant isolation, and other domains specific to the business.
---

## Workflow & Notifications

1. **Task Monitor Agent**: Scheduled job that runs hourly to detect overdue tasks and send proactive Slack reminders to CS team.

2. **Escalation Hierarchy**: If CS team doesn't act on an ESCALATE notification within a threshold (e.g., 48 hours), automatically notify CS Manager. If still unresolved after another threshold, escalate to CS Director.
   ```
   Day 0: ESCALATE → Notify CS Team (#cs-onboarding)
   Day 2: No action → Notify CS Manager (@cs-manager)
   Day 4: Still unresolved → Notify CS Director (@cs-director)
   ```

3. **Approval Workflow**: For ESCALATE decisions, send Slack message with interactive buttons:
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

8. **Opportunity Currency Mismatch Detection**: Salesforce Opportunities support multi-currency via the `CurrencyIsoCode` field. The agent would cross-validate that the Opportunity currency matches the linked NetSuite Invoice currency. A mismatch (e.g., Opportunity in USD but Invoice in CAD) could indicate a billing setup error that should be flagged to Revenue Operations before provisioning.

9. **Account Owner Validation & Reassignment Detection**: The agent currently validates the Account Owner (`OwnerId`) via the [User](https://developer.salesforce.com/docs/atlas.en-us.object_reference.meta/object_reference/sforce_api_objects_user.htm) object. In production, additional checks would include: whether the owner's `LastLoginDate` is recent (an owner who hasn't logged in for 90 days may have left the company), whether the owner's `ManagerId` is populated (for escalation routing), and whether the owner was recently reassigned (comparing `OwnerId` against `LastModifiedDate` on the Account) which could indicate a handoff that CS should be aware of.

10. **Stale Opportunity Detection**: Using the Opportunity's `AgeInDays` field and `LastActivityDate`, the agent would flag opportunities that closed a long time ago but were never onboarded - e.g., "This Opportunity closed 120 days ago with no provisioning activity." This catches deals that fell through the cracks, where the customer may have already churned or lost interest, and CS should confirm the customer still intends to proceed before provisioning.

---

## Invoice & Financial Scenarios

11. **Multi-Currency Invoice Handling**: Support invoices in foreign currencies by validating against NetSuite's [Currency](https://system.netsuite.com/help/helpcenter/en_US/APIs/REST_API_Browser/record/v1/2023.1/index.html#/definitions/currency) and [Invoice](https://system.netsuite.com/help/helpcenter/en_US/APIs/REST_API_Browser/record/v1/2023.1/index.html#/definitions/invoice) objects. The agent would fetch the invoice's currency (`symbol`, `exchangeRate`), convert outstanding amounts to the base currency (CAD) using the exchange rate effective on the invoice date, and flag discrepancies where the rate has shifted significantly since the invoice was issued, thus, alerting Finance to potential forex exposure before provisioning.

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

16. **Revenue Recognition & Contract Value Alignment**: Cross-validate the invoice total against the Salesforce Opportunity `Amount` and the CLM contract value. If the invoice total exceeds the contracted amount, potentially indicating a billing error or unapproved scope change, the agent would ESCALATE to both Finance and the Account Owner. Conversely, if the invoice is significantly below the contract value, it may indicate a missing invoice or phased billing that hasn't been fully set up, warranting a warning to Revenue Operations.

---

## Frontend & Observability

17. **Real-Time Dashboard**: React frontend showing:
     - Active onboardings with status
     - Task checklists with progress bars
     - Overdue alerts and escalation status
     - One-click actions for CS team

---

## LLM Resilience & Multi-Model Fallback

18. **Multi-Model Fallback Chain**: The prototype falls back to rule-based analysis when the OpenAI API is unavailable. In production, a secondary LLM provider (e.g., Claude via AWS Bedrock, or Gemini) would be inserted before the rule-based fallback, creating a three-tier chain: **OpenAI -> Secondary LLM -> Rule-based analysis**. This preserves the quality of LLM-powered risk analysis during provider outages while ensuring the agent never stalls. AWS Bedrock is particularly well-suited here since it offers multi-model access (Claude, Llama, Titan) within a single VPC with IAM-based authentication and no separate API key management.

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

22. **MCP and A2A Protocol Integration**: Each integration (Salesforce, CLM, NetSuite, Tasks) could be wrapped in a dedicated [MCP](https://modelcontextprotocol.io/) server, standardizing how the onboarding agent accesses external tools and data through a single protocol. If those MCP servers evolve into autonomous agents with their own decision-making. For example, a Finance Agent that proactively flags credit risk rather than just fetching invoices, or a Compliance Agent that validates data residency requirements before tenant provisioning. Then Google's [Agent2Agent (A2A)](https://a2a-protocol.org/) protocol could enable peer-to-peer collaboration between them. MCP handles the agent-to-tool layer, while A2A handles the agent-to-agent layer.