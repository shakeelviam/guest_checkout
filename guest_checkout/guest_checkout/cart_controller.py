import frappe

def get_context(context):
    """Custom cart controller to allow guest checkout"""
    context.allow_guest_checkout = True
    return context
