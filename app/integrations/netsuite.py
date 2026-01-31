"""
Mock NetSuite REST API integration for invoice/billing data.

This simulates the actual NetSuite REST API structure:
- GET /invoice - List invoices
- GET /invoice/{id} - Get single invoice
- POST /invoice - Create invoice
- PATCH /invoice/{id} - Update invoice

In production, this would use:
- OAuth 1.0 or OAuth 2.0 authentication
- NetSuite REST Web Services API
- Base URL: https://{account_id}.suitetalk.api.netsuite.com/services/rest/record/v1
"""

import uuid
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from app.logging.logger import log_event


# ============================================================================
# SIMULATED HTTP CLIENT
# ============================================================================

@dataclass
class MockHTTPResponse:
    """Simulates an HTTP response from NetSuite API."""
    status_code: int
    headers: Dict[str, str]
    json_data: Dict[str, Any]
    
    def json(self) -> Dict[str, Any]:
        return self.json_data


class NetSuiteAPIError(Exception):
    """Exception for NetSuite API errors."""
    def __init__(self, status_code: int, error_code: str, message: str):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        super().__init__(f"NetSuite API Error {status_code}: [{error_code}] {message}")


# ============================================================================
# MOCK INVOICE DATA (Matching actual NetSuite schema)
# ============================================================================

