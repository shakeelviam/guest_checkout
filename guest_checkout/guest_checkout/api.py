# guest_checkout/guest_checkout/api.py
import frappe
from frappe.utils import get_fullname
from frappe.contacts.doctype.address.address import get_address_display

@frappe.whitelist(allow_guest=True)
def create_customer_and_link_cart(guest_details):
    """
    Creates a new Customer or retrieves an existing one based on guest details,
    then links the current guest cart to this customer.
    Guest details should include: { "full_name", "email", "mobile_no", "address_list" }
    """
    guest_details = frappe.parse_json(guest_details)
    full_name = guest_details.get("full_name")
    email = guest_details.get("email")
    mobile_no = guest_details.get("mobile_no")
    address_list = guest_details.get("address_list") # List of address dicts

    if not all([full_name, email, mobile_no]):
        frappe.throw("Full Name, Email, and Mobile Number are required.")

    # 1. Find or Create Customer
    customer = None
    contact = None
    
    # Try to find an existing contact by email
    contact_name = frappe.db.get_value("Contact", {"email_id": email})
    if contact_name:
        contact = frappe.get_doc("Contact", contact_name)
        # Check if this contact is linked to a customer
        for link in contact.links:
            if link.link_doctype == "Customer":
                customer = frappe.get_doc("Customer", link.link_name)
                break

    if not customer:
        # If no customer linked to contact, or no contact found, try to find customer directly by email
        customer_name = frappe.db.get_value("Customer", {"email_id": email}) # Assuming email_id custom field on customer
        if customer_name:
             customer = frappe.get_doc("Customer", customer_name)

    if not customer:
        # Create new Customer
        customer = frappe.new_doc("Customer")
        customer.customer_name = full_name
        customer.customer_type = "Individual"
        customer.email_id = email # Assuming email_id custom field exists on Customer
        customer.mobile_no = mobile_no # Assuming mobile_no custom field exists on Customer
        customer.customer_group = frappe.db.get_single_value("Webshop Settings", "default_customer_group")
        customer.territory = frappe.utils.nestedset.get_root_of("Territory")
        customer.flags.ignore_mandatory = True
        customer.insert(ignore_permissions=True)

    if not contact:
        # Create new Contact or update existing one if found but not linked to customer
        contact = frappe.new_doc("Contact")
        contact.first_name = full_name
        contact.email_ids = [{"email_id": email, "is_primary": 1}]
        contact.append("links", dict(link_doctype="Customer", link_name=customer.name))
        contact.mobile_no = mobile_no
        contact.flags.ignore_mandatory = True
        contact.insert(ignore_permissions=True)
    elif customer.name not in [link.link_name for link in contact.links if link.link_doctype == "Customer"]:
        contact.append("links", dict(link_doctype="Customer", link_name=customer.name))
        contact.save(ignore_permissions=True)
    
    # 2. Add/Update Addresses
    for addr_data in address_list:
        address = frappe.new_doc("Address")
        address.update(addr_data)
        address.add_link("Customer", customer.name)
        address.flags.ignore_mandatory = True
        address.insert(ignore_permissions=True)
        
    # 3. Link Guest Cart to new/existing Customer
    from guest_checkout.guest_cart import _get_cart_quotation_for_guest_or_user, get_guest_id
    
    guest_party = frappe._dict({
        "doctype": "Customer",
        "name": f"GUEST-{get_guest_id()}",
        "is_guest": True
    })
    
    guest_quotation = _get_cart_quotation_for_guest_or_user(guest_party)
    
    if guest_quotation:
        # Update party details on the quotation
        guest_quotation.quotation_to = "Customer"
        guest_quotation.party_name = customer.name
        guest_quotation.customer = customer.name
        guest_quotation.customer_name = customer.customer_name
        guest_quotation.contact_person = contact.name if contact else None
        guest_quotation.contact_email = email
        guest_quotation.email_id = email
        guest_quotation.mobile_no = mobile_no # Assuming mobile_no on quotation if needed

        # Re-apply cart settings to update pricing/taxes based on customer
        from webshop.webshop.shopping_cart.cart import apply_cart_settings
        apply_cart_settings(customer, guest_quotation)
        
        guest_quotation.flags.ignore_permissions = True
        guest_quotation.save()
        
        # Clear guest_id from session as cart is now linked to a real customer
        if frappe.session.get("guest_id"):
            del frappe.session["guest_id"]

        return customer.name
    
    return None

@frappe.whitelist(allow_guest=True)
def apply_delivery_charges_to_cart(delivery_area_name, quotation_name=None):
    """
    Applies delivery charges from the selected Delivery Area to the specified quotation (cart).
    """
    if not delivery_area_name:
        frappe.throw("Delivery Area is required.")

    delivery_area = frappe.get_doc("Delivery Area", delivery_area_name)
    delivery_charge = delivery_area.delivery_charge

    from guest_checkout.guest_cart import _get_cart_quotation_for_guest_or_user

    quotation = None
    if quotation_name:
        quotation = frappe.get_doc("Quotation", quotation_name)
    else:
        quotation = _get_cart_quotation_for_guest_or_user()

    if not quotation:
        frappe.throw("Could not find an active shopping cart.")

    # Remove any existing delivery charges
    quotation.set("taxes_and_charges", []) # Clear existing
    
    # Add Delivery Charges as a Freight and Charges row
    # This assumes 'Freight and Charges' doctype and setup
    # Or, if preferred, can add a custom item to the quotation items directly.
    
    # Check if delivery_charges_account is set in Webshop Settings
    webshop_settings = frappe.get_cached_doc("Webshop Settings")
    delivery_charges_account = webshop_settings.delivery_charges_account

    if not delivery_charges_account:
        frappe.throw("Delivery Charges Account not set in Webshop Settings. Please configure it.")

    # Create a new row in Taxes and Charges for delivery
    quotation.append(
        "taxes_and_charges",
        {
            "charge_type": "Actual",
            "account_head": delivery_charges_account,
            "description": f"Delivery Charges - {delivery_area_name}",
            "amount": delivery_charge,
            "add_deduct_tax": "Add",
            "included_in_print_rate": 0,
            "tax_amount": 0 # Assuming delivery charge is not taxable here, adjust if needed
        }
    )
    
    quotation.run_method("calculate_taxes_and_totals")
    quotation.flags.ignore_permissions = True
    quotation.save()
    
    return quotation.name