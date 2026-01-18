// guest_checkout/guest_checkout/public/js/guest_checkout_form.js
frappe.provide("guest_checkout");

guest_checkout.setup_checkout_form = function() {
    if (window.location.pathname === "/cart" && frappe.session.user === "Guest") {
        // Create standardized guest checkout form
        const checkout_form_html = `
        <div class="frappe-card p-5 mb-4" id="guest-checkout-form">
            <h4>${__("Guest Checkout")}</h4>
            <p class="text-muted">${__("Please enter your information to continue")}</p>
            <hr>
            
            <div class="row">
                <div class="col-md-6">
                    <h5>${__("Personal Information")}</h5>
                    <div class="form-group">
                        <label class="control-label" for="guest-mobile">${__("Mobile Number")} <span class="text-danger">*</span></label>
                        <input type="text" class="form-control" id="guest-mobile" required 
                            placeholder="${__('Required - Primary identifier')}">
                        <small class="form-text text-muted">${__("Your mobile number is used as your primary identifier")}</small>
                    </div>
                    
                    <div class="form-group">
                        <label class="control-label" for="guest-email">${__("Email")} <span class="text-danger">*</span></label>
                        <input type="email" class="form-control" id="guest-email" required>
                    </div>
                    
                    <div class="form-group">
                        <label class="control-label" for="guest-full-name">${__("Full Name")} <span class="text-danger">*</span></label>
                        <input type="text" class="form-control" id="guest-full-name" required>
                    </div>
                </div>
                
                <div class="col-md-6">
                    <h5>${__("Delivery Address")}</h5>
                    <div class="form-group">
                        <label class="control-label" for="guest-address-line1">${__("Address Line 1")} <span class="text-danger">*</span></label>
                        <input type="text" class="form-control" id="guest-address-line1" required>
                    </div>
                    
                    <div class="form-group">
                        <label class="control-label" for="guest-address-line2">${__("Address Line 2")}</label>
                        <input type="text" class="form-control" id="guest-address-line2">
                    </div>
                    
                    <div class="row">
                        <div class="col-md-6">
                            <div class="form-group">
                                <label class="control-label" for="guest-city">${__("City")} <span class="text-danger">*</span></label>
                                <input type="text" class="form-control" id="guest-city" required>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="form-group">
                                <label class="control-label" for="guest-state">${__("State")}</label>
                                <input type="text" class="form-control" id="guest-state">
                            </div>
                        </div>
                    </div>
                    
                    <div class="row">
                        <div class="col-md-6">
                            <div class="form-group">
                                <label class="control-label" for="guest-country">${__("Country")} <span class="text-danger">*</span></label>
                                <input type="text" class="form-control" id="guest-country" required>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="form-group">
                                <label class="control-label" for="guest-postal-code">${__("Postal Code")}</label>
                                <input type="text" class="form-control" id="guest-postal-code">
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row mt-4">
                <div class="col-md-6">
                    <div class="form-group">
                        <label class="control-label" for="guest-delivery-area">${__("Delivery Area")} <span class="text-danger">*</span></label>
                        <select class="form-control" id="guest-delivery-area" required>
                            <option value="">${__("Select a delivery area")}</option>
                        </select>
                    </div>
                </div>
                <div class="col-md-6">
                    <div id="delivery-charge-display" class="alert alert-info mt-4 d-none">
                        ${__("Delivery Charge")}: <span id="delivery-charge-amount">0</span>
                    </div>
                </div>
            </div>
            
            <div class="row mt-4">
                <div class="col-md-12">
                    <div class="form-group">
                        <label class="control-label" for="guest-notes">${__("Order Notes")}</label>
                        <textarea class="form-control" id="guest-notes" rows="3" 
                            placeholder="${__('Special instructions for delivery or order')}"></textarea>
                    </div>
                </div>
            </div>
        </div>
        `;
        
        // Insert form before the cart items or payment section
        if ($('.cart-items-section').length) {
            $('.cart-items-section').before(checkout_form_html);
        } else {
            // Fallback insertion point
            $('#page-cart .cart-container').prepend(checkout_form_html);
        }
        
        // Load delivery areas
        guest_checkout.load_delivery_areas();
        
        // Bind delivery area change event
        $(document).on('change', '#guest-delivery-area', function() {
            const selected_option = $(this).find('option:selected');
            const delivery_charge = selected_option.data('charge') || 0;
            
            // Update display
            $('#delivery-charge-amount').text(frappe.format_currency(delivery_charge));
            $('#delivery-charge-display').toggleClass('d-none', !delivery_charge);
            
            // Update cart with delivery charge
            guest_checkout.update_cart_with_delivery_charge($(this).val(), delivery_charge);
        });
        
        // Bind place order button events
        $(document).on('click', '.btn-place-order', function(e) {
            if (frappe.session.user === "Guest") {
                e.preventDefault();
                guest_checkout.submit_guest_order();
                return false;
            }
        });
    }
};

