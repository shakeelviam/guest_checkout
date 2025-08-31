from __future__ import annotations
import frappe
from frappe.model.document import Document


class AISettings(Document):
    def validate(self):
        # Prevent edits to read-only transparency fields from UI
        ro_fields = [
            "detected_ram_gb",
            "cpu_features",
            "gpu_type",
            "chosen_model",
            "chosen_quant",
            "ngl_offload",
            "effective_ctx",
        ]
        for f in ro_fields:
            if self.get_dirty_fields().get(f):
                # revert change
                self.set(f, self.get_db_value(f))

        # Basic bounds
        if self.server_port and (self.server_port < 1024 or self.server_port > 65535):
            frappe.throw("Server Port must be between 1024 and 65535")
        if self.ctx_size and self.ctx_size < 512:
            frappe.throw("Context size too small")
        if self.n_predict and self.n_predict < 32:
            frappe.throw("n_predict too small")
