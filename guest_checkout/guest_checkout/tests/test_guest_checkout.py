# guest_checkout/guest_checkout/tests/test_guest_checkout.py
import frappe
import unittest
from frappe.testing.utils import FrappeTestCase
from guest_checkout.guest_cart import (
    get_guest_id,
    get_guest_party,
    _get_cart_quotation_for_guest_or_user,
    set_cart_count_allow_guest,
    update_cart_allow_guest
)
from guest_checkout.api import (
    create_customer_and_link_cart,
    apply_delivery_charges_to_cart
)

class TestGuestCheckout(FrappeTestCase):
    def setUp(self):
        # Ensure Webshop Settings are enabled and configured for testing
        frappe.db.set_single_value("Webshop Settings", "enabled", 1)
        frappe.db.set_single_value("Webshop Settings", "company", "_Test Company")
        frappe.db.set_single_value("Webshop Settings", "default_customer_group", "Commercial")
        
        # Create a test Account for delivery charges if it doesn't exist
        if not frappe.db.exists("Account", "Delivery Charges - _Test Company"):
            frappe.get_doc({
                "doctype": "Account",
                "company": "_Test Company",
                "account_name": "Delivery Charges",
                "account_type": "Expense",
                "root_type": "Expense",
                "is_group": 0,
            }).insert(ignore_permissions=True)
        frappe.db.set_single_value("Webshop Settings", "delivery_charges_account", "Delivery Charges - _Test Company")

        # Create a test Item and Website Item
        if not frappe.db.exists("Item", "Test Item for Guest Checkout"):
            self.item = frappe.get_doc({
                "doctype": "Item",
                "item_code": "Test Item for Guest Checkout",
                "item_name": "Test Item for Guest Checkout",
                "is_stock_item": 1,
            }).insert(ignore_permissions=True)
            self.website_item = frappe.get_doc({
                "doctype": "Website Item",
                "item_code": "Test Item for Guest Checkout",
                "website_warehouse": "Stores - _Test Company"
            }).insert(ignore_permissions=True)
        else:
            self.item = frappe.get_doc("Item", "Test Item for Guest Checkout")
            self.website_item = frappe.get_doc("Website Item", {"item_code": "Test Item for Guest Checkout"})

        # Create a test Delivery Area
        if not frappe.db.exists("Delivery Area", "Test Area"):
            self.delivery_area = frappe.get_doc({
                "doctype": "Delivery Area",
                "area": "Test Area",
                "delivery_charge": 50.00
            }).insert(ignore_permissions=True)
        else:
            self.delivery_area = frappe.get_doc("Delivery Area", "Test Area")

        # Mock frappe.session.user as Guest for guest-specific tests
        self.original_session_user = frappe.session.user
        frappe.session.user = "Guest"
        if "guest_id" in frappe.session:
            del frappe.session["guest_id"] # Clear any previous guest_id

    def tearDown(self):
        frappe.session.user = self.original_session_user
        if "guest_id" in frappe.session:
            del frappe.session["guest_id"]
        # Clean up any created Quotations, Customers, Contacts, Addresses, etc.
        frappe.db.rollback() # Rollback all changes made during the test

    def test_get_guest_id(self):
        guest_id1 = get_guest_id()
        self.assertIsNotNone(guest_id1)
        guest_id2 = get_guest_id()
        self.assertEqual(guest_id1, guest_id2) # Should return same ID for same session
        
        # Test new session
        del frappe.session["guest_id"]
        guest_id3 = get_guest_id()
        self.assertNotEqual(guest_id1, guest_id3)

    def test_get_guest_party_for_guest(self):
        party = get_guest_party()
        self.assertTrue(party.is_guest)
        self.assertEqual(party.doctype, "Customer")
        self.assertTrue(party.name.startswith("GUEST-"))
        self.assertEqual(party.customer_name, "Guest User")

    def test_get_guest_party_for_user(self):
        frappe.session.user = "test@example.com" # Mock a logged-in user
        # Need to mock frappe.get_doc("User", "test@example.com") and related
        # For simplicity, we'll just check it doesn't return a guest party
        party = get_guest_party()
        self.assertFalse(hasattr(party, "is_guest"))
        frappe.session.user = "Guest" # Reset

    def test_create_guest_quotation(self):
        quotation = _get_cart_quotation_for_guest_or_user()
        self.assertIsNotNone(quotation)
        self.assertTrue(quotation.party_name.startswith("GUEST-"))
        self.assertEqual(quotation.contact_email, "Guest")
        self.assertEqual(quotation.order_type, "Shopping Cart")
        self.assertEqual(quotation.docstatus, 0) # Draft

    def test_retrieve_existing_guest_quotation(self):
        _ = _get_cart_quotation_for_guest_or_user() # Create one
        quotation2 = _get_cart_quotation_for_guest_or_user() # Retrieve same one
        self.assertEqual(_.name, quotation2.name)

    def test_update_cart_add_item_guest(self):
        update_cart_allow_guest(self.item.item_code, 1)
        quotation = _get_cart_quotation_for_guest_or_user()
        self.assertEqual(len(quotation.items), 1)
        self.assertEqual(quotation.items[0].item_code, self.item.item_code)
        self.assertEqual(quotation.items[0].qty, 1)
        self.assertGreater(quotation.total_qty, 0)

    def test_update_cart_change_qty_guest(self):
        update_cart_allow_guest(self.item.item_code, 1)
        update_cart_allow_guest(self.item.item_code, 3)
        quotation = _get_cart_quotation_for_guest_or_user()
        self.assertEqual(quotation.items[0].qty, 3)

    def test_update_cart_remove_item_guest(self):
        update_cart_allow_guest(self.item.item_code, 1)
        quotation = _get_cart_quotation_for_guest_or_user()
        self.assertEqual(len(quotation.items), 1)
        update_cart_allow_guest(self.item.item_code, 0)
        quotation = _get_cart_quotation_for_guest_or_user()
        self.assertEqual(len(quotation.items), 0) # Item should be removed

    def test_set_cart_count_guest(self):
        update_cart_allow_guest(self.item.item_code, 2)
        set_cart_count_allow_guest()
        self.assertEqual(frappe.local.cookie_manager.get_cookie("cart_count"), "2")

    def test_create_customer_and_link_cart_new_customer(self):
        # First, add item to guest cart
        update_cart_allow_guest(self.item.item_code, 1)
        guest_quotation = _get_cart_quotation_for_guest_or_user()
        original_guest_id = get_guest_id()

        guest_details = frappe._dict({
            "full_name": "Test Guest User",
            "email": "testguest@example.com",
            "mobile_no": "1234567890",
            "address_list": [{
                "address_title": "Test Guest Address",
                "address_line1": "123 Test St",
                "city": "Testville",
                "country": "India",
                "pincode": "123456",
                "address_type": "Shipping"
            }]
        })

        customer_name = create_customer_and_link_cart(guest_details)
        self.assertIsNotNone(customer_name)
        
        customer = frappe.get_doc("Customer", customer_name)
        self.assertEqual(customer.customer_name, "Test Guest User")
        self.assertFalse("guest_id" in frappe.session) # Guest ID should be cleared

        # Verify quotation is linked
        updated_quotation = frappe.get_doc(guest_quotation.name)
        self.assertEqual(updated_quotation.customer, customer_name)
        self.assertEqual(updated_quotation.party_name, customer_name)
        self.assertEqual(updated_quotation.contact_email, "testguest@example.com")

        # Clean up created records (handled by rollback in tearDown)

    def test_apply_delivery_charges_to_cart(self):
        # Create a guest cart first
        update_cart_allow_guest(self.item.item_code, 1)
        guest_quotation = _get_cart_quotation_for_guest_or_user()
        original_grand_total = guest_quotation.grand_total

        apply_delivery_charges_to_cart(self.delivery_area.name, guest_quotation.name)
        updated_quotation = frappe.get_doc(guest_quotation.name)

        self.assertGreater(updated_quotation.grand_total, original_grand_total)
        self.assertEqual(len(updated_quotation.taxes_and_charges), 1)
        self.assertEqual(updated_quotation.taxes_and_charges[0].amount, self.delivery_area.delivery_charge)
        self.assertEqual(updated_quotation.taxes_and_charges[0].account_head, frappe.db.get_single_value("Webshop Settings", "delivery_charges_account"))
