# guest_checkout/guest_cart.py
import frappe
from frappe import _
from frappe.utils import get_fullname, flt, cint, cstr, nowdate
from webshop.webshop.doctype.webshop_settings.webshop_settings import get_shopping_cart_settings
from frappe.utils.nestedset import get_root_of
import json


# Using a session-based approach for guest identification
def get_guest_id():
    """Generate or retrieve unique guest ID for the session"""
    if not frappe.session.get("guest_id"):
        guest_id = frappe.generate_hash(length=10)
        frappe.session["guest_id"] = guest_id
        # Also store in cookie for persistence
        if hasattr(frappe.local, "cookie_manager"):
            frappe.local.cookie_manager.set_cookie("guest_id", guest_id, expires=365*24*60*60)
    return frappe.session["guest_id"]


def get_guest_party(user=None, mobile_no=None, email=None, full_name=None):
    """Get party object for guest or logged-in user - creates actual Customer for guests
    
    Args:
        user (str, optional): User email. Defaults to None.
        mobile_no (str, optional): Mobile number for guest user. Defaults to None.
        email (str, optional): Email for guest user. Defaults to None.
        full_name (str, optional): Full name for guest user. Defaults to None.
    
    Returns:
        Customer: Customer document with is_guest flag set if guest
    """
    if not user:
        user = frappe.session.user

    if user == "Guest":
        # For initial cart functionality, we still need a session ID
        guest_id = get_guest_id()
        
        # Check if we're in the final checkout stage with customer information
        if mobile_no and email and full_name:
            # First check if customer exists with this mobile number
            existing_customer = frappe.db.get_value(
                "Customer",
                {"mobile_no": mobile_no},
                "name"
            )
            
            if existing_customer:
                # Customer exists, update email and name if needed
                customer = frappe.get_doc("Customer", existing_customer)
                # Update email if different
                if customer.email_id != email:
                    customer.email_id = email
                    customer.flags.ignore_permissions = True
                    customer.save()
            else:
                # Create new customer with mobile as unique identifier
                customer = frappe.get_doc({
                    "doctype": "Customer",
                    "customer_name": full_name,
                    "mobile_no": mobile_no,
                    "email_id": email,
                    "customer_type": "Individual",
                    "customer_group": frappe.db.get_single_value("Selling Settings", "customer_group") or "Individual",
                    "territory": get_root_of("Territory"),
                    "disabled": 0
                })
                customer.flags.ignore_permissions = True
                customer.flags.ignore_mandatory = True
                customer.insert(ignore_permissions=True)
                frappe.db.commit()
                
            party = customer
            party.is_guest = False  # This is a real customer now
            return party
        else:
            # Initial stage - create temporary session-based cart
            # We'll use a session identifier in the name but won't save to DB yet
            party = frappe._dict({
                "doctype": "Customer",
                "name": f"TMP-{guest_id}",  # Temporary reference, not saved to DB
                "customer_name": f"Guest User {guest_id[:6]}",
                "is_guest": True
            })
            return party
    else:
        # Fallback to original get_party for logged-in users
        from webshop.webshop.shopping_cart.cart import get_party as original_get_party
        party = original_get_party(user)
        if party:
            party.is_guest = False
        return party


@frappe.whitelist(allow_guest=True)
def get_cart_quotation_allow_guest(doc=None):
    """Get cart quotation for both guest and logged-in users"""
    party = get_guest_party()

    if not doc:
        quotation = _get_cart_quotation_for_guest_or_user(party)
        doc = quotation
        set_cart_count_allow_guest(quotation)

    # Ensure addresses are fetched correctly for guests as well
    addresses = []
    shipping_addresses = []
    billing_addresses = []
    
    if not getattr(party, "is_guest", False):
        from webshop.webshop.shopping_cart.cart import get_address_docs, get_shipping_addresses, get_billing_addresses
        addresses = get_address_docs(party=party)
        shipping_addresses = get_shipping_addresses(party)
        billing_addresses = get_billing_addresses(party)
        
        if doc and not doc.customer_address and addresses:
            from webshop.webshop.shopping_cart.cart import update_cart_address
            update_cart_address("billing", addresses[0].name)

    from webshop.webshop.shopping_cart.cart import decorate_quotation_doc
    return {
        "doc": decorate_quotation_doc(doc),
        "shipping_addresses": shipping_addresses,
        "billing_addresses": billing_addresses,
        "shipping_rules": [],
        "cart_settings": frappe.get_cached_doc("Webshop Settings"),
    }


