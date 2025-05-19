# Improved Style Parser Integration

## Overview

The SBM tool has been enhanced with an improved style parser that correctly handles multi-selector CSS rules. This enhancement ensures proper categorization of styles when CSS rules contain multiple comma-separated selectors.

## Key Features

The improved style parser uses the following categorization logic:

1. If any selector in a comma-separated list matches VDP patterns, the entire rule is categorized as VDP
2. If any selector matches VRP patterns (and no VDP patterns), the entire rule is categorized as VRP
3. Otherwise, the rule is categorized as "inside"
4. Ticket-wrapped rules (with comments containing ticket numbers) are preserved intact

## Usage

The improved style parser is enabled by default in the SBM workflow. If you need to use the legacy parser for any reason, you can use the `--legacy-parser` flag when running the migration tool:

```bash
./sbm.sh <dealer-slug> --legacy-parser
```

Or directly with the Python script:

```bash
python site_builder_migration.py <dealer-slug> --legacy-parser
```

## Testing

You can test the improved style parser on a dealer theme using the test script:

```bash
python test-improved-parser.py <dealer-slug>
```

To compare the results with the legacy parser:

```bash
python test-improved-parser.py <dealer-slug> --compare
```

The test script will generate output files in the `test-output/` directory for review.

## Implementation Details

The improved style parser is integrated into the existing `sbm/scss/enhanced_parser.py` module with the following enhancements:

1. New functions for parsing and distributing style rules
   - `parse_style_rules()`: Breaks down CSS content into discrete rules and categorizes them
   - `distribute_rules()`: Groups rules by category for output

2. Enhanced `analyze_style_scss()` function with a parameter to toggle between the improved and legacy parsers

3. Updates to the migration workflow to use the improved parser by default

## Benefits

The improved style parser offers the following benefits:

1. **Better Handling of Multi-Selector Rules**: Correctly categorizes rules with multiple selectors
2. **Proper Categorization**: Ensures VDP and VRP styles are placed in the right files
3. **Preserved Ticket Context**: Ticket-wrapped rules stay intact with their comments
4. **Easier Debugging**: More detailed logging of the categorization process
5. **Backward Compatibility**: Support for the legacy parser if needed

## Troubleshooting

If you encounter issues with the improved parser:

1. Run with verbose logging for more details:
   ```bash
   python test-improved-parser.py <dealer-slug> --verbose
   ```

2. Compare with the legacy parser to identify differences:
   ```bash
   python test-improved-parser.py <dealer-slug> --compare
   ```

3. Check the generated output files in the `test-output/` directory
