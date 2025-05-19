# Enhanced Style Extraction

The Site Builder Migration (SBM) tool now includes enhanced style extraction from `style.scss` files. This feature is designed to automatically identify and extract page-specific styles from the main stylesheet and place them in the appropriate Site Builder SCSS files.

## Features

The enhanced parser can:

1. Extract page-specific styles from `style.scss` based on:

   - Selectors indicating page types (e.g., `.vdp`, `.vrp`, `.page-template-default`)
   - Comment blocks marked with section headers (e.g., `// HEADER`, `// NAVIGATION`)
   - Ticket numbers or feature markers that mention page types

2. Place extracted styles in the appropriate Site Builder files:

   - VDP styles → `sb-vdp.scss`
   - VRP/SRP styles → `sb-vrp.scss`
   - Inside page styles → `sb-inside.scss`

3. Programmatically analyze sections of code and make intelligent decisions about where they belong

## How It Works

The style extraction process follows these steps:

1. First, it looks for dedicated files like `vdp.scss`, `vrp.scss`, and `inside.scss`
2. Then, it scans `style.scss` for additional page-specific styles
3. It breaks down `style.scss` into logical sections and analyzes each one
4. It categorizes each section based on selector patterns and context
5. It merges styles from all sources into the appropriate Site Builder files
6. Finally, it transforms and validates the merged styles

## Testing Style Extraction

You can test the enhanced style extraction with any `style.scss` file using the dedicated standalone script:

```bash
python enhanced_style_parser.py [--verbose] < dealer-slug > [--dry-run]
```

Options:

- `--dry-run`: Show what would be done without modifying files
- `--verbose`: Show detailed debug information

You can also use the testing script for analyzing a single file:

```bash
chmod +x test-enhanced-parser.py
./test-enhanced-parser.py path/to/style.scss --output-dir ./output
```

This will:

- Analyze the provided `style.scss` file
- Extract styles for each page type
- Save the extracted styles to the output directory

## Detection Patterns

The parser now uses more sophisticated patterns to identify page-specific styles:

### VDP Styles

- Selectors: `.vdp`, `.lvdp`, `.page-template-vehicle`, `.vehicle-detail`, etc.
- Comment sections about VDP
- Ticket numbers mentioning VDP

### VRP Styles

- Selectors: `.vrp`, `.lvrp`, `.vehicle-list`, `.srp`, `.page-template-inventory`, etc.
- Comment sections about VRP/SRP
- Ticket numbers mentioning VRP/SRP

### Inside Page Styles (Default)

- Global selectors like `body`, `#header`, `#footer`
- Component styles that don't match VDP or VRP patterns
- Layout and structure styles

## Best Practices

While the automated extraction works well for most cases, here are some best practices:

1. **Review the Results**: Always review the generated Site Builder SCSS files to ensure styles are correctly placed

2. **Manual Adjustments**: Some styles might need manual adjustment after automated extraction

3. **Handle Shared Styles**: If styles are used across multiple page types, consider placing them in `sb-inside.scss`

4. **Selector Patterns**: The system uses selector patterns for classification - be aware that ambiguous selectors might be misclassified

## Limitations

The style extraction is based on heuristics and may not perfectly identify all page-specific styles. Manual review is still recommended for complex themes.

Common challenges include:

- Styles without clear page-type indicators
- Complex nested rules
- Minified or compressed SCSS
- Non-standard naming conventions

## Future Improvements

Planned improvements for this feature:

1. Additional selector pattern recognition
2. Machine learning-based classification for ambiguous sections
3. Conflict resolution for styles that appear in multiple files
4. Interactive mode for manual classification of ambiguous sections
