# OEM Handler Module for Site Builder Migration Tool

This module provides support for multiple Original Equipment Manufacturers (OEMs) in the Site Builder Migration (SBM) tool. It allows the tool to adapt its migration process based on the specific OEM of a dealer's website.

## Overview

The OEM module is structured with the following components:

1. **BaseOEMHandler** - Abstract base class that defines the interface for all OEM handlers
2. **StellantisHandler** - Concrete implementation for Stellantis/CDJR brands (Chrysler, Dodge, Jeep, Ram, Fiat)
3. **DefaultHandler** - Fallback handler for unrecognized dealers
4. **OEMFactory** - Factory class that detects and creates appropriate OEM handlers

## How to Add a New OEM Handler

To add support for a new OEM (e.g., Toyota, Honda, BMW), follow these steps:

### 1. Create a New Handler Class

Create a new file named after your OEM (e.g., `toyota.py`) in the `sbm/oem` directory:

```python
# filepath: sbm/oem/toyota.py
"""
Toyota OEM handler for the SBM tool.

This module provides Toyota-specific handling for Toyota brands.
"""

from .base import BaseOEMHandler


class ToyotaHandler(BaseOEMHandler):
    """
    Toyota specific implementation.

    Handles Toyota and Lexus brands.
    """

    def get_map_styles(self):
        """
        Get Toyota-specific map styles.

        Returns:
            str: CSS/SCSS content for map styles
        """
        # Option 1: Load from a file
        return self._load_style_file('toyota-map-styles.scss')

        # Option 2: Return the styles inline
        # return """
        # /* Toyota-specific map styles */
        # #mapRow {
        #   position: relative;
        #   .mapwrap {
        #     height: 500px;
        #   }
        # }
        # """

    def get_directions_styles(self):
        """
        Get Toyota-specific direction box styles.

        Returns:
            str: CSS/SCSS content for directions box styles
        """
        return self._load_style_file('toyota-directions-row-styles.scss')

    def get_map_partial_patterns(self):
        """
        Get Toyota-specific patterns for identifying map partials.

        Returns:
            list: Regular expression patterns for finding map partials
        """
        # Toyota-specific patterns
        toyota_patterns = [
            r'dealer-groups/toyota/map-row-\d+',
            r'dealer-groups/toyota/directions'
        ]
        return toyota_patterns + super().get_map_partial_patterns()

    def get_shortcode_patterns(self):
        """
        Get Toyota-specific patterns for identifying map shortcodes.

        Returns:
            list: Regular expression patterns for finding map shortcodes
        """
        # Toyota-specific shortcode patterns
        toyota_patterns = [
            r'add_shortcode\s*\(\s*[\'"]toyota-map[\'"]'
        ]
        return toyota_patterns + super().get_shortcode_patterns()

    def get_brand_match_patterns(self):
        """
        Get patterns for identifying if a dealer belongs to Toyota.

        Returns:
            list: Regular expression patterns for matching Toyota brands
        """
        return [
            r'toyota',
            r'lexus',
            r'scion'
        ]
```

### 2. Add your Style Files (Optional)

If your OEM has specific style files, add them to the appropriate directory:

```
/auto-sbm
  /toyota                  # Create a directory for your OEM
    /add-to-sb-inside
      toyota-map-styles.scss
      toyota-directions-row-styles.scss
```

### 3. Register your Handler in the OEMFactory

Update the `OEMFactory` class in `sbm/oem/factory.py` to include your new handler:

```python
# In sbm/oem/factory.py

# Import your new handler
from .toyota import ToyotaHandler

class OEMFactory:
    """
    Factory for creating OEM handlers based on dealer information.
    """

    # Add your handler to the list of available handlers
    _handlers = [
        StellantisHandler,
        ToyotaHandler,  # Add your new handler here
        # Add more handlers as needed
    ]

    # Rest of the factory code...
```

### 4. Test Your Implementation

Test your new OEM handler with both:

1. Automatic detection:

```bash
python -m sbm.cli your-toyota-dealer-slug
```

2. Manual specification:

```bash
python -m sbm.cli your-toyota-dealer-slug --oem toyota
```

## OEM Handler Interface

Any new OEM handler must implement the following methods:

### Required Methods

These methods must be implemented in your handler:

- `get_map_styles()` - Returns CSS/SCSS content for map styles
- `get_directions_styles()` - Returns CSS/SCSS content for directions box styles
- `get_brand_match_patterns()` - Returns patterns for identifying if a dealer belongs to this OEM

### Optional Methods

These methods have default implementations but can be overridden:

- `get_map_partial_patterns()` - Returns patterns for identifying map partials
- `get_shortcode_patterns()` - Returns patterns for identifying map shortcodes

### Helper Methods

- `_load_style_file(filename)` - Helper method to load style content from a file

## Best Practices

1. **Keep Styles Consistent**: Follow the existing styling patterns for consistency.
2. **Provide Specific Patterns**: Make your pattern matching as specific as possible to avoid false positives.
3. **Document Brand Associations**: Clearly document which brands your handler supports.
4. **Test Thoroughly**: Test your handler with both known and edge cases.
5. **Fallback Gracefully**: When in doubt, fall back to default implementations.
