from __future__ import annotations
from typing import List, Dict, Any

import frappe

# NOTE: These are stubs to demonstrate structure. Replace with ORM implementations.


def top_items(posting_date_from: str, posting_date_to: str, limit: int = 5) -> Dict[str, Any]:
    return {
        "columns": ["Item", "Qty", "Amount"],
        "rows": [["Example Item A", 10, 1000.0], ["Example Item B", 8, 800.0]][:limit],
    }


def top_customers(posting_date_from: str, posting_date_to: str, limit: int = 5) -> Dict[str, Any]:
    return {
        "columns": ["Customer", "Amount"],
        "rows": [["Acme Corp", 5000.0], ["Globex", 4200.0]][:limit],
    }


def total_outstanding_receivables() -> Dict[str, Any]:
    return {"columns": ["Metric", "Value"], "rows": [["Total Outstanding Receivables", 12345.67]]}
