"""
Simulate CS-led remediation of onboarding blockers and warnings.

These helpers mutate the in-memory mock system data so a subsequent onboarding
re-run can transition an account from BLOCK/ESCALATE into PROCEED.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
from typing import Any, Dict, List

from app.integrations import clm, netsuite, salesforce


_ORIGINAL_SALESFORCE_ACCOUNTS = deepcopy(salesforce.MOCK_ACCOUNTS)
_ORIGINAL_SALESFORCE_OPPORTUNITIES = deepcopy(salesforce.MOCK_OPPORTUNITIES)
_ORIGINAL_SALESFORCE_CONTRACTS = deepcopy(salesforce.MOCK_CONTRACTS)
_ORIGINAL_CLM_DB = deepcopy(clm.MOCK_CLM_DB)
_ORIGINAL_NETSUITE_DB = deepcopy(netsuite.MOCK_INVOICES_DB)
_ORIGINAL_NETSUITE_MAP = deepcopy(netsuite.ACCOUNT_TO_INVOICE_MAP)


def reset_resolution_state() -> None:
    """Restore the mock systems to their original demo state."""
    salesforce.MOCK_ACCOUNTS.clear()
    salesforce.MOCK_ACCOUNTS.update(deepcopy(_ORIGINAL_SALESFORCE_ACCOUNTS))

    salesforce.MOCK_OPPORTUNITIES.clear()
    salesforce.MOCK_OPPORTUNITIES.update(deepcopy(_ORIGINAL_SALESFORCE_OPPORTUNITIES))

    salesforce.MOCK_CONTRACTS.clear()
    salesforce.MOCK_CONTRACTS.update(deepcopy(_ORIGINAL_SALESFORCE_CONTRACTS))

    clm.MOCK_CLM_DB.clear()
    clm.MOCK_CLM_DB.update(deepcopy(_ORIGINAL_CLM_DB))

    netsuite.MOCK_INVOICES_DB.clear()
    netsuite.MOCK_INVOICES_DB.update(deepcopy(_ORIGINAL_NETSUITE_DB))

    netsuite.ACCOUNT_TO_INVOICE_MAP.clear()
    netsuite.ACCOUNT_TO_INVOICE_MAP.update(deepcopy(_ORIGINAL_NETSUITE_MAP))


def simulate_issue_resolution(account_id: str) -> Dict[str, Any]:
    """
    Apply demo-safe remediations for an account so the next onboarding run can
    proceed through provisioning.
    """
    changes: List[str] = []

    _ensure_account_exists(account_id, changes)
    _resolve_account_data(account_id, changes)
    _resolve_opportunity(account_id, changes)
    contract_id = _resolve_salesforce_contract(account_id, changes)
    clm_contract_id = _resolve_clm_contract(account_id, contract_id, changes)
    _resolve_invoice(account_id, clm_contract_id, changes)

    return {
        "status": "resolved",
        "account_id": account_id,
        "changes_applied": changes,
        "resolved_at": datetime.utcnow().isoformat(),
    }


def _ensure_account_exists(account_id: str, changes: List[str]) -> None:
    if account_id in salesforce.MOCK_ACCOUNTS:
        return

    template = deepcopy(_ORIGINAL_SALESFORCE_ACCOUNTS["ACME-001"])
    template["Id"] = f"0018Z0000{account_id.replace('-', '')[:8]}Q"
    template["Name"] = f"Resolved {account_id}"
    template["Website"] = f"https://{account_id.lower().replace('-', '')}.demo"
    template["CreatedDate"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000+0000")
    template["LastModifiedDate"] = template["CreatedDate"]
    salesforce.MOCK_ACCOUNTS[account_id] = template
    changes.append("Created missing Salesforce account record")


def _resolve_account_data(account_id: str, changes: List[str]) -> None:
    account = salesforce.MOCK_ACCOUNTS[account_id]
    updated = False

    defaults = {
        "BillingCountry": "United States",
        "BillingCity": "New York",
        "BillingState": "NY",
        "BillingStreet": "1 Customer Way",
        "BillingPostalCode": "10001",
        "Industry": "Technology",
        "OwnerId": "0058Z000001OWNER",
        "Type": "Customer",
        "IsDeleted": False,
    }

    for field, value in defaults.items():
        if account.get(field) != value and (field in {"IsDeleted", "Type"} or not account.get(field)):
            account[field] = value
            updated = True

    if updated:
        account["LastModifiedDate"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000+0000")
        changes.append("Normalized Salesforce account fields for onboarding readiness")


def _resolve_opportunity(account_id: str, changes: List[str]) -> Dict[str, Any]:
    account = salesforce.MOCK_ACCOUNTS[account_id]
    opportunity = salesforce.get_opportunity_by_account(account_id)

    if opportunity is None:
        template = deepcopy(_ORIGINAL_SALESFORCE_OPPORTUNITIES["OPP-ACME-001"])
        template["Id"] = f"0068Z0000{account_id.replace('-', '')[:8]}O"
        template["Name"] = f"{account['Name']} - Resolved Deal"
        template["AccountId"] = account["Id"]
        template["Amount"] = 150000.00
        opportunity_key = f"OPP-{account_id}"
        salesforce.MOCK_OPPORTUNITIES[opportunity_key] = template
        opportunity = template
        changes.append("Created missing Salesforce opportunity")

    updated = False
    if opportunity.get("StageName") != "Closed Won":
        opportunity["StageName"] = "Closed Won"
        opportunity["IsClosed"] = True
        opportunity["IsWon"] = True
        opportunity["Probability"] = 100
        updated = True
    if not opportunity.get("AccountId"):
        opportunity["AccountId"] = account["Id"]
        updated = True
    if not opportunity.get("OwnerId"):
        opportunity["OwnerId"] = "0058Z000001OWNER"
        updated = True
    if not opportunity.get("CloseDate"):
        opportunity["CloseDate"] = datetime.utcnow().strftime("%Y-%m-%d")
        updated = True
    if not opportunity.get("Amount"):
        opportunity["Amount"] = 150000.00
        updated = True

    if updated:
        changes.append("Resolved Salesforce opportunity to Closed Won")

    return opportunity


def _resolve_salesforce_contract(account_id: str, changes: List[str]) -> str:
    account = salesforce.MOCK_ACCOUNTS[account_id]
    opportunity = salesforce.get_opportunity_by_account(account_id)
    contract = salesforce.get_contract_by_account(account_id)

    if contract is None:
        contract = deepcopy(_ORIGINAL_SALESFORCE_CONTRACTS["8008Z000000CONTR"])
        contract["Id"] = f"8008Z0000{account_id.replace('-', '')[:8]}C"
        contract["ContractNumber"] = f"R{account_id.replace('-', '')[:7]}"
        contract["AccountId"] = account["Id"]
        salesforce.MOCK_CONTRACTS[contract["Id"]] = contract
        changes.append("Created missing Salesforce contract")

    contract["AccountId"] = account["Id"]
    contract["OwnerId"] = "0058Z000001OWNER"
    contract["Status"] = "Activated"
    contract["StartDate"] = contract.get("StartDate") or datetime.utcnow().strftime("%Y-%m-%d")
    contract["EndDate"] = contract.get("EndDate") or (datetime.utcnow() + timedelta(days=365)).strftime("%Y-%m-%d")
    contract["ActivatedDate"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000+0000")
    contract["CustomerSignedDate"] = contract.get("CustomerSignedDate") or datetime.utcnow().strftime("%Y-%m-%d")
    contract["CompanySignedDate"] = contract.get("CompanySignedDate") or datetime.utcnow().strftime("%Y-%m-%d")

    if opportunity and opportunity.get("ContractId") != contract["Id"]:
        opportunity["ContractId"] = contract["Id"]

    changes.append("Activated Salesforce contract linkage")
    return contract["Id"]


def _resolve_clm_contract(account_id: str, sf_contract_id: str, changes: List[str]) -> str:
    contract = clm.MOCK_CLM_DB.get(account_id)
    if contract is None:
        contract = deepcopy(_ORIGINAL_CLM_DB["ACME-001"])
        contract["id"] = f"CLM-CTR-{account_id.replace('-', '')[:6]}"
        contract["contract_id"] = contract["id"]
        contract["external_id"] = account_id
        contract["name"] = f"{salesforce.MOCK_ACCOUNTS[account_id]['Name']} - Service Agreement"
        clm.MOCK_CLM_DB[account_id] = contract
        changes.append("Created missing CLM contract")

    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    contract["salesforce_contract_id"] = sf_contract_id
    contract["status"] = "EXECUTED"
    contract["status_details"] = {
        "code": "EXECUTED",
        "label": "Fully Executed",
        "description": "All signatures collected and countersigned",
    }
    contract["effective_date"] = contract.get("effective_date") or datetime.utcnow().strftime("%Y-%m-%d")
    contract["expiry_date"] = contract.get("expiry_date") or (datetime.utcnow() + timedelta(days=365)).strftime("%Y-%m-%d")
    contract["signed_date"] = now

    signatories = contract.get("signatories") or []
    if not signatories:
        signatories = [
            {
                "id": f"SIG-{account_id}-1",
                "name": "Customer Signer",
                "email": f"{account_id.lower().replace('-', '')}@customer.demo",
                "role": "Executive Sponsor",
                "company": salesforce.MOCK_ACCOUNTS[account_id]["Name"],
            },
            {
                "id": f"SIG-{account_id}-2",
                "name": "Sarah Johnson",
                "email": "sarah.johnson@stackadapt.com",
                "role": "CS Manager",
                "company": "StackAdapt",
            },
        ]
        contract["signatories"] = signatories

    for signatory in signatories:
        signatory["signed"] = True
        signatory["signed_date"] = signatory.get("signed_date") or now
        signatory.pop("reminder_sent", None)
        signatory.pop("reminder_date", None)

    changes.append("Marked CLM contract as fully executed")
    return contract["contract_id"]


def _resolve_invoice(account_id: str, clm_contract_id: str, changes: List[str]) -> None:
    opportunity = salesforce.get_opportunity_by_account(account_id) or {}
    account = salesforce.MOCK_ACCOUNTS[account_id]
    invoice_key = _find_invoice_key(account_id)

    if invoice_key is None:
        template = deepcopy(_ORIGINAL_NETSUITE_DB["1001"])
        invoice_key = str(max(int(key) for key in netsuite.MOCK_INVOICES_DB.keys()) + 1)
        template["id"] = invoice_key
        template["tranId"] = f"INV-RES-{account_id.replace('-', '')[:6]}"
        template["externalId"] = f"{account_id}-INV"
        netsuite.MOCK_INVOICES_DB[invoice_key] = template
        changes.append("Created missing NetSuite invoice")

    invoice = netsuite.MOCK_INVOICES_DB[invoice_key]
    total = float(opportunity.get("Amount") or invoice.get("total") or 150000.0)
    today = datetime.utcnow().strftime("%Y-%m-%d")

    invoice["externalId"] = f"{account_id}-INV"
    invoice["clmContractRef"] = clm_contract_id
    invoice["entity"] = {"id": invoice.get("entity", {}).get("id", "999"), "refName": account["Name"]}
    invoice["email"] = invoice.get("email") or f"billing@{account_id.lower().replace('-', '')}.demo"
    invoice["billAddress"] = invoice.get("billAddress") or "1 Customer Way\nNew York, NY 10001\nUnited States"
    invoice["currency"] = {"id": "1", "refName": "USD"}
    invoice["exchangeRate"] = 1.0
    invoice["subtotal"] = total
    invoice["taxTotal"] = 0.0
    invoice["total"] = total
    invoice["amountPaid"] = total
    invoice["amountRemaining"] = 0.0
    invoice["tranDate"] = today
    invoice["dueDate"] = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")
    invoice["status"] = {"id": "B", "refName": "Paid In Full"}
    invoice["lastModifiedDate"] = datetime.utcnow().isoformat()
    netsuite.ACCOUNT_TO_INVOICE_MAP[account_id] = invoice_key

    changes.append("Aligned and marked NetSuite invoice as paid in full")


def _find_invoice_key(account_id: str) -> str | None:
    external_id = f"{account_id}-INV"
    for key, invoice in netsuite.MOCK_INVOICES_DB.items():
        if invoice.get("externalId") == external_id:
            return key
    return None
