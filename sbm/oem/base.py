"""
Base OEM handler for SBM Tool V2.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from sbm.config import Config


class BaseOEMHandler(ABC):
    """Base class for OEM handlers."""
    
    def __init__(self, config: Config):
        """Initialize OEM handler."""
        self.config = config
    
    @abstractmethod
    def detect_oem(self, slug: str) -> Dict[str, Any]:
        """Detect OEM for theme."""
        pass
    
    @abstractmethod
    def get_oem_name(self) -> str:
        """Get OEM name."""
        pass
    
    def get_additional_styles(self, file_type: str) -> List[str]:
        """Get additional styles to inject for this OEM.
        
        Args:
            file_type: Type of file ('sb-inside', 'sb-home', etc.)
            
        Returns:
            List of CSS/SCSS code blocks to inject
        """
        return []
    
    def get_enhanced_features(self) -> List[str]:
        """Get list of enhanced features this OEM provides."""
        return [] 
