# Enterprise Onboarding Agent - Presenter Script
## 5-Minute Demo Walkthrough

---

## BEFORE YOU START

**Setup checklist:**
- [ ] Server running: `uvicorn main:app --reload`
- [ ] Browser open to `http://localhost:8000/docs`
- [ ] Terminal visible for logs
- [ ] No `OPENAI_API_KEY` set (to show rule-based fallback) OR key set (to show LLM)
- [ ] Error simulation disabled: `POST /demo/disable-random-errors`

---

## INTRODUCTION (30 seconds)

> "Hi, I'm [Your Name]. Today I'll demonstrate my Enterprise Customer Onboarding Agent - an AI-powered solution that automates the entire customer onboarding workflow from deal closure through SaaS provisioning.
>
> The problem we're solving: When a sales deal closes, Customer Success teams face a manual, error-prone process - checking Salesforce, verifying contracts are signed, confirming invoices are paid, then manually provisioning the customer. This doesn't scale.
>
> My solution automates this entire workflow using a LangGraph-based AI agent. Let me show you how it works."

---

## PART 1: SWAGGER UI OVERVIEW (45 seconds)

*[Show the Swagger UI at /docs - as seen in the screenshot]*

> "Here's our FastAPI backend. Let me walk you through the API structure:
>
> **Webhooks section** - This is the production entry point. When Salesforce detects an Opportunity moved to 'Closed Won', it calls our `/webhook/onboarding` endpoint. The `/debug/onboarding` endpoint lets us test with custom data.
>
> **Demo section** - These are the endpoints we'll use today:
> - `/demo/run/{account_id}` - triggers onboarding for a specific account
> - `/demo/run-all` - batch processes all test scenarios  
> - `/demo/enable-random-errors` and `/demo/disable-random-errors` - lets us simulate API failures for resilience testing
> - `/demo/tasks/{account_id}` - shows the onboarding task checklist
> - `/demo/reports` - lists all generated reports
>
> **Health endpoint** - Standard health check for monitoring.
>
> Behind these endpoints, there's a LangGraph state machine that orchestrates the entire workflow: fetching data from Salesforce, CLM, and NetSuite, validating business rules, analyzing risks with an LLM, making decisions, and taking actions.
>
> Let me show you this in action."

---

## PART 2: HAPPY PATH DEMO (60 seconds)

*[Navigate to POST /webhook/onboarding in Swagger]*

> "Let's trigger an onboarding for ACME Corp - a scenario where everything is in order."

*[Enter this in the request body:]*
```json
{
  "event_type": "opportunity.closed_won",
  "account_id": "ACME-001",
  "correlation_id": "demo-001"
}
```

*[Click Execute]*

> "While this runs, look at the **terminal logs** - you'll see each step:
> - Fetching from Salesforce... 
> - Fetching from CLM... status EXECUTED
> - Fetching from NetSuite... invoice PAID
> - Validation complete... analyzing risks..."

*[Once response appears, scroll through it]*

> "Now let's look at the response. Here's what the agent decided and did:
>
> **Decision: PROCEED** - all checks passed.
>
> **Violations and Warnings** - both empty, meaning no issues found.
>
> **Actions Taken** - look at this: it provisioned a tenant automatically!
> - Tenant ID: TEN-something
> - Tier: Enterprise - it detected this from the opportunity amount
> - 14 onboarding tasks created, 4 already completed by the system
>
> **Notifications Sent** - Slack message and welcome email to #cs-onboarding, welcome email to the customer.
>
> **Provisioning Details** - the full tenant config: max users, features enabled, API rate limits, even an admin URL and API key.
>
> **Generated Reports** - markdown, HTML, and JSON audit files for compliance.
>
> All of this happened automatically in a few seconds. The CS team now has everything they need to start the customer relationship."

*[Show the response]*

> "The response includes:
> - Decision: PROCEED
> - A human-readable summary
> - The provisioned tenant ID
> - The onboarding task checklist
> - Notifications that were sent
>
> All of this happened automatically in about 5 seconds."

---

## PART 3: VIEWING ONBOARDING TASKS (45 seconds)

*[Navigate to GET /demo/tasks/{account_id}]*

> "Now let's look at the onboarding tasks that were created."

*[Enter account_id: ACME-001 and Execute]*

> "The system created 14 tasks organized by category:
>
> **Automated tasks** - already completed by the system: tenant creation, welcome email, Slack notification.
>
> **CS team tasks** - pending actions for Customer Success: schedule kickoff call, configure SSO, create training plan.
>
> **Customer tasks** - what the customer needs to do: verify login, complete the platform tour, attend training.
>
> Each task has dependencies, due dates, and assigned owners. This gives CS teams a clear, actionable checklist."

*[Navigate to GET /demo/tasks/{account_id}/next-actions]*

> "The next-actions endpoint shows CS exactly what they need to do today - perfect for a dashboard."

---

## PART 4: ERROR HANDLING DEMO (60 seconds)

*[Navigate to POST /demo/enable-random-errors]*

