"""
SBM Tool V2 - Site Builder Migration Tool

Team-friendly migration tool for DealerInspire dealer websites.
Automated SCSS processing and Site Builder migration capabilities.
"""

__version__ = "2.0.0"
__author__ = "DealerInspire Development Team"
__email__ = "development@dealerinspire.com"

from sbm.config import Config
from sbm.utils.logger import get_logger
from sbm.utils.errors import SBMError

# Core imports for easy access
from .core.migration import migrate_dealer_theme
from .core.workflow import MigrationWorkflow

__all__ = [
    "Config",
    "get_logger", 
    "SBMError",
    "migrate_dealer_theme",
    "MigrationWorkflow"
] 
