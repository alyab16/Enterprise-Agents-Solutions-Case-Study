flowchart TB

    %% Specialized Agents
    subgraph AGENTS["🤖 Specialized AI Agents"]
        A1[Onboarding Coordinator<br/><i>Orchestrates workflow</i>]
        A2[Contract Agent<br/><i>Monitors signatures</i>]
        A3[Finance Agent<br/><i>Tracks payments</i>]
        A4[Task Monitor Agent<br/><i>Overdue detection</i>]
        A5[Sentiment Agent<br/><i>Customer interaction scoring</i>]
    end

    %% Tool Labels
    T1[get_account<br/>get_opportunity]
    T2[get_contract<br/>send_reminder]
    T3[get_invoice<br/>send_dunning]
    T4[get_overdue<br/>update_status]
    T5[get_sentiment<br/>log_interaction]

    %% Router
    R[MCP Tool Router<br/>Route Tool Calls]

    %% MCP Servers
    subgraph SERVERS["🔧 MCP Servers"]
        S1[Salesforce MCP Server<br/>salesforce.*]
        S2[CLM MCP Server<br/>clm.*]
        S3[NetSuite MCP Server<br/>netsuite.*]
        S4[Task MCP Server<br/>tasks.*]
        S5[Sentiment MCP Server<br/>sentiment.*]
    end

    %% External APIs
    subgraph APIS["🌐 External APIs"]
        API1[(Salesforce REST API)]
        API2[(CLM REST API)]
        API3[(NetSuite REST API)]
    end

    %% Connections: Agents → Tools → Router
    A1 --> T1 --> R
    A2 --> T2 --> R
    A3 --> T3 --> R
    A4 --> T4 --> R
    A5 --> T5 --> R

    %% Router → MCP Servers
    R --> S1
    R --> S2
    R --> S3
    R --> S4
    R --> S5

    %% Auth + External APIs
    S1 -- OAuth 2.0 --> API1
    S2 -- Bearer Token --> API2
    S3 -- Token Auth --> API3