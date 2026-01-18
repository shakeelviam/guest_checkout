# Guest Checkout App Package
# This file makes guest_checkout a proper Python package

import sys
import os

# Get the current directory
current_dir = os.path.dirname(__file__)

# Add the current directory to Python path if not already
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Make the inner guest_checkout module available
try:
    from . import guest_checkout
except ImportError:
    # If the inner module doesn't exist yet, pass
    pass