MOCK_INVOICES_DB: Dict[str, Dict[str, Any]] = {
    "1001": {
        "id": "1001",
        "tranId": "INV-2024-001",
        "externalId": "ACME-001-INV",
        "entity": {
            "id": "101",
            "refName": "ACME Corp"
        },
        "tranDate": "2024-01-01",
        "dueDate": "2024-01-31",
        "status": {
            "id": "B",  # B = Paid In Full
            "refName": "Paid In Full"
        },
        "currency": {
            "id": "1",
            "refName": "USD"
        },
        "exchangeRate": 1.0,
        "subtotal": 150000.00,
        "taxTotal": 0.00,
        "shippingCost": 0.00,
        "handlingCost": 0.00,
        "total": 150000.00,
        "amountPaid": 150000.00,
        "amountRemaining": 0.00,
        "terms": {
            "id": "1",
            "refName": "Net 30"
        },
        "subsidiary": {
            "id": "1",
            "refName": "StackAdapt Inc."
        },
        "department": {
            "id": "1",
            "refName": "Sales"
        },
        "class": {
            "id": "1",
            "refName": "Enterprise"
        },
        "memo": "Enterprise License - Annual Subscription",
        "email": "billing@acme.com",
        "billAddress": "123 Enterprise Ave\nSan Francisco, CA 94105\nUnited States",
        "billAddressee": "ACME Corp",
        "billAttention": "Accounts Payable",
        "createdDate": "2024-01-01T10:00:00Z",
        "lastModifiedDate": "2024-01-15T14:30:00Z",
        "item": {
            "items": [
                {
                    "line": 1,
                    "item": {"id": "501", "refName": "Enterprise License - Annual"},
                    "description": "StackAdapt Enterprise Platform - 12 Month License",
                    "quantity": 1.0,
                    "rate": 120000.00,
                    "amount": 120000.00
                },
                {
                    "line": 2,
                    "item": {"id": "502", "refName": "Professional Services"},
                    "description": "Implementation and Training Services",
                    "quantity": 1.0,
                    "rate": 30000.00,
                    "amount": 30000.00
                }
            ]
        },
        "links": [
            {"rel": "self", "href": "/invoice/1001"}
        ]
    },
    "1002": {
        "id": "1002",
        "tranId": "INV-2024-002",
        "externalId": "BETA-002-INV",
        "entity": {
            "id": "102",
            "refName": "Beta Industries"
        },
        "tranDate": "2024-01-15",
        "dueDate": "2024-02-14",
        "status": {
            "id": "A",  # A = Open
            "refName": "Open"
        },
        "currency": {
            "id": "2",
            "refName": "CAD"
        },
        "exchangeRate": 1.35,
        "subtotal": 75000.00,
        "taxTotal": 9750.00,  # 13% HST
        "shippingCost": 0.00,
        "handlingCost": 0.00,
        "total": 84750.00,
        "amountPaid": 0.00,
        "amountRemaining": 84750.00,
        "terms": {
            "id": "2",
            "refName": "Net 45"
        },
        "subsidiary": {
            "id": "2",
            "refName": "StackAdapt Canada Ltd."
        },
        "department": {
            "id": "1",
            "refName": "Sales"
        },
        "class": {
            "id": "2",
            "refName": "Growth"
        },
        "memo": "Growth Plan - Annual Subscription",
        "email": "ap@betaindustries.ca",
        "billAddress": "456 Industrial Blvd\nToronto, ON M5V 1A1\nCanada",
        "billAddressee": "Beta Industries Inc.",
        "billAttention": "Finance Department",
        "createdDate": "2024-01-15T09:00:00Z",
        "lastModifiedDate": "2024-01-15T09:00:00Z",
        "item": {
            "items": [
                {
                    "line": 1,
                    "item": {"id": "503", "refName": "Growth License - Annual"},
                    "description": "StackAdapt Growth Platform - 12 Month License",
                    "quantity": 1.0,
                    "rate": 75000.00,
                    "amount": 75000.00
                }
            ]
        },
        "links": [
            {"rel": "self", "href": "/invoice/1002"}
        ]
    },
    "1003": {
        "id": "1003",
        "tranId": "INV-2023-089",
        "externalId": "GAMMA-003-INV",
        "entity": {
            "id": "103",
            "refName": "Gamma Startup"
        },
        "tranDate": "2023-12-01",
        "dueDate": "2023-12-31",
        "status": {
            "id": "A",  # A = Open (but overdue)
            "refName": "Open"
        },
        "currency": {
            "id": "1",
            "refName": "USD"
        },
        "exchangeRate": 1.0,
        "subtotal": 25000.00,
        "taxTotal": 0.00,
        "shippingCost": 0.00,
        "handlingCost": 0.00,
        "total": 25000.00,
        "amountPaid": 0.00,
        "amountRemaining": 25000.00,
        "terms": {
            "id": "1",
            "refName": "Net 30"
        },
        "subsidiary": {
            "id": "1",
            "refName": "StackAdapt Inc."
        },
        "department": {
            "id": "1", 
            "refName": "Sales"
        },
        "class": {
            "id": "3",
            "refName": "Starter"
        },
        "memo": "Starter Plan - Annual Subscription",
        "email": "founders@gammastartup.io",
        "billAddress": "789 Startup Lane\nAustin, TX 78701\nUnited States",
        "billAddressee": "Gamma Startup Inc.",
        "createdDate": "2023-12-01T11:00:00Z",
        "lastModifiedDate": "2023-12-01T11:00:00Z",
        "item": {
            "items": [
                {
                    "line": 1,
                    "item": {"id": "504", "refName": "Starter License - Annual"},
                    "description": "StackAdapt Starter Platform - 12 Month License",
                    "quantity": 1.0,
                    "rate": 25000.00,
                    "amount": 25000.00
                }
            ]
        },
        "links": [
            {"rel": "self", "href": "/invoice/1003"}
        ]
    },
    "1004": {
        "id": "1004",
        "tranId": "INV-2024-003",
        "externalId": "DELTA-004-INV",
        "entity": {
            "id": "104",
            "refName": "Delta Corp"
        },
        "tranDate": "2024-01-20",
        "dueDate": "2024-02-19",
        "status": {
            "id": "E",  # E = Pending Approval (Draft-like state)
            "refName": "Pending Approval"
        },
        "currency": {
            "id": "1",
            "refName": "USD"
        },
        "exchangeRate": 1.0,
        "subtotal": 50000.00,
        "taxTotal": 0.00,
        "total": 50000.00,
        "amountPaid": 0.00,
        "amountRemaining": 50000.00,
        "terms": {
            "id": "1",
            "refName": "Net 30"
        },
        "memo": "Draft invoice - not yet sent",
        "createdDate": "2024-01-20T08:00:00Z",
        "lastModifiedDate": "2024-01-20T08:00:00Z",
        "item": {
            "items": []
        },
        "links": [
            {"rel": "self", "href": "/invoice/1004"}
        ]
    }
}