> "Now let's see how the agent handles problems. I'll enable error simulation to inject API failures."

*[Set auth_rate to 1.0 and Execute]*

> "I've set a 100% authentication failure rate for Salesforce."

*[Navigate back to POST /webhook/onboarding and run ACME-001 again]*

> "Now when we run the same scenario..."

*[Execute and watch logs]*

> "Watch the logs - Salesforce authentication failed with a 401 error.
>
> The agent:
> - Captures the error with full context
> - Records it as a critical API error
> - Makes the decision: BLOCK
> - Does NOT proceed with incomplete data"

*[Show the response]*

> "Look at the response:
> - Decision: BLOCK
> - API errors section shows exactly what failed
> - Risk level: Critical
> - The summary explains in plain English what went wrong
> - Recommended actions tell the team how to fix it
>
> This is crucial for production - the agent fails safely and provides actionable guidance."

*[Navigate to POST /demo/disable-random-errors and Execute]*

> "Let me disable error simulation for the next demo."

---

## PART 5: ESCALATION SCENARIO (45 seconds)

*[Navigate to POST /demo/run/{account_id}]*

> "Let's look at an escalation scenario - where something needs human review but isn't a blocker."

*[Enter account_id: GAMMA-003 and set generate_report to true]*

*[Execute]*

> "GAMMA-003 has an overdue invoice. Watch what happens..."

*[Show the response]*

> "Decision: ESCALATE - not BLOCK.
>
> The agent found:
> - All critical checks passed - account exists, contract is signed
> - But there's a warning: the invoice is overdue
>
> So instead of blocking, it:
> - Flags the issue for human review
> - Notifies the CS team via Slack
> - Provides context about the payment issue
> - Recommends involving Finance
>
> This balances automation with human judgment for edge cases."

---

## PART 6: REPORTS (30 seconds)

*[Navigate to GET /demo/reports]*

> "Every run generates reports in multiple formats."

*[Execute]*

> "We have:
> - **Markdown reports** - human-readable summaries
> - **HTML reports** - ready to email or display in dashboards  
> - **JSON audit logs** - for compliance and system integration
>
> These provide full traceability of every decision the agent made."

---

## CONCLUSION (30 seconds)

> "To summarize what we've seen:
>
> This AI agent automates enterprise customer onboarding by:
> - Integrating with Salesforce, CLM, and NetSuite
> - Using LLM intelligence with rule-based fallback
> - Making smart decisions: PROCEED, ESCALATE, or BLOCK
> - Handling errors gracefully with actionable guidance
> - Creating structured onboarding task checklists
> - Generating comprehensive reports
>
> For production, I would add: a React dashboard, AWS deployment with Bedrock for the LLM, Docker and Kubernetes for scaling, CI/CD pipelines, and LangSmith for observability.
>
> Thank you! I'm happy to answer any questions or dive deeper into any part of the system."

---

## BACKUP: QUICK COMMANDS

If something goes wrong, here are quick recovery commands:

```bash
# Restart server
uvicorn main:app --reload

# Disable all errors
curl -X POST "http://localhost:8000/demo/disable-random-errors"

# Quick happy path test
curl -X POST "http://localhost:8000/demo/run/ACME-001"

# Check server health
curl http://localhost:8000/
```

---

## TIMING GUIDE

| Section | Duration | Cumulative |
|---------|----------|------------|
| Introduction | 0:30 | 0:30 |
| Architecture | 0:45 | 1:15 |
| Happy Path | 1:00 | 2:15 |
| Tasks | 0:45 | 3:00 |
| Error Handling | 1:00 | 4:00 |
| Escalation | 0:45 | 4:45 |
| Reports | 0:30 | 5:15 |
| Conclusion | 0:30 | 5:45 |

**Total: ~5:45** (buffer for loading times)

---

## KEY POINTS TO EMPHASIZE

1. **LangGraph orchestration** - Modern agent framework, not just scripts
2. **Graceful error handling** - Production systems fail; ours handles it
3. **LLM + Fallback** - Works without API key too
4. **Actionable outputs** - Not just data, but recommendations with owners
5. **14-task checklist** - Thought through the full CS workflow
6. **Three decision types** - PROCEED/ESCALATE/BLOCK shows nuanced logic

---

## QUESTIONS YOU MIGHT GET

**Q: Why LangGraph instead of just functions?**
> "LangGraph gives us state machine semantics, conditional routing, checkpointing, and LangSmith tracing out of the box. It's designed for exactly this kind of multi-step agent workflow."

**Q: How does it handle rate limits?**
> "Each integration has retry logic with exponential backoff. If we hit rate limits, the agent records it as an API error and blocks - we don't want to proceed with potentially stale data."

**Q: What if the LLM hallucinates?**
> "The LLM only generates summaries and recommendations - it doesn't make the actual decision. The decision logic is deterministic: API errors or violations = BLOCK, warnings only = ESCALATE, all clear = PROCEED."

**Q: How would this scale?**
> "For production: message queues for async processing, Redis for distributed state, Kubernetes for horizontal scaling, and LLM response caching to reduce costs."
