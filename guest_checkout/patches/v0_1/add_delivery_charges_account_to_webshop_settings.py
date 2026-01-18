import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

def execute():
    # Add Delivery Charges Account to Webshop Settings
    create_custom_field(
        "Webshop Settings",
        {
            "fieldname": "delivery_charges_account",
            "label": "Delivery Charges Account",
            "fieldtype": "Link",
            "options": "Account",
            "insert_after": "payment_gateway_account",
            "depends_on": "eval:doc.enable_checkout === 1"
        },
    )
