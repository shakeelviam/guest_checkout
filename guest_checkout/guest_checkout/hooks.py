# guest_checkout/hooks.py
app_name = "guest_checkout"
app_title = "Guest Checkout"
app_publisher = "Your Name"
app_description = "Facilitates guest checkout functionality for Webshop."
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "your.email@example.com"
app_license = "MIT"

patches = ["guest_checkout.patches.v0_1.add_delivery_charges_account_to_webshop_settings"]

# Includes in <head>
# ------------------

# Include JS files for both desk and web
app_include_js = "/assets/guest_checkout/js/guest_checkout_shopping_cart.js"

# IMPORTANT: Add web-specific JS for guest checkout functionality
web_include_js = [
    "/assets/guest_checkout/js/guest_checkout.js",
    "/assets/guest_checkout/js/guest_login_modal.js",
    "/assets/guest_checkout/js/guest_checkout_form.js"
]

# Jinja Context
# -------------
website_context = {
    "webshop.webshop.shopping_cart.cart": [
        "guest_checkout.guest_cart.get_delivery_areas_for_context"
    ]
}

# Scheduled Tasks
# ---------------
# Daily cleanup of old guest quotations (older than 7 days)
scheduler_events = {
    "daily": [
        "guest_checkout.guest_cart.cleanup_guest_quotations"
    ]
}

# Overriding Methods
# --------------------
# Override standard webshop methods to support guest checkout
override_whitelisted_methods = {
    "webshop.webshop.shopping_cart.cart.get_party": "guest_checkout.guest_cart.get_guest_party",
    "webshop.webshop.shopping_cart.cart.get_cart_quotation": "guest_checkout.guest_cart.get_cart_quotation_allow_guest",
    "webshop.webshop.shopping_cart.cart.update_cart": "guest_checkout.guest_cart.update_cart_allow_guest",
    "webshop.webshop.shopping_cart.cart.set_cart_count": "guest_checkout.guest_cart.set_cart_count_allow_guest"
}

# Fixtures
# --------
# Export custom fields for easy installation
fixtures = [
    {
        "dt": "Custom Field",
        "filters": [
            [
                "name",
                "in",
                [
                    "Customer-guest_checkout"
                ]
            ]
        ]
    }
]
