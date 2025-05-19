# Testing OEM Module Support

This document outlines how to test the OEM modular support in the Site Builder Migration (SBM) tool.

## 1. Testing With Stellantis/CDJR Dealer

For Stellantis/CDJR dealers (Chrysler, Dodge, Jeep, Ram, Fiat), the tool should automatically detect the OEM and apply the appropriate styles.

```bash
# Let the tool auto-detect (recommended)
./sbm.sh chryslerdodgejeepram123

# Or manually specify the OEM
./sbm.sh chryslerdodgejeepram123 --oem=stellantis
```

Expected behavior:

- The OEM factory should detect the brand from the dealer slug
- Stellantis-specific map partial patterns should be used to find maps
- Stellantis-specific styles should be added to sb-inside.scss
- Log messages should indicate "Using StellantisHandler for <slug>"

## 2. Testing With Non-Stellantis Dealer

For dealers of other brands, the tool should automatically fall back to the DefaultHandler.

```bash
# Let the tool auto-detect
./sbm.sh toyota123

# Or manually specify the default handler
./sbm.sh toyota123 --oem=default
```

Expected behavior:

- The OEM factory should not match any specific handler and use DefaultHandler
- Default generic map partial patterns should be used to find maps
- Default generic map styles should be added to sb-inside.scss
- Log messages should indicate "Using DefaultHandler for <slug>"

## 3. Running Unit Tests

Unit tests have been added to validate the OEM factory and handler functionality:

```bash
# Navigate to the auto-sbm directory
cd /Users/nathanhart/auto-sbm

# Run the tests
python -m unittest tests/test_oem_factory.py
```

The tests verify:

- Brand detection for Stellantis brands
- Slug-based detection for Stellantis dealers
- Fallback to DefaultHandler for unknown brands
- Correct pattern matching for each handler
- Proper style generation

## 4. Command-Line Options

The new OEM support adds the following command-line option:

### Python Module Usage

```bash
python -m sbm.cli stellantis < dealer-slug > --oem
```

### Shell Script Usage

```bash
./sbm.sh < dealer-slug > --oem=stellantis
```

## 5. Future OEM Implementation

When implementing support for additional OEMs:

1. Create a new handler class in the `sbm/oem/` directory
2. Add the handler to the OEMFactory.\_handlers list
3. Provide OEM-specific style files in a dedicated directory
4. Run tests to ensure the new handler is properly detected

For detailed instructions, refer to the [OEM module documentation](sbm/oem/README.md).

## 6. Troubleshooting

If the OEM detection isn't working as expected:

1. Enable verbose logging with `--verbose`
2. Check the log output for messages about OEM detection
3. Verify that the brand match patterns in your handler match the dealer slug or brand information
4. Manually specify the OEM with `--oem=<name>` to bypass automatic detection
