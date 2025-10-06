#!/usr/bin/env python
"""
Django development server runner with Python 3.13 compatibility patch
"""
import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the cgi patch before Django imports
try:
    import cgi
except ImportError:
    print("Applying Python 3.13 compatibility patch for Django...")
    import cgi_patch

# Now run Django normally
if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clothingstore.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(['manage.py', 'runserver'])
