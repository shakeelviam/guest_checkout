// guest_checkout/public/js/guest_checkout_shopping_cart.js
// Overrides for shopping cart to support guest checkout

frappe.provide("shopping_cart");

// Override place order button behavior
$(document).on('click', '.btn-place-order', function(e) {
    e.preventDefault();
    e.stopPropagation();
    
    // Check if user is guest
    if (frappe.session.user === 'Guest') {
        // For guests, show the checkout modal
        if (window.guest_checkout && window.guest_checkout.show_checkout_modal) {
            guest_checkout.show_checkout_modal();
        } else {
            frappe.msgprint({
                title: __('Guest Checkout'),
                message: __('Please wait while we load the checkout form...'),
                indicator: 'blue'
            });
            
            // Reload page if guest_checkout not loaded yet
            setTimeout(function() {
                window.location.reload();
            }, 1000);
        }
        return false;
    }
    
    // For logged-in users, use default behavior
    place_order(this);
});

// Override request for quotation button
$(document).on('click', '.btn-request-for-quotation', function(e) {
    e.preventDefault();
    e.stopPropagation();
    
    if (frappe.session.user === 'Guest') {
        frappe.msgprint({
            title: __('Login Required'),
            message: __('Please login to request a quotation.'),
            indicator: 'orange'
        });
        setTimeout(function() {
            window.location.href = '/login?redirect-to=/cart';
        }, 2000);
        return false;
    }
    
    // For logged-in users, use default behavior
    request_quotation(this);
});

// Helper function to update cart count everywhere
function update_cart_indicators() {
    frappe.call({
        method: "guest_checkout.guest_cart.get_shopping_cart_menu",
        callback: function(r) {
            if (r.message) {
                const count = r.message.cart_count || 0;
                
                // Update all cart count indicators
                $('.cart-count, #cart-count-text, .ps-cart-btn').each(function() {
                    if ($(this).hasClass('ps-cart-btn')) {
                        $(this).html(`<i class="fa fa-shopping-cart"></i> Cart (${count})`);
                    } else {
                        $(this).text(count);
                    }
                });
                
                // Update cookie
                document.cookie = `cart_count=${count}; path=/; max-age=31536000`;
            }
        }
    });
}

// Update cart on page load
$(document).ready(function() {
    update_cart_indicators();
});
