"""
Site Builder Migration (SBM) Tool

A comprehensive toolset for automating dealer website migrations to the Site Builder platform.
"""

# Dynamic version from package metadata (single source of truth: pyproject.toml)
try:
    from importlib.metadata import version

    __version__ = version("auto-sbm")
except Exception:
    # Fallback for development/editable installs
    __version__ = "dev"
