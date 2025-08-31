from __future__ import annotations
import json
from typing import Optional, Dict, Any

import frappe


@frappe.whitelist(methods=["POST"])  # type: ignore
def ask_ai(question: str, site_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Skeleton endpoint. Wires UI to backend and reads AI Settings.
    Replace with actual llama-server call and plan execution later.
    """
    if not question or not isinstance(question, str):
        return {"ok": False, "error": "Invalid or empty question"}

    try:
        settings = frappe.get_single("AI Settings")  # type: ignore
    except Exception:
        settings = None

    # Minimal placeholder return to keep UI functional
    return {
        "ok": True,
        "answer_markdown": (
            "This is a placeholder response from ai_erpnext_chat.api.ask_ai.\n\n"
            "• You asked: `" + frappe.safe_decode(question) + "`\n"
            "• Next step: implement llama-server call and plan execution."
        ),
        "data_table": None,
        "debug": {"settings_loaded": bool(settings)},
    }
