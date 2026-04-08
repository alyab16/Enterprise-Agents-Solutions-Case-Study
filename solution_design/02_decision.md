%%{init: {
  "theme": "base",
  "themeVariables": {
    "background": "#f8fafc",
    "primaryTextColor": "#1f2937",
    "lineColor": "#475569",
    "fontSize": "16px"
  }
}}%%
flowchart TD

    %% Nodes
    A([🚀 Start Onboarding])

    B{API Errors<br/>Count > 0?}
    C{Violations<br/>Count > 0?}
    D{Warnings<br/>Count > 0?}

    E[🚫 BLOCK<br/>Cannot Proceed]
    F[Notify CS Team<br/>Send Block Alert]

    G[⚠️ ESCALATE<br/>Human Review Required]
    H[Notify CS Team<br/>Request Review]

    I[✅ PROCEED<br/>Auto-Provision]
    J[Provision Tenant<br/>Create 14 Onboarding Tasks]
    K[Notify CS Team<br/>Send Welcome Email]

    M[📊 Assess Risks & Sentiment<br/>check_onboarding_progress<br/>identify_onboarding_risks<br/>get_customer_sentiment]

    L([✓ Complete])

    %% Flow
    A --> B

    B -- Yes --> E
    B -- No --> C

    C -- Yes --> E
    C -- No --> D

    D -- Yes --> G
    D -- No --> I

    E --> F --> L
    G --> H --> L
    I --> J --> K --> M --> L

    %% Styles
    classDef start fill:#2563eb,color:#ffffff,stroke:#1e40af,stroke-width:2px;
    classDef decision fill:#bfdbfe,color:#1e3a8a,stroke:#60a5fa,stroke-width:2px;
    classDef block fill:#fecaca,color:#7f1d1d,stroke:#dc2626,stroke-width:2px;
    classDef escalate fill:#fde68a,color:#78350f,stroke:#f59e0b,stroke-width:2px;
    classDef proceed fill:#bbf7d0,color:#14532d,stroke:#16a34a,stroke-width:2px;
    classDef process fill:#e0f2fe,color:#0c4a6e,stroke:#38bdf8,stroke-width:1.5px;
    classDef final fill:#1e3a8a,color:#ffffff,stroke:#1e40af,stroke-width:2px;

    %% Apply Classes
    class A start;
    class B,C,D decision;
    class E block;
    class G escalate;
    class I proceed;
    class F,H,J,K,M process;
    class L final;