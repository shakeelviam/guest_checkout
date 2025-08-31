/* global frappe */
(function () {
  function whenToolbarReady(cb, tries = 40) {
    if (window.frappe && frappe.ui && frappe.ui.toolbar) { cb(); return; }
    if (tries <= 0) return;
    setTimeout(() => whenToolbarReady(cb, tries - 1), 250);
  }

  document.addEventListener("DOMContentLoaded", () => {
    whenToolbarReady(() => {
      try {
        if (frappe.ui.toolbar && frappe.ui.toolbar.add_dropdown_item) {
          frappe.ui.toolbar.add_dropdown_item("Help", __("Ask ERPNext (AI)"), () => open_ai_dialog());
        } else if (frappe.toolbar && frappe.toolbar.add_menu_item) {
          frappe.toolbar.add_menu_item("Ask ERPNext (AI)", () => open_ai_dialog());
        }
      } catch (e) {}
    });
  });

  function open_ai_dialog() {
    const d = new frappe.ui.Dialog({
      title: "Ask ERPNext (AI)",
      fields: [{ label: "Question", fieldname: "question", fieldtype: "Small Text", reqd: 1 }],
      primary_action_label: "Ask",
      primary_action: (values) => {
        if (!values || !values.question) return;
        d.set_primary_action("Asking...");
        d.set_df_property("question", "read_only", 1);
        frappe.call({
          method: "ai_erpnext_chat.api.ask_ai",
          type: "POST",
          args: { question: values.question },
        }).then((r) => {
          const msg = (r && r.message) || {};
          const md = msg.ok ? (msg.answer_markdown || "(no content)") : (msg.error || "Request failed");
          d.set_message(`<div class="markdown" style="margin-top: 12px;">${frappe.markdown(md)}</div>`);
        }).catch(() => {
          d.set_message(`<div class="text-muted">${__("AI service error or unavailable.")}</div>`);
        }).finally(() => {
          d.set_primary_action_label("Ask");
          d.set_df_property("question", "read_only", 0);
        });
      },
    });
    d.show();
  }
})();