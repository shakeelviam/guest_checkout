// guest_checkout/public/js/guest_checkout.js
// Guest checkout functionality for Webshop

frappe.provide("guest_checkout");

// Initialize guest checkout on page load
$(document).ready(function() {
    guest_checkout.init();
});

guest_checkout.init = function() {
    // Update cart count in navbar on page load
    guest_checkout.update_cart_count();
    
    // Override shopping_cart methods if they exist
    if (typeof shopping_cart !== 'undefined') {
        guest_checkout.override_shopping_cart();
    }
    
    // Setup guest checkout button handlers
    guest_checkout.setup_checkout_handlers();
    
    // Listen for cart update events
    $(document).on('cart_updated', function(e, data) {
        guest_checkout.update_cart_display(data);
    });
};

// Override default shopping cart update_cart function
guest_checkout.override_shopping_cart = function() {
    shopping_cart.update_cart = function(opts) {
        if (opts.btn) {
            $(opts.btn).prop("disabled", true);
        }

        return frappe.call({
            type: "POST",
            method: "guest_checkout.guest_cart.update_cart_allow_guest",
            args: {
                item_code: opts.item_code,
                qty: opts.qty,
                additional_notes: opts.additional_notes,
                with_items: opts.with_items || 0
            },
            btn: opts.btn,
            callback: function(r) {
                if (opts.btn) {
                    $(opts.btn).prop("disabled", false);
                }
                
                // Update cart count
                guest_checkout.update_cart_count();
                
                if (opts.callback) {
                    opts.callback(r);
                }
            }
        });
    };
};

// Update cart count in navbar
guest_checkout.update_cart_count = function() {
    frappe.call({
        method: "guest_checkout.guest_cart.get_shopping_cart_menu",
        callback: function(r) {
            if (r.message) {
                const cart_count = r.message.cart_count || 0;
                const cart_items = r.message.cart_items || [];
                const total = r.message.total || 0;
                
                // Update navbar cart button
                const cartBtn = $('.ps-cart-btn, .cart-icon');
                if (cartBtn.length) {
                    cartBtn.html(`<i class="fa fa-shopping-cart"></i> Cart (${cart_count})`);
                }
                
                // Update cart count badge if exists
                const cartBadge = $('.cart-count, #cart-count-text');
                if (cartBadge.length) {
                    cartBadge.text(`Cart (${cart_count})`);
                }
                
                // Update cookie
                document.cookie = `cart_count=${cart_count}; path=/; max-age=31536000`;
                
                // Trigger custom event
                $(document).trigger('cart_updated', {
                    count: cart_count,
                    items: cart_items,
                    total: total
                });
            }
        }
    });
};

