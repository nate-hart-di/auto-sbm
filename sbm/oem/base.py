"""
Base OEM handler for SBM Tool V2.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
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