@frappe.whitelist(allow_guest=True)
def update_cart_allow_guest(item_code, qty, additional_notes=None, with_items=False):
    """Update cart for both guest and logged-in users"""
    party = get_guest_party()
    quotation = _get_cart_quotation_for_guest_or_user(party)

    empty_card = False
    qty = flt(qty)
    
    if qty == 0:
        quotation_items = quotation.get("items", {"item_code": ["!=", item_code]})
        if quotation_items:
            quotation.set("items", quotation_items)
        else:
            empty_card = True
    else:
        warehouse = frappe.get_cached_value(
            "Website Item", {"item_code": item_code}, "website_warehouse"
        )

        quotation_items = quotation.get("items", {"item_code": item_code})
        if not quotation_items:
            quotation.append(
                "items",
                {
                    "doctype": "Quotation Item",
                    "item_code": item_code,
                    "qty": qty,
                    "additional_notes": additional_notes,
                    "warehouse": warehouse,
                },
            )
        else:
            quotation_items[0].qty = qty
            quotation_items[0].warehouse = warehouse
            quotation_items[0].additional_notes = additional_notes

    # Apply cart settings for both guests and users
    from webshop.webshop.shopping_cart.cart import apply_cart_settings
    apply_cart_settings(party, quotation)

    quotation.flags.ignore_permissions = True
    quotation.payment_schedule = []
    
    if not empty_card:
        quotation.save()
    else:
        quotation.delete()
        quotation = None

    set_cart_count_allow_guest(quotation)

    if cint(with_items):
        context = get_cart_quotation_allow_guest(quotation)
        return {
            "items": frappe.render_template(
                "templates/includes/cart/cart_items.html", context
            ),
            "total": frappe.render_template(
                "templates/includes/cart/cart_items_total.html", context
            ),
            "taxes_and_totals": frappe.render_template(
                "templates/includes/cart/cart_payment_summary.html", context
            ),
        }
    else:
        return {
            "name": quotation.name if quotation else None,
            "shopping_cart_menu": get_shopping_cart_menu(quotation)
        }


def set_cart_count_allow_guest(quotation=None):
    """Set cart count in cookie for both guest and logged-in users"""
    from webshop.webshop.doctype.webshop_settings.webshop_settings import get_shopping_cart_settings

    if cint(get_shopping_cart_settings().enabled):
        if not quotation:
            quotation = _get_cart_quotation_for_guest_or_user()

        cart_count = cstr(cint(quotation.get("total_qty"))) if quotation else "0"

        if hasattr(frappe.local, "cookie_manager"):
            frappe.local.cookie_manager.set_cookie("cart_count", cart_count)