# Mapping from external account IDs to NetSuite invoice IDs
ACCOUNT_TO_INVOICE_MAP = {
    "ACME-001": "1001",
    "BETA-002": "1002", 
    "GAMMA-003": "1003",
    "DELTA-004": "1004",
}


# ============================================================================
# MOCK REST API CLIENT
# ============================================================================

class NetSuiteClient:
    """
    Mock NetSuite REST API client.
    
    In production, this would handle:
    - OAuth authentication
    - Request signing
    - Rate limiting
    - Pagination
    - Error handling
    """
    
    def __init__(self, account_id: str = "TSTDRV123456", base_url: str = None):
        self.account_id = account_id
        self.base_url = base_url or f"https://{account_id}.suitetalk.api.netsuite.com/services/rest/record/v1"
        self._request_count = 0
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Dict = None,
        json_body: Dict = None,
        headers: Dict = None
    ) -> MockHTTPResponse:
        """
        Simulate making an HTTP request to NetSuite REST API.
        """
        self._request_count += 1
        request_id = str(uuid.uuid4())[:8]
        
        log_event(
            "netsuite.api.request",
            method=method,
            endpoint=endpoint,
            request_id=request_id,
            params=params,
        )
        
        # Simulate API latency would go here in real implementation
        # await asyncio.sleep(0.1)
        
        return MockHTTPResponse(
            status_code=200,
            headers={
                "Content-Type": "application/vnd.oracle.resource+json; type=singular",
                "X-N-OperationId": request_id,
            },
            json_data={}
        )
    
    def get_invoice(self, invoice_id: str, expand_sub_resources: bool = False) -> Dict[str, Any]:
        """
        GET /invoice/{id}
        
        Retrieve a single invoice by internal ID.
        """
        log_event("netsuite.api.get_invoice", invoice_id=invoice_id)
        
        if invoice_id not in MOCK_INVOICES_DB:
            raise NetSuiteAPIError(
                status_code=404,
                error_code="RECORD_NOT_FOUND",
                message=f"Invoice with ID {invoice_id} not found"
            )
        
        invoice = MOCK_INVOICES_DB[invoice_id].copy()
        
        log_event(
            "netsuite.api.get_invoice.success",
            invoice_id=invoice_id,
            tran_id=invoice.get("tranId"),
            status=invoice.get("status", {}).get("refName"),
        )
        
        return invoice
    
    def get_invoice_by_external_id(self, external_id: str) -> Optional[Dict[str, Any]]:
        """
        GET /invoice?q=externalId IS "{external_id}"
        
        Search for invoice by external ID.
        """
        log_event("netsuite.api.search_invoice", external_id=external_id)
        
        for invoice in MOCK_INVOICES_DB.values():
            if invoice.get("externalId") == external_id:
                return invoice
        
        return None
    
    def list_invoices(
        self, 
        q: str = None,
        limit: int = 1000,
        offset: int = 0,
        fields: List[str] = None
    ) -> Dict[str, Any]:
        """
        GET /invoice
        
        List invoices with optional filtering.
        
        Returns invoiceCollection schema.
        """
        log_event("netsuite.api.list_invoices", query=q, limit=limit, offset=offset)
        
        # Filter invoices based on query
        items = list(MOCK_INVOICES_DB.values())
        
        if q:
            # Simple query parsing (in reality NetSuite uses SuiteQL)
            # Example: q="entity.id IS 101"
            filtered = []
            for inv in items:
                if "entity" in q.lower():
                    # Extract entity ID from query
                    entity_id = inv.get("entity", {}).get("id")
                    if entity_id and entity_id in q:
                        filtered.append(inv)
                elif "status" in q.lower():
                    status_id = inv.get("status", {}).get("id")
                    if status_id and status_id in q:
                        filtered.append(inv)
                else:
                    filtered.append(inv)
            items = filtered
        
        # Apply pagination
        total = len(items)
        items = items[offset:offset + limit]
        
        # Build collection response
        response = {
            "count": len(items),
            "hasMore": (offset + limit) < total,
            "items": items,
            "offset": offset,
            "totalResults": total,
            "links": [
                {"rel": "self", "href": f"/invoice?limit={limit}&offset={offset}"}
            ]
        }
        
        if response["hasMore"]:
            response["links"].append({
                "rel": "next",
                "href": f"/invoice?limit={limit}&offset={offset + limit}"
            })
        
        return response
    
    def get_invoices_by_customer(self, customer_id: str) -> List[Dict[str, Any]]:
        """
        GET /invoice?q=entity.id IS {customer_id}
        
        Get all invoices for a specific customer.
        """
        result = self.list_invoices(q=f"entity.id IS {customer_id}")
        return result.get("items", [])


