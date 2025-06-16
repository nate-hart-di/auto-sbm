"""
Stellantis OEM handler for SBM Tool V2.
"""

from typing import Dict, Any, List
from sbm.oem.base import BaseOEMHandler


class StellantisHandler(BaseOEMHandler):
    """Stellantis-specific OEM handler."""
    
    def detect_oem(self, slug: str) -> Dict[str, Any]:
        """Detect Stellantis brands."""
        stellantis_brands = ["chrysler", "dodge", "jeep", "ram", "fiat", "cdjr"]
        
        for brand in stellantis_brands:
            if brand in slug.lower():
                return {
                    "oem": "Stellantis",
                    "brand": brand.capitalize(),
                    "confidence": 0.95,
                    "enhanced_processing": True
                }
        
        return {
            "oem": "Unknown",
            "brand": "Unknown",
            "confidence": 0.0,
            "enhanced_processing": False
        }
    
    def get_oem_name(self) -> str:
        """Get OEM name."""
        return "Stellantis"
    
    def detect_brand(self, slug: str) -> str:
        """Detect specific Stellantis brand from slug."""
        stellantis_brands = ["chrysler", "dodge", "jeep", "ram", "fiat", "cdjr"]
        
        for brand in stellantis_brands:
            if brand in slug.lower():
                return brand.capitalize()
        
        return "Unknown"
    
    def get_additional_styles(self, file_type: str) -> List[str]:
        """Get FCA-specific styles to inject."""
        if file_type == "sb-inside":
            return [
                self._get_fca_direction_row_styles(),
                self._get_fca_cookie_banner_styles()
            ]
        elif file_type == "sb-home":
            return [
                self._get_fca_cookie_banner_styles()
            ]
        return []
    
    def get_enhanced_features(self) -> List[str]:
        """Get list of Stellantis enhanced features."""
        return [
            "FCA Direction Row Styles",
            "FCA Cookie Banner styles"
        ]
    
    def _get_fca_direction_row_styles(self) -> str:
        """Get FCA Direction Row styles for Stellantis dealers."""
        return '''
/* FCA DIRECTION ROW STYLES */
#mapRow {
    position: relative;
    
    .mapwrap {
        height: 600px;
    }
}

#map-canvas {
    height: 100%;
}

#directionsBox {
    padding: 50px 0;
    text-align: left;
    width: 400px;
    position: absolute;
    top: 200px;
    left: 50px;
    background: $white;
    color: $black;
    font-family: 'Lato', sans-serif;
}

@media (min-width: 768px) {
    #mapRow .mapwrap {
        height: 400px;
    }
}

@media (min-width: 1024px) {
    #mapRow .mapwrap {
        height: 600px;
    }
    
    #directionsBox {
        max-width: 45%;
    }
}'''
    
    def _get_fca_cookie_banner_styles(self) -> str:
        """Get FCA Cookie Banner styles for Stellantis dealers."""
        return '''
/* FCA COOKIE BANNER STYLES */
.cookie-consent-banner {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: $primary;
    color: $white;
    padding: 1rem;
    z-index: 9999;
    box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.1);
    
    .cookie-consent-content {
        max-width: 1200px;
        margin: 0 auto;
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 1rem;
    }
    
    .cookie-consent-text {
        flex: 1;
        font-size: 0.9rem;
        line-height: 1.4;
    }
    
    .cookie-consent-buttons {
        display: flex;
        gap: 0.5rem;
        
        .btn {
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9rem;
            transition: background 0.2s;
            
            &.accept {
                background: $cta;
                color: $white;
                
                &:hover {
                    background: $ctahover;
                }
            }
            
            &.decline {
                background: transparent;
                color: $white;
                border: 1px solid $white;
                
                &:hover {
                    background: rgba(255, 255, 255, 0.1);
                }
            }
        }
    }
}

@media (max-width: 768px) {
    .cookie-consent-banner .cookie-consent-content {
        flex-direction: column;
        text-align: center;
    }
}''' 