def _get_cart_quotation_for_guest_or_user(party=None):
    """Return the open Quotation of type Shopping Cart or make a new one"""
    if not party:
        party = get_guest_party()

    quotation = None
    
    # Handle true guest users differently (temporary party with no DB record)
    if getattr(party, "is_guest", False) and party.name.startswith("TMP-"):
        # Check for guest quotation in session
        quotation_name = frappe.session.get("guest_quotation_name")
        
        if quotation_name and frappe.db.exists("Quotation", quotation_name):
            quotation = frappe.get_doc("Quotation", quotation_name)
            # Make sure it's still a draft shopping cart
            if quotation.docstatus != 0 or quotation.order_type != "Shopping Cart":
                quotation = None
    else:
        # For registered users or guests with finalized customer details,
        # use normal quotation lookup
        quotation_name = frappe.db.get_value(
            "Quotation",
            filters={
                "party_name": party.name,
                "order_type": "Shopping Cart",
                "docstatus": 0,
            },
            order_by="modified desc",
        )
        
        if quotation_name:
            quotation = frappe.get_doc("Quotation", quotation_name)
    
    # Create new quotation if none exists
    if not quotation:
        company = frappe.db.get_single_value("Webshop Settings", "company")
        
        # Create new quotation
        qdoc = frappe.get_doc({
            "doctype": "Quotation",
            "naming_series": get_shopping_cart_settings().quotation_series or "QTN-CART-",
            "quotation_to": "Customer",
            "company": company,
            "order_type": "Shopping Cart",
            "status": "Draft",
            "docstatus": 0,
            "__islocal": 1,
            "party_name": party.name if not getattr(party, "is_guest", False) else None,
            "contact_email": frappe.session.user if frappe.session.user != "Guest" else ""
        })

        # Only set contact person for logged-in users
        if not getattr(party, "is_guest", False):
            qdoc.contact_person = frappe.db.get_value(
                "Contact", {"email_id": frappe.session.user}
            )

        qdoc.flags.ignore_permissions = True
        qdoc.run_method("set_missing_values")
        
        # Apply cart settings
        from webshop.webshop.shopping_cart.cart import apply_cart_settings
        apply_cart_settings(party, qdoc)
        
        quotation = qdoc
        
        # For guests, save quotation reference in session
        if getattr(party, "is_guest", False) and quotation.name:
            frappe.session["guest_quotation_name"] = quotation.name

    return quotation


@frappe.whitelist(allow_guest=True)
def get_shopping_cart_menu(quotation=None):
    """Get shopping cart menu data for navbar"""
    if not quotation:
        quotation = _get_cart_quotation_for_guest_or_user()
    
    if not quotation:
        return {
            "cart_count": 0,
            "cart_items": [],
            "total": 0
        }
    
    items = []
    for item in quotation.items:
        items.append({
            "item_code": item.item_code,
            "item_name": item.item_name,
            "qty": item.qty,
            "rate": item.rate,
            "amount": item.amount,
            "image": frappe.db.get_value("Item", item.item_code, "image")
        })
    
    return {
        "cart_count": cint(quotation.total_qty),
        "cart_items": items,
        "total": quotation.grand_total if quotation.grand_total else 0
    }


