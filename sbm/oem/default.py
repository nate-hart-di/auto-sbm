"""
Default OEM handler for SBM Tool V2.
"""

from typing import Dict, Any
from sbm.oem.base import BaseOEMHandler


class DefaultHandler(BaseOEMHandler):
    """Default OEM handler for unknown brands."""
    
    def detect_oem(self, slug: str) -> Dict[str, Any]:
        """Default OEM detection."""
        return {
            "oem": "Unknown",
            "brand": "Unknown",
            "confidence": 0.0,
            "enhanced_processing": False
        }
    
    def get_oem_name(self) -> str:
        """Get OEM name."""
        return "Unknown" 
