// guest_checkout/guest_checkout/public/js/guest_login_modal.js
frappe.provide("guest_checkout");

// Initialize guest checkout modal functionality
guest_checkout.init_guest_modal = function() {
    // Create and inject modal HTML if it doesn't exist
    if (!$("#guest-login-modal").length) {
        const modal_html = `
            <div class="modal fade" id="guest-login-modal" tabindex="-1" role="dialog" aria-labelledby="guest-login-modal-title" aria-hidden="true">
                <div class="modal-dialog" role="document">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="guest-login-modal-title">${__("Checkout Options")}</h5>
                            <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                                <span aria-hidden="true">&times;</span>
                            </button>
                        </div>
                        <div class="modal-body text-center">
                            <div class="row">
                                <div class="col-md-6 border-right">
                                    <div class="p-3">
                                        <i class="fas fa-user-check fa-3x mb-3 text-primary"></i>
                                        <h5>${__("Returning Customer?")}</h5>
                                        <p>${__("Log in to access your account")}</p>
                                        <button class="btn btn-primary btn-block mt-3" id="guest-modal-login">
                                            ${__("Login")}
                                        </button>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="p-3">
                                        <i class="fas fa-shopping-bag fa-3x mb-3 text-success"></i>
                                        <h5>${__("Guest Checkout")}</h5>
                                        <p>${__("Continue without creating an account")}</p>
                                        <button class="btn btn-success btn-block mt-3" id="guest-modal-continue">
                                            ${__("Continue as Guest")}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        $('body').append(modal_html);
        
        // Setup event handlers
        $("#guest-modal-login").on("click", function() {
            window.location.href = "/login?redirect-to=" + encodeURIComponent(window.location.pathname);
        });
        
        $("#guest-modal-continue").on("click", function() {
            // Close modal and proceed to cart
            $("#guest-login-modal").modal('hide');
            // Directly go to cart page
            window.location.href = "/cart";
        });
    }
    
    // Override webshop's update_cart function for guests
    if (frappe.session.user === "Guest" && webshop && webshop.webshop && webshop.webshop.shopping_cart) {
        // Store the original update_cart function
        const original_update_cart = webshop.webshop.shopping_cart.update_cart;
        
        // Replace with our modal-triggering version
        webshop.webshop.shopping_cart.update_cart = function(opts) {
            // First add item to cart
            original_update_cart(opts);
            
            // Then show the modal for guest users
            if (frappe.session.user === "Guest") {
                $("#guest-login-modal").modal('show');
            }
        };
    }
};

// Initialize when DOM is ready
$(document).ready(function() {
    guest_checkout.init_guest_modal();
});
