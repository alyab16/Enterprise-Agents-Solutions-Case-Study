# Solution Design: Enterprise Onboarding Agent

## Overview

This document describes the architecture and design decisions for the Enterprise Onboarding Agent.

## Key Design Principles

### 1. Error Handling

- **Never swallow errors**: Integration errors are always captured and reported
- **Fail fast**: When an external system fails, stop immediately
- **Full context**: Errors include system, operation, account, and raw message

### 2. Observability

- Structured logging with correlation IDs
- API error tracking with entity context
- Audit logs for compliance

### 3. Separation of Concerns

- Integrations: Handle API communication
- Nodes: Orchestrate workflow steps
- Invariants: Enforce business rules
- Reports: Generate outputs

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    FastAPI Layer                      │
│  /webhook/salesforce    /demo/run    /demo/reports    │
└─────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│                  LangGraph Workflow                   │
│  init → fetch_sf → fetch_clm → fetch_invoice →       │
│  validate → analyze → decide → notify → provision     │
└─────────────────────────────────────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  Salesforce │   │     CLM     │   │   NetSuite  │
│ Integration │   │ Integration │   │ Integration │
└─────────────┘   └─────────────┘   └─────────────┘
```

## Error Flow

1. Integration makes API call
2. If error occurs, return structured error payload (not exception)
3. Node detects error payload and calls `add_api_error()`
4. `add_api_error()` enriches with context and adds violation
5. Workflow continues to decision node
6. Decision is BLOCK due to violation
7. Reports include full error details

## Report Generation

Reports include:
- Account and correlation IDs
- All API errors with full context
- Business violations and warnings
- Recommended actions
- Raw error messages for debugging