@frappe.whitelist(allow_guest=True)
def complete_guest_checkout(guest_data, address_data, payment_method="Bookeey", delivery_area=None, delivery_charge=0):
    """
    Complete checkout for guest user with delivery area support
    Creates or updates Customer with provided information and converts Quotation to Sales Order
    
    Args:
        guest_data: JSON string with {mobile, email, full_name}
        address_data: JSON string with {address_line1, city, state, country, pincode, phone}
        payment_method: Payment method (default: Bookeey)
        delivery_area: Delivery Area name from Delivery Area doctype
        delivery_charge: Delivery charge amount
    """
    try:
        # Parse JSON data
        if isinstance(guest_data, str):
            guest_data = json.loads(guest_data)
        if isinstance(address_data, str):
            address_data = json.loads(address_data)
        
        # Validate required fields
        required_guest_fields = ['mobile', 'email', 'full_name']
        for field in required_guest_fields:
            if not guest_data.get(field):
                frappe.throw(_("Missing required field: {0}").format(field))
        
        required_address_fields = ['address_line1', 'city', 'country']
        for field in required_address_fields:
            if not address_data.get(field):
                frappe.throw(_("Missing required address field: {0}").format(field))
        
        # Get guest quotation using the session
        quotation = None
        quotation_name = frappe.session.get("guest_quotation_name")
        if quotation_name:
            quotation = frappe.get_doc("Quotation", quotation_name) if frappe.db.exists("Quotation", quotation_name) else None
        
        if not quotation or not quotation.items:
            frappe.throw(_("Cart is empty"))
        
        # Get or create customer using mobile number as primary identifier
        party = get_guest_party(
            mobile_no=guest_data['mobile'], 
            email=guest_data['email'], 
            full_name=guest_data['full_name']
        )
        
        customer_name = party.name
        
        # Create or update address
        address = create_or_update_address(customer_name, address_data)
        
        # Update quotation with real customer info
        quotation.party_name = customer_name
        quotation.customer_name = guest_data['full_name']
        quotation.contact_email = guest_data['email']
        quotation.contact_mobile = guest_data['mobile']
        quotation.customer_address = address.name
        quotation.address_display = address.get_display()
        quotation.shipping_address_name = address.name
        quotation.shipping_address = address.get_display()
        
        # Add delivery charges if provided
        if delivery_area and flt(delivery_charge) > 0:
            # Get delivery area details
            delivery_area_doc = frappe.get_doc("Delivery Area", delivery_area)
            
            # Check webshop settings for delivery charges account
            webshop_settings = frappe.get_cached_doc("Webshop Settings")
            delivery_charges_account = webshop_settings.get("delivery_charges_account")
            
            if delivery_charges_account:
                # Remove existing delivery charges if any
                existing_taxes = []
                for tax in quotation.get("taxes", []):
                    if "Delivery Charges" not in tax.description:
                        existing_taxes.append(tax)
                
                quotation.taxes = existing_taxes
                
                # Add delivery charge as tax
                quotation.append("taxes", {
                    "charge_type": "Actual",
                    "account_head": delivery_charges_account,
                    "description": f"Delivery Charges - {delivery_area_doc.area}",
                    "tax_amount": flt(delivery_charge)
                })
            else:
                # Fallback to item-based charges if tax account not set
                delivery_item_exists = False
                
                # Check if delivery charge item already exists
                for item in quotation.items:
                    if item.item_code == "Delivery Charges":
                        item.rate = flt(delivery_charge)
                        item.amount = flt(delivery_charge)
                        delivery_item_exists = True
                        break
                
                if not delivery_item_exists and frappe.db.exists("Item", "Delivery Charges"):
                    quotation.append("items", {
                        "item_code": "Delivery Charges",
                        "item_name": f"Delivery Charges - {delivery_area_doc.area}",
                        "description": f"Delivery to {delivery_area_doc.area}",
                        "qty": 1,
                        "rate": flt(delivery_charge),
                        "amount": flt(delivery_charge)
                    })
        
        # Apply cart settings with real customer
        real_party = frappe.get_doc("Customer", customer_name)
        from webshop.webshop.shopping_cart.cart import apply_cart_settings
        apply_cart_settings(real_party, quotation)
        
        quotation.flags.ignore_permissions = True
        quotation.save()
        
        # Submit quotation
        quotation.submit()
        
        # Create Sales Order from Quotation
        from erpnext.selling.doctype.quotation.quotation import _make_sales_order
        sales_order = frappe.get_doc(_make_sales_order(quotation.name))
        sales_order.customer = customer_name
        sales_order.customer_name = guest_data['full_name']
        sales_order.contact_email = guest_data['email']
        sales_order.contact_mobile = guest_data['mobile']
        sales_order.customer_address = address.name
        sales_order.address_display = address.get_display()
        sales_order.shipping_address_name = address.name
        sales_order.shipping_address = address.get_display()
        
        # Add delivery area if custom field exists
        if delivery_area and frappe.db.exists("Custom Field", {"dt": "Sales Order", "fieldname": "delivery_area"}):
            sales_order.set("delivery_area", delivery_area)
        
        sales_order.flags.ignore_permissions = True
        sales_order.insert(ignore_permissions=True)
        sales_order.submit()
        
        # Create Payment Entry
        payment_entry = create_payment_entry(sales_order, payment_method)
        
        # Clear guest session
        if frappe.session.get("guest_id"):
            frappe.session.pop("guest_id")
        
        set_cart_count_allow_guest(None)
        
        return {
            "success": True,
            "customer": customer_name,
            "sales_order": sales_order.name,
            "payment_entry": payment_entry.name if payment_entry else None,
            "grand_total": sales_order.grand_total,
            "delivery_charge": delivery_charge,
            "delivery_area": delivery_area,
            "message": _("Order placed successfully!")
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Guest Checkout Error")
        frappe.throw(_("Checkout failed: {0}").format(str(e)))


def create_or_update_address(customer_name, address_data):
    """Create or update address for customer"""
    existing_address = frappe.db.get_value(
        "Address",
        {
            "address_line1": address_data['address_line1'],
            "city": address_data['city'],
            "pincode": address_data.get('pincode')
        },
        "name"
    )
    
    if existing_address:
        address = frappe.get_doc("Address", existing_address)
        if not any(link.link_doctype == "Customer" and link.link_name == customer_name for link in address.links):
            address.append("links", {
                "link_doctype": "Customer",
                "link_name": customer_name
            })
            address.flags.ignore_permissions = True
            address.save()
    else:
        address = frappe.get_doc({
            "doctype": "Address",
            "address_title": customer_name,
            "address_type": "Billing",
            "address_line1": address_data['address_line1'],
            "address_line2": address_data.get('address_line2', ''),
            "city": address_data['city'],
            "state": address_data.get('state', ''),
            "country": address_data['country'],
            "pincode": address_data.get('pincode', ''),
            "phone": address_data.get('phone', ''),
            "email_id": address_data.get('email', ''),
            "links": [{
                "link_doctype": "Customer",
                "link_name": customer_name
            }]
        })
        address.flags.ignore_permissions = True
        address.insert(ignore_permissions=True)
    
    return address


def create_payment_entry(sales_order, payment_method="Bookeey"):
    """Create payment entry for sales order"""
    try:
        payment_gateway_account = frappe.db.get_value(
            "Payment Gateway Account",
            {"payment_gateway": payment_method},
            ["name", "payment_account"]
        )
        
        if not payment_gateway_account:
            frappe.log_error(f"Payment Gateway Account not found for {payment_method}", "Payment Entry Creation")
            return None
        
        from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
        payment_entry = get_payment_entry("Sales Order", sales_order.name)
        payment_entry.mode_of_payment = payment_method
        payment_entry.paid_amount = sales_order.grand_total
        payment_entry.received_amount = sales_order.grand_total
        
        payment_entry.flags.ignore_permissions = True
        payment_entry.insert(ignore_permissions=True)
        payment_entry.submit()
        
        return payment_entry
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Payment Entry Creation Error")
        return None


def cleanup_guest_quotations():
    """Delete abandoned guest quotations and customers older than 7 days"""
    from frappe.utils import add_days
    
    old_date = add_days(nowdate(), -7)
    
    # Delete old guest quotations
    guest_quotations = frappe.get_all(
        "Quotation",
        filters={
            "modified": ["<", old_date],
            "docstatus": 0,
            "party_name": ["in", frappe.get_all("Customer", {"guest_checkout": 1}, pluck="name")]
        },
        pluck="name"
    )
    
    for quotation_name in guest_quotations:
        try:
            frappe.delete_doc("Quotation", quotation_name, force=1, ignore_permissions=True)
        except Exception as e:
            frappe.log_error(f"Error deleting quotation {quotation_name}: {str(e)}", "Guest Quotation Cleanup")
    
    # Delete old temporary guest customers (no orders)
    guest_customers = frappe.get_all(
        "Customer",
        filters={
            "modified": ["<", old_date],
            "guest_checkout": 1
        },
        pluck="name"
    )
    
    for customer_name in guest_customers:
        try:
            # Only delete if no sales orders exist
            has_orders = frappe.db.exists("Sales Order", {"customer": customer_name})
            if not has_orders:
                frappe.delete_doc("Customer", customer_name, force=1, ignore_permissions=True)
        except Exception as e:
            frappe.log_error(f"Error deleting customer {customer_name}: {str(e)}", "Guest Customer Cleanup")
    
    frappe.db.commit()
    
    if guest_quotations or guest_customers:
        frappe.logger().info(f"Cleaned up {len(guest_quotations)} quotations and {len(guest_customers)} guest customers")


def get_delivery_areas_for_context(context):
    """Add delivery areas to context for guest checkout form"""
    if frappe.session.user == "Guest":
        context.delivery_areas = frappe.get_all("Delivery Area", fields=["name", "area", "delivery_charge"])