# ============================================================================
# SINGLETON CLIENT INSTANCE
# ============================================================================

_client: Optional[NetSuiteClient] = None


def get_client() -> NetSuiteClient:
    """Get or create the NetSuite client singleton."""
    global _client
    if _client is None:
        _client = NetSuiteClient()
    return _client


# ============================================================================
# HIGH-LEVEL FUNCTIONS (Used by the agent)
# ============================================================================

def get_invoice(account_id: str) -> Dict[str, Any]:
    """
    Fetch invoice data for an account.
    
    This is the main function used by the onboarding agent.
    Returns a simplified structure for the agent to process.
    """
    client = get_client()
    
    # Map account ID to invoice ID
    invoice_id = ACCOUNT_TO_INVOICE_MAP.get(account_id)
    
    if not invoice_id:
        log_event("netsuite.invoice.not_found", account_id=account_id)
        return {
            "invoice_id": None,
            "status": "NOT_FOUND",
            "error": f"No invoice found for account {account_id}"
        }
    
    try:
        # Call the REST API
        invoice = client.get_invoice(invoice_id)
        
        # Transform NetSuite response to agent-friendly format
        return _transform_invoice_for_agent(invoice, account_id)
        
    except NetSuiteAPIError as e:
        log_event("netsuite.api.error", error=str(e), account_id=account_id)
        return {
            "invoice_id": None,
            "status": "API_ERROR",
            "error": str(e)
        }