// Update cart display in dropdown or page
guest_checkout.update_cart_display = function(data) {
    const count = data.count || 0;
    const items = data.items || [];
    const total = data.total || 0;
    
    // Update dropdown if it exists
    const cartDropdown = $('#cart-dropdown, .ps-cart-dropdown');
    if (cartDropdown.length && items.length > 0) {
        let itemsHTML = '';
        items.forEach(function(item) {
            const imageHTML = item.image 
                ? `<img src="${item.image}" class="ps-cart-item-image" style="width: 60px; height: 60px; object-fit: cover; border-radius: 4px;" alt="${item.item_name}">`
                : `<div class="ps-cart-item-image" style="width: 60px; height: 60px; background: #f5f5f5; border-radius: 4px; display: flex; align-items: center; justify-content: center;"><i class="fa fa-image" style="color: #ccc;"></i></div>`;
            
            itemsHTML += `
                <div class="ps-cart-item" style="display: flex; gap: 10px; padding: 10px 0; border-bottom: 1px solid #f0f0f0;">
                    ${imageHTML}
                    <div class="ps-cart-item-details" style="flex: 1;">
                        <div class="ps-cart-item-name" style="font-weight: 600; font-size: 14px; margin-bottom: 5px;">${item.item_name}</div>
                        <div class="ps-cart-item-qty" style="font-size: 13px; color: #666;">Qty: ${item.qty}</div>
                        <div class="ps-cart-item-price" style="font-weight: 600; color: #66cfc7;">KD ${item.amount.toFixed(3)}</div>
                    </div>
                </div>
            `;
        });
        
        const totalHTML = `
            <div class="ps-cart-total" style="padding: 15px; border-top: 2px solid #f0f0f0; display: flex; justify-content: space-between; font-weight: 600; font-size: 16px;">
                <span>Total:</span>
                <span>KD ${total.toFixed(3)}</span>
            </div>
        `;
        
        const actionsHTML = `
            <div class="ps-cart-actions" style="padding: 15px; display: flex; gap: 10px;">
                <button class="ps-view-cart-btn" onclick="window.location.href='/cart'" style="flex: 1; padding: 10px; border: none; border-radius: 6px; font-weight: 600; cursor: pointer; background: #f5f5f5; color: #333;">View Cart</button>
                <button class="ps-checkout-btn" data-action="guest-checkout" style="flex: 1; padding: 10px; border: none; border-radius: 6px; font-weight: 600; cursor: pointer; background: #66cfc7; color: white;">Checkout</button>
            </div>
        `;
        
        const cartItemsContainer = $('#cart-items-container, .ps-cart-items');
        if (cartItemsContainer.length) {
            cartItemsContainer.html(itemsHTML + totalHTML + actionsHTML);
        }
    }
};

// Setup checkout button handlers
guest_checkout.setup_checkout_handlers = function() {
    // Handle checkout button clicks
    $(document).on('click', '[data-action="guest-checkout"], .btn-place-order', function(e) {
        e.preventDefault();
        
        // Check if user is logged in
        if (frappe.session.user !== 'Guest') {
            // For logged-in users, use standard checkout
            window.location.href = '/checkout';
            return;
        }
        
        // For guests, show checkout modal
        guest_checkout.show_checkout_modal();
    });
};

