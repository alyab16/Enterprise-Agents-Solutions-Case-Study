---
config:
  theme: base
  themeVariables:
    background: '#ffffff'
    primaryColor: '#e8f0ff'
    primaryBorderColor: '#5b8def'
    lineColor: '#6b7a90'
    primaryTextColor: '#1f2937'
    clusterBkg: '#f7f9fc'
    clusterBorder: '#c7d0e0'
    fontSize: 13px
  flowchart:
    curve: basis
    nodeSpacing: 30
    rankSpacing: 40
---
flowchart LR
 subgraph TRIGGERS["1 · TRIGGER LAYER — How onboarding starts"]
    direction LR
        WH["fa:fa-bolt Salesforce Webhook (real-time)"]
        API["fa:fa-plug REST API / Manual (on-demand)"]
        BATCH["fa:fa-clock Scheduled Batch (nightly / periodic)"]
  end
 subgraph PARALLEL["Parallel fetches after account is loaded"]
    direction LR
        F_USER["fetch_salesforce_user\n(account owner)"]
        F_OPP["fetch_salesforce_opportunity\n(deal details)"]
  end
 subgraph CHAIN["Sequential chain: Sales → Contract → CLM → Invoice"]
    direction LR
        F_CON["fetch_salesforce_contract\n(via ContractId)"]
        F_CLM["fetch_clm_contract\n(via sf_contract_id)"]
        F_INV["fetch_netsuite_invoice\n(via clmContractRef)"]
  end
 subgraph FETCH["Step 1 · GATHER DATA — fetch from source systems"]
    direction TB
        F_ACC["fetch_salesforce_account (primary record)"]
        PARALLEL
        CHAIN
  end
 subgraph VALIDATE["Step 2 · VALIDATE — business rules + financial checks"]
    direction TB
        V_BIZ["validate_business_rules\n(5 domains)"]
        V_FIN["check_financial_alignment\n(cross-system · 2% threshold)"]
        V_CUR["convert_currency\n(historical ECB rate)"]
  end
 subgraph ACT_B["BLOCK path — stop onboarding"]
    direction LR
        N_BLK["notify_blocked (Slack alert)"]
        N_FIN["notify_finance_overdue (finance alert)"]
  end
 subgraph ACT_E["ESCALATE path — flag for review"]
        N_ESC["notify_escalation (CS team review)"]
  end
 subgraph ACT_P["PROCEED path — complete onboarding"]
    direction LR
        PROV["provision_account (activate services)"]
        N_SUC["notify_success (Slack confirmation)"]
        N_EMAIL["send_email (CS team summary)"]
        N_WEL["send_customer_welcome (welcome email)"]
  end
 subgraph ASSESS["Step 5 · ASSESS RISKS & SENTIMENT (mandatory for PROCEED)"]
    direction LR
        MON_PROG["check_onboarding_progress\n(health status)"]
        MON_RISK["identify_onboarding_risks\n(overdue/blocked/stalled)"]
        MON_SENT["get_customer_sentiment\n(score, label, trend)"]
  end
 subgraph MONITOR["Step 6 · POST-PROVISIONING ACTIONS"]
    direction LR
        MON_REM["send_task_reminder (to owner)"]
        MON_ESC["escalate_stalled_onboarding\n(#cs-escalations)"]
        MON_UPD["update_onboarding_task\n(status change)"]
  end
 subgraph PORTFOLIO["Step 5 · PORTFOLIO MANAGEMENT"]
    direction LR
        PORT_OV["get_portfolio_overview\n(all accounts)"]
        PORT_AL["get_all_alerts (aggregated risks)"]
        PORT_BA["batch_send_reminders (by filter)"]
  end
 subgraph AGENT["2 · PYDANTIC AI AGENT — 28 tools via @agent.tool"]
        ENTRY["Initialize OnboardingDeps (account_id, correlation_id)"]
        FETCH
        VALIDATE
        DECIDE{"LLM DECISION POINT\n(errors / warnings / clear)"}
        ACT_B
        ACT_E
        ACT_P
        MONITOR
        PORTFOLIO
        OUTPUT["OnboardingResult (structured output)"]
  end
 subgraph REPORTS["3 · GENERATED REPORTS — post-run artifacts"]
    direction LR
        R_MD["fa:fa-file-text Markdown Report"]
        R_HTML["fa:fa-envelope HTML Email"]
        R_JSON["fa:fa-database JSON Audit Log"]
  end
 subgraph OBS["4 · OBSERVABILITY — opt-in tracing"]
    direction LR
        LOGFIRE["Pydantic Logfire (native tracing)"]
        LANGSMITH["LangSmith (OTEL bridge)"]
  end
 subgraph MCP["5 · FASTMCP SERVERS — app/mcp/"]
    direction TB
        MCP_SF["salesforce_server (accounts, users, opps, contracts)"]
        MCP_CLM["clm_server (contract lifecycle)"]
        MCP_NS["netsuite_server (invoices, payments)"]
        MCP_CUR["currency_server (FX conversion)"]
        MCP_PRV["provisioning_server (account activation)"]
        MCP_NOT["notifications_server (Slack, email)"]
        MCP_VAL["validation_server (business rules)"]
        MCP_SENT["sentiment_server (customer sentiment)"]
  end
 subgraph EXT["6 · EXTERNAL SYSTEMS — third-party integrations"]
    direction TB
        SF["fa:fa-cloud Salesforce CRM (Account · Opportunity · User · Contract)"]
        CLM_EXT["fa:fa-file-contract CLM (Contract Lifecycle Mgmt)"]
        NS["fa:fa-calculator NetSuite ERP (Invoices · Payments)"]
        FX["fa:fa-exchange Frankfurter API (ECB exchange rates)"]
        SLACK["fa:fa-comments Slack (Notifications)"]
        EMAIL_EXT["fa:fa-envelope Email (Welcome · CS alerts)"]
  end
    TRIGGERS -- account_id + correlation_id --> ENTRY
    ENTRY --> F_ACC
    F_ACC -- OwnerId --> F_USER
    F_ACC --> F_OPP
    F_OPP -- ContractId --> F_CON
    F_CON -- sf_contract_id --> F_CLM
    F_CLM -- clmContractRef --> F_INV
    FETCH --> V_BIZ
    V_BIZ --> V_FIN
    V_FIN -. if currencies differ .-> V_CUR
    VALIDATE --> DECIDE
    DECIDE -- "errors or violations" --> ACT_B
    DECIDE -- "warnings only (non-critical)" --> ACT_E
    DECIDE -- "all clear (no issues)" --> ACT_P
    ACT_B --> OUTPUT
    ACT_E --> OUTPUT
    ACT_P -- "post-provisioning" --> ASSESS
    ASSESS --> MONITOR
    ASSESS --> OUTPUT
    MONITOR --> OUTPUT
    PORTFOLIO -. "portfolio-wide (CS assistant)" .-> OUTPUT
    OUTPUT --> REPORTS
    AGENT -.-> OBS
    AGENT -. every tool mirrored as FastMCP server .-> MCP
    MCP --> EXT
    ```@{ label: "```" }

     WH:::trigger
     API:::trigger
     BATCH:::trigger
     F_USER:::fetch
     F_OPP:::fetch
     F_CON:::fetch
     F_CLM:::fetch
     F_INV:::fetch
     F_ACC:::fetch
     V_BIZ:::validate
     V_FIN:::validate
     V_CUR:::validate
     N_BLK:::block
     N_FIN:::block
     N_ESC:::escalate
     PROV:::proceed
     N_SUC:::proceed
     N_EMAIL:::proceed
     N_WEL:::proceed
     ENTRY:::entry
     DECIDE:::decision
     OUTPUT:::output
     R_MD:::report
     R_HTML:::report
     R_JSON:::report
     LOGFIRE:::obs
     LANGSMITH:::obs
     MCP_SF:::mcp
     MCP_CLM:::mcp
     MCP_NS:::mcp
     MCP_CUR:::mcp
     MCP_PRV:::mcp
     MCP_NOT:::mcp
     MCP_VAL:::mcp
     MCP_SENT:::mcp
     MON_SENT:::monitor
     MON_PROG:::monitor
     MON_RISK:::monitor
     MON_REM:::monitor
     MON_ESC:::monitor
     MON_UPD:::monitor
     PORT_OV:::portfolio
     PORT_AL:::portfolio
     PORT_BA:::portfolio
     SF:::ext
     CLM_EXT:::ext
     NS:::ext
     FX:::ext
     SLACK:::ext
     EMAIL_EXT:::ext
    classDef trigger   fill:#fff3cd,stroke:#d4a017,stroke-width:2px,color:#1f2937
    classDef entry     fill:#e8f0ff,stroke:#5b8def,stroke-width:2px,color:#1f2937
    classDef fetch     fill:#e6f7ee,stroke:#2e9d69,stroke-width:1px,color:#1f2937
    classDef validate  fill:#f1ecff,stroke:#8b7cf6,stroke-width:1px,color:#1f2937
    classDef decision  fill:#fff7db,stroke:#d4a017,stroke-width:2px,color:#1f2937
    classDef block     fill:#fde8e8,stroke:#e5484d,stroke-width:1px,color:#1f2937
    classDef escalate  fill:#fff3cd,stroke:#d4a017,stroke-width:1px,color:#1f2937
    classDef proceed   fill:#e6f7ee,stroke:#2e9d69,stroke-width:1px,color:#1f2937
    classDef output    fill:#e8f0ff,stroke:#5b8def,stroke-width:2px,color:#1f2937
    classDef report    fill:#f5f5f5,stroke:#999,stroke-width:1px,color:#1f2937
    classDef mcp       fill:#f0f0f0,stroke:#888,stroke-width:1px,stroke-dasharray:5 5,color:#555
    classDef ext       fill:#dbeafe,stroke:#3b82f6,stroke-width:1px,color:#1f2937
    classDef obs       fill:#fef3c7,stroke:#d97706,stroke-width:1px,stroke-dasharray:5 5,color:#92400e
    classDef monitor   fill:#e0f2fe,stroke:#0284c7,stroke-width:1px,color:#1f2937
    classDef portfolio fill:#fce7f3,stroke:#db2777,stroke-width:1px,color:#1f2937