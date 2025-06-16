"""
OEM factory for SBM Tool V2.

Creates appropriate OEM handlers based on dealer theme analysis.
"""

from typing import Dict, Any
from sbm.config import Config
from sbm.oem.base import BaseOEMHandler
from sbm.oem.stellantis import StellantisHandler
from sbm.oem.default import DefaultHandler


class OEMHandlerFactory:
    """Factory for creating OEM handlers."""
    
    def __init__(self, config: Config):
        """Initialize factory with config."""
        self.config = config
    
    def get_handler(self, slug: str) -> BaseOEMHandler:
        """Get appropriate OEM handler for a dealer slug."""
        # Try Stellantis first
        stellantis_handler = StellantisHandler(self.config)
        stellantis_result = stellantis_handler.detect_oem(slug)
        
        if stellantis_result["confidence"] > 0.5:
            return stellantis_handler
        
        # Default fallback
        return DefaultHandler(self.config)
    
    @staticmethod
    def detect_oem(slug: str) -> Dict[str, Any]:
        """Quick OEM detection without creating handler."""
        stellantis_brands = ["chrysler", "dodge", "jeep", "ram", "fiat", "cdjr"]
        
        for brand in stellantis_brands:
            if brand in slug.lower():
                return {
                    "oem": "Stellantis",
                    "brand": brand.capitalize(),
                    "confidence": 0.95
                }
        
        return {
            "oem": "Unknown",
            "brand": "Unknown", 
            "confidence": 0.0
        } 
