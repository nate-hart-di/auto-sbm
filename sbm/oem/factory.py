"""
OEM factory for SBM Tool V2.

Creates appropriate OEM handlers based on dealer theme analysis.
"""

from typing import Dict, Any
from sbm.config import Config
from sbm.oem.handler import OEMHandler


class OEMFactory:
    """Factory for creating OEM handlers."""
    
    @staticmethod
    def create_handler(slug: str, config: Config) -> OEMHandler:
        """Create appropriate OEM handler for a dealer theme."""
        return OEMHandler(config)
    
    @staticmethod
    def detect_oem(slug: str) -> Dict[str, Any]:
        """Detect OEM from dealer slug."""
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
