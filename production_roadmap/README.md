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

## Event-Driven Integration

4. **Event-Driven Task Completion**: Webhooks from the SaaS platform to automatically mark tasks complete:
   ```
   Customer logs in → Mark "Verify Login Access" complete
   Customer completes tour → Mark "Complete Platform Tour" complete
   ```

5. **Optimized Data Fetching**: Batch API requests (Salesforce Composite API) and concurrent multithreaded calls with bounded retry logic to reduce latency.

## Salesforce & CRM Scenarios

6. **Account Hierarchy & Subsidiary Onboarding**: Salesforce Accounts support parent-child relationships via the [`ParentId`](https://developer.salesforce.com/docs/atlas.en-us.object_reference.meta/object_reference/sforce_api_objects_account.htm) field. Enterprise customers often have a parent account with multiple subsidiaries, each requiring their own tenant. The agent would detect child accounts under a parent, validate whether the contract covers subsidiaries, and either onboard them under a single master agreement or flag that separate contracts are needed per entity.

7. **Multi-Opportunity Handling**: A single Account can have multiple Closed Won [Opportunities](https://developer.salesforce.com/docs/atlas.en-us.object_reference.meta/object_reference/sforce_api_objects_opportunity.htm) representing upsells, renewals, or separate product lines. Rather than assuming one Opportunity per Account, the agent would fetch all Closed Won Opportunities, validate that each has a linked `ContractId`, and determine which Opportunity is driving the current onboarding, prioritizing by `CloseDate` or `Amount`, and warning CS if multiple Opportunities lack contract linkage.

8. **Opportunity Currency Mismatch Detection**: Salesforce Opportunities support multi-currency via the `CurrencyIsoCode` field. The agent would cross-validate that the Opportunity currency matches the linked NetSuite Invoice currency. A mismatch (e.g., Opportunity in USD but Invoice in CAD) could indicate a billing setup error that should be flagged to Revenue Operations before provisioning.

9. **Account Owner Validation & Reassignment Detection**: The agent currently validates the Account Owner (`OwnerId`) via the [User](https://developer.salesforce.com/docs/atlas.en-us.object_reference.meta/object_reference/sforce_api_objects_user.htm) object. In production, additional checks would include: whether the owner's `LastLoginDate` is recent (an owner who hasn't logged in for 90 days may have left the company), whether the owner's `ManagerId` is populated (for escalation routing), and whether the owner was recently reassigned (comparing `OwnerId` against `LastModifiedDate` on the Account) which could indicate a handoff that CS should be aware of.

10. **Stale Opportunity Detection**: Using the Opportunity's `AgeInDays` field and `LastActivityDate`, the agent would flag opportunities that closed a long time ago but were never onboarded - e.g., "This Opportunity closed 120 days ago with no provisioning activity." This catches deals that fell through the cracks, where the customer may have already churned or lost interest, and CS should confirm the customer still intends to proceed before provisioning.

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

## Frontend & Observability

17. **Real-Time Dashboard**: React frontend showing:
     - Active onboardings with status
     - Task checklists with progress bars
     - Overdue alerts and escalation status
     - One-click actions for CS team

## Multi-Agent Architecture

18. **MCP and A2A Protocol Integration**: Each integration (Salesforce, CLM, NetSuite, Tasks) could be wrapped in a dedicated [MCP](https://modelcontextprotocol.io/) server, standardizing how the onboarding agent accesses external tools and data through a single protocol. If those MCP servers evolve into autonomous agents with their own decision-making. For example, a Finance Agent that proactively flags credit risk rather than just fetching invoices, or a Compliance Agent that validates data residency requirements before tenant provisioning. Then Google's [Agent2Agent (A2A)](https://a2a-protocol.org/) protocol could enable peer-to-peer collaboration between them. MCP handles the agent-to-tool layer, while A2A handles the agent-to-agent layer.
