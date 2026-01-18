import frappe
from frappe import _

@frappe.whitelist(allow_guest=True)
def get_delivery_areas():
    """Fetch delivery areas for guest checkout dropdown."""
    try:
        # Check which field exists
        field_name = None
        for field in ["delivery_charges", "delivery_charge"]:
            if frappe.db.exists("DocField", {
                "parent": "Delivery Area",
                "fieldname": field
            }):
                field_name = field
                break
        
        if not field_name:
            return {"success": True, "areas": []}
        
        # Fetch areas
        areas = frappe.get_all(
            "Delivery Area",
            filters={"disabled": 0},
            fields=["area_name", field_name],
            order_by="area_name"
        )
        
        # Format response
        formatted_areas = []
        for area in areas:
            charge = area.get(field_name, 0)
            formatted_areas.append({
                "area_name": area.area_name,
                "delivery_charge": charge,
                "delivery_charges": charge
            })
        
        return {
            "success": True,
            "areas": formatted_areas
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Delivery Areas Error")
        return {
            "success": False,
            "message": str(e),
            "areas": []
        }
