"""SCSS Processing Feature Slice

This feature slice handles the transformation of legacy SCSS to Site Builder-compatible CSS.
It replaces the monolithic sbm/scss/ modules with a clean, type-safe architecture.

Main Components:
- models.py: Pydantic models for SCSS data structures
- service.py: Core SCSS processing service
- mixin_parser.py: Improved mixin conversion with type safety
- validator.py: SCSS validation and compliance checking
- transformers/: Individual transformation modules
"""

from .models import (
    ScssMixinDefinition,
    ScssProcessingConfig,
    ScssProcessingResult,
    ScssTransformationContext,
    ScssVariable,
)
from .service import ScssProcessingService

__all__ = [
    "ScssMixinDefinition",
    "ScssProcessingConfig",
    "ScssProcessingResult",
    "ScssProcessingService",
    "ScssTransformationContext",
    "ScssVariable"
]
