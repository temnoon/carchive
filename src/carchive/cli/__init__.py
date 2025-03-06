"""
Initialize the CLI package. Contains shared CLI utilities and configuration.
"""

import logging

# Configure global logging for CLI modules
# Suppress NumExpr messages across all CLI commands
logging.getLogger('numexpr').setLevel(logging.ERROR)
logging.getLogger('numexpr.utils').setLevel(logging.ERROR)
