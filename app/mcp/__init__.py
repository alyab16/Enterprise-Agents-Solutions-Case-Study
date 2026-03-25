"""
FastMCP server definitions for the Enterprise Onboarding Agent.

Each module defines an independent MCP server that wraps an existing
integration. In production, these can be deployed as standalone services
accessible via HTTP (MCPServerStreamableHTTP). For this implementation,
the tools are registered in-process on the Pydantic AI agent, while
these server definitions serve as the extractable MCP interface.

Servers:
- salesforce_server: Salesforce CRM data (accounts, users, opportunities, contracts)
- clm_server: Contract Lifecycle Management (contract status, signatures)
- netsuite_server: NetSuite ERP (invoices, payments)
- provisioning_server: SaaS tenant provisioning and onboarding tasks
- notifications_server: Slack and email notifications
- validation_server: Business rule validation (invariant checks)
"""
