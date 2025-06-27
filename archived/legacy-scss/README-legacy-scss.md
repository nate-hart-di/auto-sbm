# Legacy Style Parser Files

This directory contains legacy versions of style parsers that have been integrated into the main SBM codebase.

## Files

- `improved_style_parser.py`: The original standalone improved style parser that correctly handles multi-selector CSS rules. This functionality has been integrated into `sbm/scss/enhanced_parser.py`.

## Notes

These files are kept for reference only. All functionality has been properly integrated into the main SBM codebase according to the modular structure.

When working with the SBM tool, you should use the integrated parser via:

```python
from sbm.scss.enhanced_parser import analyze_style_scss

# Call with default parameters (uses improved parser)
styles = analyze_style_scss(theme_dir)

# Or explicitly specify parser type
styles = analyze_style_scss(theme_dir, use_improved_parser=True)
```