def _transform_invoice_for_agent(invoice: Dict[str, Any], account_id: str) -> Dict[str, Any]:
    """
    Transform NetSuite invoice to agent-friendly format.
    
    Maps NetSuite status codes to simple statuses:
    - A (Open) → PENDING or OVERDUE (based on due date)
    - B (Paid In Full) → PAID
    - E (Pending Approval) → DRAFT
    - V (Voided) → VOIDED
    """
    status_map = {
        "A": "OPEN",
        "B": "PAID",
        "D": "CANCELLED",
        "E": "DRAFT",
        "V": "VOIDED",
    }
    
    ns_status = invoice.get("status", {}).get("id", "A")
    status = status_map.get(ns_status, "UNKNOWN")
    
    # Check if overdue
    due_date_str = invoice.get("dueDate")
    days_overdue = 0
    
    if due_date_str and status == "OPEN":
        try:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
            today = date.today()
            if today > due_date:
                days_overdue = (today - due_date).days
                status = "OVERDUE"
        except ValueError:
            pass
    
    # Extract line items
    items = invoice.get("item", {}).get("items", [])
    line_items = [
        {
            "description": item.get("description", item.get("item", {}).get("refName", "")),
            "amount": item.get("amount", 0)
        }
        for item in items
    ]
    
    return {
        # Basic identifiers
        "invoice_id": invoice.get("tranId"),
        "internal_id": invoice.get("id"),
        "external_id": invoice.get("externalId"),
        "account_id": account_id,
        
        # Status
        "status": status,
        "status_detail": invoice.get("status", {}).get("refName"),
        "days_overdue": days_overdue,
        
        # Amounts
        "currency": invoice.get("currency", {}).get("refName", "USD"),
        "subtotal": invoice.get("subtotal", 0),
        "tax_total": invoice.get("taxTotal", 0),
        "shipping_cost": invoice.get("shippingCost", 0),
        "total": invoice.get("total", 0),
        "amount_paid": invoice.get("amountPaid", 0),
        "amount_remaining": invoice.get("amountRemaining", 0),
        
        # Dates
        "invoice_date": invoice.get("tranDate"),
        "due_date": invoice.get("dueDate"),
        
        # Terms
        "terms": invoice.get("terms", {}).get("refName"),
        
        # Customer info
        "customer_name": invoice.get("entity", {}).get("refName"),
        "customer_email": invoice.get("email"),
        "billing_address": invoice.get("billAddress"),
        
        # Line items
        "line_items": line_items,
        
        # Metadata
        "memo": invoice.get("memo"),
        "created_date": invoice.get("createdDate"),
        "last_modified_date": invoice.get("lastModifiedDate"),
        
        # Classification
        "subsidiary": invoice.get("subsidiary", {}).get("refName"),
        "department": invoice.get("department", {}).get("refName"),
        "class": invoice.get("class", {}).get("refName"),
    }


def get_invoice_status(account_id: str) -> str:
    """Get just the invoice status for an account."""
    invoice = get_invoice(account_id)
    return invoice.get("status", "UNKNOWN")


def is_payment_received(account_id: str) -> bool:
    """Check if payment has been received for an account."""
    invoice = get_invoice(account_id)
    return invoice.get("status") == "PAID"


def get_outstanding_amount(account_id: str) -> float:
    """Get outstanding amount for an account."""
    invoice = get_invoice(account_id)
    if invoice.get("status") == "PAID":
        return 0.0
    return invoice.get("amount_remaining", 0.0)


def get_days_overdue(account_id: str) -> int:
    """Get number of days the invoice is overdue."""
    invoice = get_invoice(account_id)
    return invoice.get("days_overdue", 0)


# ============================================================================
# ADDITIONAL API FUNCTIONS (for completeness)
# ============================================================================

def create_invoice(invoice_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    POST /invoice
    
    Create a new invoice in NetSuite.
    """
    client = get_client()
    
    log_event("netsuite.api.create_invoice", customer=invoice_data.get("entity"))
    
    # In production, this would POST to NetSuite
    # For mock, just return success
    new_id = str(max(int(k) for k in MOCK_INVOICES_DB.keys()) + 1)
    
    return {
        "id": new_id,
        "status": "created",
        "links": [{"rel": "self", "href": f"/invoice/{new_id}"}]
    }


def update_invoice(invoice_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    PATCH /invoice/{id}
    
    Update an existing invoice.
    """
    client = get_client()
    
    log_event("netsuite.api.update_invoice", invoice_id=invoice_id, updates=list(updates.keys()))
    
    if invoice_id not in MOCK_INVOICES_DB:
        raise NetSuiteAPIError(404, "RECORD_NOT_FOUND", f"Invoice {invoice_id} not found")
    
    # Apply updates
    MOCK_INVOICES_DB[invoice_id].update(updates)
    MOCK_INVOICES_DB[invoice_id]["lastModifiedDate"] = datetime.utcnow().isoformat()
    
    return {"status": "updated"}
