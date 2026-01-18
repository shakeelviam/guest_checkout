#!/usr/bin/env python
# Test script for guest checkout functionality

import frappe
import unittest
import json
from frappe.tests.utils import FrappeTestCase

class TestGuestCheckoutFunctionality(FrappeTestCase):
    def setUp(self):
        # Set up test environment
        print("Setting up test environment...")
        frappe.set_user("Guest")
        
        # Create a test item if it doesn't exist
        if not frappe.db.exists("Item", "Test Guest Checkout Item"):
            print("Creating test item...")
            test_item = frappe.get_doc({
                "doctype": "Item",
                "item_code": "Test Guest Checkout Item",
                "item_name": "Test Guest Checkout Item",
                "item_group": "All Item Groups",
                "stock_uom": "Nos",
                "is_stock_item": 1,
                "standard_rate": 100
            })
            test_item.insert(ignore_permissions=True)

        # Create a delivery area if it doesn't exist
        if not frappe.db.exists("Delivery Area", "Test Area"):
            print("Creating test delivery area...")
            delivery_area = frappe.get_doc({
                "doctype": "Delivery Area",
                "area": "Test Area",
                "delivery_charge": 10.0
            })
            delivery_area.insert(ignore_permissions=True)

    def test_guest_checkout_flow(self):
        from guest_checkout.guest_cart import (
            get_guest_id, 
            get_guest_party, 
            update_cart_allow_guest,
            complete_guest_checkout
        )
        
        print("Testing guest checkout flow...")
        
        # 1. Get a guest ID and party
        guest_id = get_guest_id()
        party = get_guest_party()
        
        print(f"Guest ID: {guest_id}")
        print(f"Guest Party: {party.name}")
        self.assertTrue(hasattr(party, "is_guest"))
        
        # 2. Add item to cart
        update_cart_allow_guest("Test Guest Checkout Item", 1)
        print("Added item to cart")
        
        # 3. Prepare checkout data
        guest_data = {
            "mobile": "9876543210",
            "email": "test@example.com",
            "full_name": "Test Guest"
        }
        
        address_data = {
            "address_line1": "123 Test Street",
            "city": "Test City",
            "state": "Test State",
            "country": "Kuwait",
            "pincode": "12345"
        }
        
        # 4. Complete checkout
        try:
            result = complete_guest_checkout(
                guest_data=json.dumps(guest_data),
                address_data=json.dumps(address_data),
                payment_method="Bookeey",
                delivery_area="Test Area",
                delivery_charge=10.0
            )
            
            print("Checkout result:", result)
            if result and result.get("success"):
                print(f"Successfully created sales order: {result.get('sales_order')}")
                
                # Verify the customer was created with the mobile number as identifier
                customer = frappe.get_doc("Customer", result.get("customer"))
                self.assertEqual(customer.mobile_no, "9876543210")
                
                # Verify delivery charges were applied
                sales_order = frappe.get_doc("Sales Order", result.get("sales_order"))
                self.assertGreaterEqual(sales_order.grand_total, sales_order.total + 10.0)
            else:
                print("Checkout failed")
                print(result)
        except Exception as e:
            print(f"Error during checkout: {str(e)}")
            raise

    def tearDown(self):
        # Clean up after test
        print("Cleaning up...")
        frappe.set_user("Administrator")
        frappe.db.rollback()

if __name__ == "__main__":
    unittest.main()