// Show guest checkout modal WITH DELIVERY AREA
guest_checkout.show_checkout_modal = function() {
    // First, fetch delivery areas
    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Delivery Area",
            fields: ["name", "area", "delivery_charge"],
            limit_page_length: 999
        },
        callback: function(r) {
            const delivery_areas = r.message || [];
            
            // Build delivery area options
            let delivery_options = delivery_areas.map(area => {
                return `${area.area} - KD ${parseFloat(area.delivery_charge).toFixed(3)}`;
            });
            
            const d = new frappe.ui.Dialog({
                title: __('Complete Your Order'),
                fields: [
                    {
                        fieldtype: 'Section Break',
                        label: __('Personal Information')
                    },
                    {
                        fieldname: 'full_name',
                        fieldtype: 'Data',
                        label: __('Full Name'),
                        reqd: 1,
                        description: __('Enter your full name')
                    },
                    {
                        fieldname: 'email',
                        fieldtype: 'Data',
                        label: __('Email Address'),
                        reqd: 1,
                        options: 'Email',
                        description: __('We will send order confirmation to this email')
                    },
                    {
                        fieldname: 'mobile',
                        fieldtype: 'Data',
                        label: __('Mobile Number'),
                        reqd: 1,
                        description: __('Enter mobile with country code (e.g., +96512345678)')
                    },
                    {
                        fieldtype: 'Column Break'
                    },
                    {
                        fieldtype: 'Section Break',
                        label: __('Delivery Address')
                    },
                    {
                        fieldname: 'delivery_area',
                        fieldtype: 'Select',
                        label: __('Delivery Area'),
                        options: delivery_options,
                        reqd: 1,
                        description: __('Select your delivery area')
                    },
                    {
                        fieldname: 'address_line1',
                        fieldtype: 'Data',
                        label: __('Address Line 1'),
                        reqd: 1,
                        description: __('Block, Street, Building number')
                    },
                    {
                        fieldname: 'address_line2',
                        fieldtype: 'Data',
                        label: __('Address Line 2'),
                        description: __('Apartment, Floor (optional)')
                    },
                    {
                        fieldname: 'city',
                        fieldtype: 'Data',
                        label: __('City'),
                        reqd: 1,
                        default: 'Kuwait City'
                    },
                    {
                        fieldtype: 'Column Break'
                    },
                    {
                        fieldname: 'state',
                        fieldtype: 'Data',
                        label: __('State/Province'),
                        description: __('Optional')
                    },
                    {
                        fieldname: 'pincode',
                        fieldtype: 'Data',
                        label: __('Postal Code'),
                        description: __('Optional')
                    },
                    {
                        fieldname: 'country',
                        fieldtype: 'Link',
                        label: __('Country'),
                        options: 'Country',
                        reqd: 1,
                        default: 'Kuwait'
                    },
                    {
                        fieldtype: 'Section Break',
                        label: __('Additional Information')
                    },
                    {
                        fieldname: 'phone',
                        fieldtype: 'Data',
                        label: __('Alternative Phone'),
                        description: __('Optional')
                    },
                    {
                        fieldname: 'payment_method',
                        fieldtype: 'Select',
                        label: __('Payment Method'),
                        options: ['Bookeey', 'Cash on Delivery'],
                        default: 'Bookeey',
                        reqd: 1
                    }
                ],
                size: 'large',
                primary_action_label: __('Place Order'),
                primary_action: function(values) {
                    // Find the selected delivery area details
                    const selected_area_text = values.delivery_area;
                    const selected_area = delivery_areas.find(area => 
                        selected_area_text.includes(area.area)
                    );
                    
                    values.delivery_area_name = selected_area ? selected_area.name : null;
                    values.delivery_charge = selected_area ? selected_area.delivery_charge : 0;
                    
                    d.hide();
                    guest_checkout.process_checkout(values);
                },
                secondary_action_label: __('Cancel'),
                secondary_action: function() {
                    d.hide();
                }
            });
            
            d.show();
        }
    });
};

// Process guest checkout WITH DELIVERY AREA
guest_checkout.process_checkout = function(values) {
    // Show processing message
    frappe.show_alert({
        message: __('Processing your order...'),
        indicator: 'blue'
    }, 3);
    
    const guest_data = {
        full_name: values.full_name,
        email: values.email,
        mobile: values.mobile
    };
    
    const address_data = {
        address_line1: values.address_line1,
        address_line2: values.address_line2 || '',
        city: values.city,
        state: values.state || '',
        pincode: values.pincode || '',
        country: values.country,
        phone: values.phone || values.mobile,
        email: values.email
    };
    
    frappe.call({
        method: "guest_checkout.guest_cart.complete_guest_checkout",
        args: {
            guest_data: JSON.stringify(guest_data),
            address_data: JSON.stringify(address_data),
            payment_method: values.payment_method,
            delivery_area: values.delivery_area_name,
            delivery_charge: values.delivery_charge
        },
        freeze: true,
        freeze_message: __('Creating your order...'),
        callback: function(r) {
            if (r.message && r.message.success) {
                // Show success message
                frappe.show_alert({
                    message: __('Order placed successfully! Order ID: {0}', [r.message.sales_order]),
                    indicator: 'green'
                }, 10);
                
                // Clear cart count
                guest_checkout.update_cart_count();
                
                // Redirect to order confirmation or thank you page
                setTimeout(function() {
                    window.location.href = `/order-confirmation?order=${r.message.sales_order}`;
                }, 2000);
            } else {
                frappe.msgprint({
                    title: __('Checkout Failed'),
                    message: __('Unable to complete your order. Please try again or contact support.'),
                    indicator: 'red'
                });
            }
        },
        error: function(r) {
            frappe.msgprint({
                title: __('Error'),
                message: __('An error occurred while processing your order. Please try again.'),
                indicator: 'red'
            });
        }
    });
};

// Export for use in other scripts
window.guest_checkout = guest_checkout;
