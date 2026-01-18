# This file marks the `guest_checkout` directory as a Python package.

# Fix for Python import system - explicitly import submodules
import sys
import os

# Add the current directory to Python path if not already
current_dir = os.path.dirname(__file__)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Explicitly import the guest_cart module
from . import guest_cart

# Re-export the main functions
__all__ = ['guest_cart']

# Make functions available at package level for backward compatibility
update_cart_allow_guest = guest_cart.update_cart_allow_guest
get_cart_quotation_allow_guest = guest_cart.get_cart_quotation_allow_guest
set_cart_count_allow_guest = guest_cart.set_cart_count_allow_guest
get_guest_party = guest_cart.get_guest_party
