import frappe
from frappe import _

@frappe.whitelist(allow_guest=True)
def create_guest_sales_order(guest_data, cart_items):
    """
    Guest checkout for SA7BA website.
    Uses mobile number as unique identifier.
    Delivery Area doctype fields: area_name, delivery_charges
    """
    try:
        frappe.flags.ignore_permissions = True

        # 1. VALIDATE INPUT
        if not guest_data.get("phone"):
            frappe.throw(_("Mobile number is required."))
        if not guest_data.get("email"):
            frappe.throw(_("Email is required."))
        if not guest_data.get("delivery_area"):
            frappe.throw(_("Please select delivery area (Jabriya/Hawally)."))

        # 2. GET/CREATE CUSTOMER BY MOBILE
        mobile = guest_data.get("phone").strip()
        customer = get_or_create_customer_by_mobile(mobile, guest_data)
        
        # 3. CREATE/UPDATE CONTACT AND ADDRESS
        create_or_update_contact(customer.name, guest_data)

        # 4. CREATE SALES ORDER WITH DELIVERY CHARGES
        sales_order = create_sales_order(customer.name, cart_items, guest_data)
        frappe.db.commit()

        # 5. RETURN SUCCESS
        return {
            "success": True,
            "message": _("Order placed successfully. Order #{}").format(sales_order.name),
            "sales_order": sales_order.name,
            "order_total": sales_order.grand_total,
            "customer": customer.customer_name,
            "customer_mobile": mobile,
            "delivery_area": guest_data.get("delivery_area"),
            "delivery_charge": get_delivery_charge(guest_data.get("delivery_area"))
        }

    except Exception as e:
        frappe.db.rollback()
        return {"success": False, "message": str(e)}
    finally:
        frappe.flags.ignore_permissions = False


# --- HELPER FUNCTIONS ---
def get_or_create_customer_by_mobile(mobile, data):
    """
    Find customer by mobile number, or create new one.
    Uses the actual name from the guest form.
    """
    clean_mobile = ''.join(filter(str.isdigit, mobile))
    
    # Try to find existing customer by mobile number
    customer_name = frappe.db.get_value("Customer", 
                                       {"mobile_no": clean_mobile}, 
                                       "name")
    
    if customer_name:
        customer = frappe.get_doc("Customer", customer_name)
        # Update name if provided and different
        if data.get("full_name") and data.get("full_name") != customer.customer_name:
            customer.customer_name = data.get("full_name")
            customer.save(ignore_permissions=True)
        return customer
    
    # CREATE NEW CUSTOMER
    cust = frappe.new_doc("Customer")
    cust.customer_name = data.get("full_name") or f"Customer-{clean_mobile[-4:]}"
    cust.customer_type = "Individual"
    cust.mobile_no = clean_mobile
    cust.email_id = data.get("email", "")
    
    cust.insert(ignore_permissions=True)
    return cust


def create_or_update_contact(customer_name, data):
    """
    Create contact for customer with address.
    """
    email = data.get("email", "").strip().lower()
    mobile = data.get("phone", "").strip()
    clean_mobile = ''.join(filter(str.isdigit, mobile))
    delivery_area = data.get("delivery_area", "")
    
    # Create contact
    contact = frappe.new_doc("Contact")
    
    if data.get("full_name"):
        parts = data.get("full_name").split(' ', 1)
        contact.first_name = parts[0]
        contact.last_name = parts[1] if len(parts) > 1 else ""
    else:
        contact.first_name = "Customer"
    
    # Add email
    if email:
        contact.append("email_ids", {
            "email_id": email,
            "is_primary": 1
        })
    
    # Add mobile
    if clean_mobile:
        contact.append("phone_nos", {
            "phone": clean_mobile,
            "is_primary_phone": 1
        })
    
    # Link to customer
    contact.append("links", {
        "link_doctype": "Customer",
        "link_name": customer_name
    })
    
    contact.insert(ignore_permissions=True)
    
    # Create address using delivery area
    create_address(customer_name, contact.name, data)


def create_address(customer_name, contact_name, data):
    """
    Create address with delivery area as city.
    """
    address_line1 = data.get("shipping_address", {}).get("address_line1", "")
    delivery_area = data.get("delivery_area", "")
    
    if not address_line1:
        address_line1 = f"Delivery to {delivery_area}" if delivery_area else "Address"
    
    addr = frappe.new_doc("Address")
    addr.address_line1 = address_line1
    
    # Use delivery area as city (Jabriya/Hawally)
    if delivery_area:
        addr.city = delivery_area
    
    addr.address_type = "Shipping"
    addr.is_primary_address = 1
    
    # Link to customer
    addr.append("links", {
        "link_doctype": "Customer",
        "link_name": customer_name
    })
    
    # Link to contact
    if contact_name:
        addr.append("links", {
            "link_doctype": "Contact",
            "link_name": contact_name
        })
    
    addr.insert(ignore_permissions=True)


def get_delivery_charge(area_name):
    """
    Fetch delivery charge from Delivery Area doctype.
    Fields: area_name, delivery_charges
    """
    if not area_name:
        return 0
    
    # Get delivery charge by area_name
    charge = frappe.db.get_value("Delivery Area", 
                                {"area_name": area_name}, 
                                "delivery_charges")
    
    return float(charge) if charge else 0


def get_actual_item_code(website_item_code):
    """
    Convert Website Item code to actual Item code.
    """
    actual_item_code = frappe.db.get_value("Website Item", 
                                          website_item_code, 
                                          "item_code")
    return actual_item_code or website_item_code


def create_sales_order(customer_name, cart_items, data):
    """
    Create Sales Order with delivery charges.
    """
    so = frappe.new_doc("Sales Order")
    so.customer = customer_name
    so.order_type = "Sales"
    so.delivery_date = frappe.utils.add_days(frappe.utils.nowdate(), 7)
    
    # Add cart items
    for item in cart_items:
        actual_item_code = get_actual_item_code(item.get("item_code"))
        so.append("items", {
            "item_code": actual_item_code,
            "qty": item.get("qty"),
            "rate": item.get("rate")
        })
    
    # Add delivery charge based on selected area
    delivery_area = data.get("delivery_area")
    delivery_charge = get_delivery_charge(delivery_area)
    
    if delivery_charge > 0:
        so.append("items", {
            "item_code": "Delivery Charges",  # Your service item code
            "qty": 1,
            "rate": delivery_charge,
            "description": f"Delivery to {delivery_area}",
            "item_name": f"Delivery Charges ({delivery_area})"
        })
    else:
        # If area not found or charge is 0, add note but no charge
        so.notes = f"Note: No delivery charge applied for {delivery_area}"
    
    so.insert(ignore_permissions=True)
    so.submit()
    return so
