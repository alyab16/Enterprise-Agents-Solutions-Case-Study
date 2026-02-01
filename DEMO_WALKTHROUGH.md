# Demo Walkthrough - Enterprise Onboarding Agent

## Overview (30 seconds)
This agent automates Customer Success onboarding from **Sales → Contract → Invoice → Provisioning**, integrating with Salesforce (CRM), CLM, NetSuite (ERP), and a SaaS provisioning system.

---

## End-to-End Demo Flow (3 minutes)

### Step 1: Trigger Onboarding (Webhook)
```bash
# Simulates Salesforce firing a webhook when Opportunity = "Closed Won"
curl -X POST http://localhost:8000/webhook/onboarding \
  -H "Content-Type: application/json" \
  -d '{"account_id": "ACME-001", "event": "opportunity.closed_won"}'
```

**What happens:**
- Agent initializes with correlation ID for tracing
- Fetches Account, User, Opportunity from Salesforce
- Fetches Contract status from CLM
- Fetches Invoice status from NetSuite

### Step 2: Risk Analysis (LLM-Powered)
The agent analyzes the collected data:
- Checks business rules (invariants) for violations/warnings
- Calls OpenAI GPT-4 to generate human-readable risk assessment
- Falls back to rule-based analysis if LLM unavailable

**Example LLM Output:**
```json
{
  "summary": "ACME Corp onboarding is ready to proceed. All checks passed.",
  "risk_level": "low",
  "recommended_actions": [
    {"action": "Proceed with provisioning", "owner": "System", "priority": 1}
  ]
}
```

### Step 3: Decision & Action
Based on analysis, agent decides:
- **PROCEED** → Auto-provisions tenant, sends welcome email
- **ESCALATE** → Notifies CS team via Slack for review
- **BLOCK** → Alerts CS team of critical issues

**For ACME-001 (Happy Path):**
```
Decision: ✅ PROCEED
Actions: 
  - Provisioned tenant TEN-E2B91C6D (Enterprise tier)
  - Sent Slack notification to #cs-onboarding
  - Sent welcome email to customer
```

### Step 4: View Results
```bash
# Check generated reports
curl http://localhost:8000/demo/reports

# View detailed run report
open reports_output/run_report_ACME-001_*.html
```

---

## Demonstrating Key Capabilities (2 minutes)

### A. Handling Blocked Scenarios
```bash
curl -X POST http://localhost:8000/demo/run/BETA-002?generate_report=true
```
**Result:** BLOCK - Opportunity not in "Closed Won" stage
- Agent identifies the risk before wasting CS time
- Sends alert to #cs-onboarding-alerts channel

### B. Escalation with Warnings
```bash
curl -X POST http://localhost:8000/demo/run/GAMMA-003?generate_report=true
```
**Result:** ESCALATE - Invoice is overdue
- Agent doesn't block, but flags for human review
- Notifies Finance team about payment issue

### C. API Error Resilience
```bash
# Enable 100% auth failure rate
curl -X POST "http://localhost:8000/demo/enable-random-errors?auth_rate=1.0"

# Run scenario - should BLOCK due to API errors
curl -X POST http://localhost:8000/demo/run/ACME-001
```
**Result:** BLOCK - Salesforce authentication failed
- Agent gracefully handles API failures
- Records error details for debugging
- Doesn't proceed with incomplete data

### D. Full Batch Run
```bash
curl -X POST http://localhost:8000/demo/run-all?generate_reports=true
```
Runs all scenarios, generates reports only for real accounts.

---

## Production Extension Notes

### What Would Change for Production:

1. **Real OAuth Integration**
   - Replace mock credentials with Salesforce Connected App
   - Implement token refresh flows
   - Store credentials in HashiCorp Vault

2. **Message Queue**
   - Replace sync processing with SQS/RabbitMQ
   - Enable horizontal scaling with Kubernetes

3. **Human-in-the-Loop**
   - Add Slack interactive buttons for ESCALATE approval
   - Implement approval workflow before provisioning high-value accounts

4. **Monitoring**
   - Add Prometheus metrics (latency, error rates)
   - DataDog/Jaeger distributed tracing
   - PagerDuty alerts for critical failures

5. **Multi-Agent Collaboration (MCP)**
   - Deploy specialized agents (Contract Agent, Finance Agent)
   - Connect via MCP servers for tool sharing
   - Enable cross-agent context passing

---

## Key Files to Review

| File | Purpose |
|------|---------|
| `app/agent/graph.py` | LangGraph workflow definition |
| `app/agent/nodes.py` | Individual processing steps |
| `app/llm/risk_analyzer.py` | LLM integration with fallback |
| `app/integrations/api_errors.py` | Error simulation & handling |
| `app/api/demo.py` | REST endpoints for demo |
| `docs/SOLUTION_DESIGN.md` | Full architecture documentation |

---

## Running the Demo

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment (optional - works without for demo)
export OPENAI_API_KEY=sk-...

# Start server
uvicorn main:app --reload

# Open docs
open http://localhost:8000/docs
```

---

*Total demo time: ~5 minutes*
