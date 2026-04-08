%%{
  init: {
    "theme": "base",
    "themeVariables": {
      "background": "#ffffff",
      "primaryColor": "#e8f0ff",
      "primaryBorderColor": "#5b8def",
      "lineColor": "#6b7a90",
      "primaryTextColor": "#1f2937",
      "fontSize": "13px"
    }
  }
}%%

flowchart LR

%% ============ INGESTION ============
START(("🔵 Start"))
WEBHOOK["Webhook /<br/>API Trigger"]
INIT["Initialize<br/>OnboardingDeps<br/>(account_id,<br/>correlation_id)"]

%% ============ AGENT RUNS ============
AGENT_START["Agent.run()<br/>Pydantic AI"]

%% ============ FETCH PHASE ============
subgraph FETCH["1. Gather Data"]
  direction TB
  FA["fetch_salesforce_account"]
  FA -->|"OwnerId"| FU["fetch_salesforce_user"]
  FA -->|"parallel"| FO["fetch_salesforce_opportunity"]
  FA -->|"parallel"| FC["fetch_salesforce_contract"]
  FA -->|"parallel"| FCLM["fetch_clm_contract"]
  FA -->|"parallel"| FI["fetch_netsuite_invoice"]
end

%% ============ VALIDATE PHASE ============
subgraph VAL["2. Validate"]
  direction TB
  VB["validate_business_rules<br/>(5 domains, no args)"]
  VF["check_financial_alignment<br/>(cross-currency, 2% threshold)"]
  VB --> VF
  VF -.->|"if currencies differ"| CC["convert_currency<br/>(historical rate<br/>from invoice date)"]
end

%% ============ DECIDE ============
DECIDE{"LLM Decides<br/>PROCEED /<br/>ESCALATE /<br/>BLOCK"}

%% ============ PROCEED PATH ============
subgraph ACT_PROCEED["3a. PROCEED Actions"]
  direction TB
  PROV["provision_account<br/>(tier from CLM)"]
  NS["notify_success"]
  SE["send_email<br/>(CS manager)"]
  CW["send_customer_welcome"]
  PROV --> NS --> SE --> CW
end

%% ============ ASSESS RISKS & SENTIMENT (MANDATORY FOR PROCEED) ============
subgraph ASSESS["5. Assess Risks & Sentiment (mandatory)"]
  direction TB
  CHK["check_onboarding_progress<br/>(health status)"]
  RISK["identify_onboarding_risks<br/>(overdue/blocked/stalled)"]
  SENT["get_customer_sentiment<br/>(score, label, trend)"]
  CHK --> RISK
  RISK --> SENT
end

%% ============ POST-PROVISIONING ACTIONS ============
subgraph MONITOR["6. Post-Provisioning Actions"]
  direction TB
  REM["send_task_reminder<br/>(to task owner)"]
  ESC["escalate_stalled_onboarding<br/>(#cs-escalations)"]
end

%% ============ PORTFOLIO ============
subgraph PORT["5. Portfolio Management"]
  direction TB
  POV["get_portfolio_overview<br/>(all accounts)"]
  PAL["get_all_alerts<br/>(aggregated risks)"]
  PBR["batch_send_reminders<br/>(by filter)"]
end

%% ============ ESCALATE PATH ============
subgraph ACT_ESCALATE["3b. ESCALATE Actions"]
  direction TB
  NE["notify_escalation<br/>(#cs-onboarding)"]
end

%% ============ BLOCK PATH ============
subgraph ACT_BLOCK["3c. BLOCK Actions"]
  direction TB
  NB["notify_blocked<br/>(#cs-onboarding-alerts)"]
  NF["notify_finance_overdue<br/>(if invoice overdue)"]
  NB --> NF
end

%% ============ OUTPUT ============
RESULT["OnboardingResult<br/>(structured output)"]
REPORT["Generate Reports<br/>MD + HTML + JSON"]
DONE(("🟢 Done"))

%% ============ FLOWS ============
START --> WEBHOOK --> INIT --> AGENT_START
AGENT_START --> FETCH
FETCH --> VAL
VAL --> DECIDE

DECIDE -->|"✅ all clear"| ACT_PROCEED
DECIDE -->|"⚠️ warnings only"| ACT_ESCALATE
DECIDE -->|"🚫 errors or<br/>violations"| ACT_BLOCK

ACT_PROCEED --> ASSESS
ASSESS -->|"risks found"| MONITOR
ASSESS --> RESULT
MONITOR --> RESULT
ACT_ESCALATE --> RESULT
ACT_BLOCK --> RESULT

RESULT --> REPORT --> DONE

PORT -. "CS assistant<br/>portfolio queries" .-> RESULT

%% ============ STYLES ============
classDef startEnd fill:#dbeafe,stroke:#3b82f6,stroke-width:2px
classDef trigger fill:#fff3cd,stroke:#d4a017,stroke-width:2px
classDef agent fill:#e8f0ff,stroke:#5b8def,stroke-width:2px
classDef fetch fill:#e6f7ee,stroke:#2e9d69,stroke-width:1px
classDef validate fill:#f1ecff,stroke:#8b7cf6,stroke-width:1px
classDef decision fill:#fff7db,stroke:#d4a017,stroke-width:2px
classDef proceed fill:#e6f7ee,stroke:#2e9d69,stroke-width:1px
classDef escalate fill:#fff3cd,stroke:#d4a017,stroke-width:1px
classDef block fill:#fde8e8,stroke:#e5484d,stroke-width:1px
classDef output fill:#f5f5f5,stroke:#999,stroke-width:1px

class START,DONE startEnd
class WEBHOOK,INIT trigger
class AGENT_START agent
class FA,FU,FO,FC,FCLM,FI fetch
class VB,VF,CC validate
class DECIDE decision
class PROV,NS,SE,CW proceed
class NE escalate
class NB,NF block
class CHK,RISK,SENT,REM,ESC monitor
class POV,PAL,PBR portfolio
class RESULT,REPORT output

classDef monitor fill:#e0f2fe,stroke:#0284c7,stroke-width:1px
classDef portfolio fill:#fce7f3,stroke:#db2777,stroke-width:1px
```
