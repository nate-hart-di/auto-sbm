"""SCSS Transformation Modules

This package contains specialized transformer modules that replace the monolithic
processing logic from the legacy processor.py file.

Each transformer is responsible for a specific aspect of SCSS transformation:
- VariableTransformer: Converts SCSS variables to CSS custom properties
- MixinTransformer: Converts SCSS mixins to CSS
- FunctionTransformer: Converts SCSS functions to CSS
- PathTransformer: Converts relative paths to absolute paths
- ImportRemover: Removes @import statements
- ContentCleaner: Cleans up whitespace and formatting
"""

from .base import BaseTransformer
from .content_cleaner import ContentCleaner
from .function_transformer import FunctionTransformer
from .import_remover import ImportRemover
from .mixin_transformer import MixinTransformer
from .path_transformer import PathTransformer
from .variable_transformer import VariableTransformer

__all__ = [
    "BaseTransformer",
    "ContentCleaner",
    "FunctionTransformer",
    "ImportRemover",
    "MixinTransformer",
    "PathTransformer",
    "VariableTransformer"
]
