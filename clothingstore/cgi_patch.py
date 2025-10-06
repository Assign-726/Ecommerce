# Temporary patch for Python 3.13 compatibility with Django
# This creates a minimal cgi module replacement

import sys
import urllib.parse
from io import StringIO

class FieldStorage:
    def __init__(self, fp=None, headers=None, outerboundary=None, 
                 environ=None, keep_blank_values=0, strict_parsing=0):
        self.list = []
        self.file = fp
        self.headers = headers or {}
        self.outerboundary = outerboundary
        self.environ = environ or {}
        
    def getvalue(self, key, default=None):
        return default
        
    def getfirst(self, key, default=None):
        return default
        
    def getlist(self, key):
        return []

def parse_qs(qs, keep_blank_values=False, strict_parsing=False, 
             encoding='utf-8', errors='replace', max_num_fields=None, separator='&'):
    return urllib.parse.parse_qs(qs, keep_blank_values, strict_parsing, 
                                encoding, errors, max_num_fields, separator)

def parse_qsl(qs, keep_blank_values=False, strict_parsing=False,
              encoding='utf-8', errors='replace', max_num_fields=None, separator='&'):
    return urllib.parse.parse_qsl(qs, keep_blank_values, strict_parsing,
                                 encoding, errors, max_num_fields, separator)

def escape(s, quote=False):
    import html
    return html.escape(s, quote)

# Add this module to sys.modules
sys.modules['cgi'] = sys.modules[__name__]
