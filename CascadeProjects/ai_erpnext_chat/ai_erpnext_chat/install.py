from __future__ import annotations
import subprocess
import os

import frappe


def after_install():
    """Skeleton: attempt to record default AI Settings and hint running installer.
    Full implementation should run scripts/install_ai_backend.sh with privileges.
    """
    try:
        # Create or update single doctype defaults
        doc = frappe.get_single("AI Settings")  # type: ignore
        if not doc.server_port:
            doc.server_port = 8081
        if not doc.ctx_size:
            doc.ctx_size = 2048
        if not doc.n_predict:
            doc.n_predict = 700
        if doc.use_local is None:
            doc.use_local = 1
        doc.save(ignore_permissions=True)  # type: ignore
    except Exception:
        frappe.log_error("AI Settings creation failed (skeleton)", "ai_erpnext_chat.install")  # type: ignore

    # Log a message for admins
    frappe.msgprint(
        "ai_erpnext_chat installed (skeleton). Run scripts/install_ai_backend.sh on the server to set up llama-server.",
        alert=True,
    )