// Load delivery areas from backend
guest_checkout.load_delivery_areas = function() {
    frappe.call({
        method: "guest_checkout.delivery.get_delivery_areas",
        callback: function(r) {
            if (r.message && r.message.success) {
                const areas = r.message.areas || [];
                const select = $('#guest-delivery-area');
                
                // Clear existing options except first
                select.find('option:not(:first)').remove();
                
                // Add new options
                areas.forEach(function(area) {
                    const charge = area.delivery_charge || area.delivery_charges || 0;
                    select.append(`
                        <option value="${area.area_name}" data-charge="${charge}">
                            ${area.area_name} - ${frappe.format_currency(charge)}
                        </option>
                    `);
                });
            }
        }
    });
};

// Update cart with delivery charges
guest_checkout.update_cart_with_delivery_charge = function(delivery_area, delivery_charge) {
    if (!delivery_area) return;
    
    frappe.call({
        method: "guest_checkout.api.apply_delivery_charges_to_cart",
        args: {
            delivery_area_name: delivery_area,
            delivery_charge: delivery_charge
        },
        callback: function(r) {
            if (r.message) {
                // Refresh cart totals
                guest_checkout.refresh_cart_totals();
            }
        }
    });
};

// Refresh cart totals
guest_checkout.refresh_cart_totals = function() {
    // Refresh cart page to show updated totals
    // This could be improved to update only specific sections
    frappe.call({
        method: "webshop.webshop.shopping_cart.cart.get_cart_quotation",
        callback: function(r) {
            if (r.message) {
                $('.cart-tax-items').html(r.message.taxes);
                $('.cart-grand-total').html(r.message.grand_total_formatted);
                
                if (r.message.taxes_and_totals_html) {
                    $('.cart-payment-summary').html(r.message.taxes_and_totals_html);
                }
            }
        }
    });
};

// Submit guest order
guest_checkout.submit_guest_order = function() {
    // Validate form
    let is_valid = true;
    $('#guest-checkout-form input[required], #guest-checkout-form select[required]').each(function() {
        if (!$(this).val()) {
            $(this).addClass('is-invalid');
            is_valid = false;
        } else {
            $(this).removeClass('is-invalid');
        }
    });
    
    if (!is_valid) {
        frappe.msgprint(__("Please fill in all required fields"));
        return;
    }
    
    // Collect form data
    const guest_data = {
        mobile: $('#guest-mobile').val(),
        email: $('#guest-email').val(),
        full_name: $('#guest-full-name').val(),
        notes: $('#guest-notes').val()
    };
    
    const address_data = {
        address_line1: $('#guest-address-line1').val(),
        address_line2: $('#guest-address-line2').val(),
        city: $('#guest-city').val(),
        state: $('#guest-state').val(),
        country: $('#guest-country').val(),
        pincode: $('#guest-postal-code').val(),
        phone: $('#guest-mobile').val() // Use same phone number for address
    };
    
    const delivery_area = $('#guest-delivery-area').val();
    const delivery_charge = $('#guest-delivery-area option:selected').data('charge') || 0;
    
    // Show loading state
    frappe.freeze(__("Processing your order..."));
    
    // Submit order
    frappe.call({
        method: "guest_checkout.guest_cart.complete_guest_checkout",
        args: {
            guest_data: guest_data,
            address_data: address_data,
            payment_method: "Bookeey", // Default payment method
            delivery_area: delivery_area,
            delivery_charge: delivery_charge
        },
        callback: function(r) {
            frappe.unfreeze();
            
            if (r.message && r.message.success) {
                frappe.show_alert({
                    message: __("Order placed successfully! Order ID: {0}", [r.message.sales_order]),
                    indicator: 'green'
                });
                
                // Clear cart cookie and redirect to success page
                document.cookie = "cart_count=0; path=/";
                
                // Redirect to order success page
                if (r.message.sales_order) {
                    window.location.href = '/orders/' + r.message.sales_order;
                } else {
                    window.location.href = '/my-orders';
                }
            } else {
                frappe.msgprint({
                    title: __('Checkout Error'),
                    indicator: 'red',
                    message: r.message?.message || __("There was a problem processing your order. Please try again.")
                });
            }
        },
        error: function() {
            frappe.unfreeze();
            frappe.msgprint({
                title: __('Checkout Error'),
                indicator: 'red',
                message: __("There was a problem processing your order. Please try again.")
            });
        }
    });
};

// Initialize on document ready
$(document).ready(function() {
    guest_checkout.setup_checkout_form();
});
