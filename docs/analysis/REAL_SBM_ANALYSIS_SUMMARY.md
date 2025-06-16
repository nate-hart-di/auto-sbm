# Real SBM Pattern Analysis & Script Updates

## Analysis Summary

After analyzing **20+ real Stellantis Site Builder Migration PRs** from the `carsdotcom/di-websites-platform` repository, I discovered the actual patterns used in production SBM migrations and updated the automation script accordingly.

## Key Findings from Real PRs

### 1. **Consistent File Structure**

Every SBM PR creates/modifies exactly **3 files**:

- `dealer-themes/{dealername}/sb-inside.scss` (always created new)
- `dealer-themes/{dealername}/sb-vdp.scss` (modified or created)
- `dealer-themes/{dealername}/sb-vrp.scss` (modified or created)

### 2. **Standard PR Patterns**

- **Title Format**: `{dealername} SBM FE Audit`
- **Branch Naming**: `{dealername}-SBM{MMDD}` format
- **Labels**: Consistently tagged with "fe-dev, Themes"
- **PR Description**: Standardized "What/Why/Instructions for Reviewers" template

### 3. **Map Components (Universal)**

Every `sb-inside.scss` file contains identical map components:

- `#mapRow` with 600px height
- `#map-canvas` with 100% height
- `#directionsBox` with specific positioning (400px width, absolute positioning)
- Responsive breakpoint at 920px (mobile: 250px height, 45% max-width)

### 4. **Content Migration Patterns**

- **sb-inside.scss**: Map components + general site styles
- **sb-vdp.scss**: Vehicle Detail Page specific styles (extracted from legacy files)
- **sb-vrp.scss**: Vehicle Results Page specific styles (extracted from legacy files)

## PRs Analyzed

Analyzed 20+ PRs including:

- #12574 (libertyjeepchrysler), #12572 (firkinscdjr), #12570 (scottpetersonmotor)
- #12558 (towbindodge), #12556 (universitycjdr), #12216 (Marshall CDJR)
- #12212 (Tacoma CDJR), #12361 (maseratiofnaperville), #12134 (Sewell CDJR)
- And many more...

## Script Updates Made

### 1. **Updated SCSS Processor** (`sbm/scss/processor.py`)

- **Real Pattern Implementation**: Now creates the exact 3-file structure found in real PRs
- **Map Components**: Adds the standard map components found in every real SBM
- **Style Extraction**: Implements pattern-based extraction of VDP/VRP styles from legacy files
- **File Headers**: Uses the exact header comments found in real PRs

### 2. **Updated Migration Script** (`sbm/core/migration.py`)

- **Real Workflow**: Follows the actual 5-step process used in production
- **Error Handling**: Improved error handling and result tracking
- **Integration**: Properly integrates the new SCSS processor

### 3. **New Test Suite** (`tests/test_real_sbm_patterns.py`)

- **Pattern Validation**: Tests that automation matches real PR patterns
- **File Structure**: Validates the 3-file creation pattern
- **Map Components**: Verifies exact map component implementation
- **Content Patterns**: Tests style extraction and file headers

## Key Technical Details

### Map Component Specifications (from real PRs):

```scss
#mapRow {
  position: relative;
  .mapwrap {
    height: 600px; // Standard desktop height
  }
}

#directionsBox {
  width: 400px; // Standard width
  top: 200px; // Standard positioning
  left: 50px;
  font-family: 'Lato', sans-serif; // Most common font
}

@media (max-width: 920px) {
  // Exact breakpoint from PRs
  #mapRow .mapwrap {
    height: 250px; // Mobile height
  }
  #directionsBox {
    max-width: 45%; // Mobile responsive
  }
}
```

### File Headers (exact from real PRs):

```scss
/*
    Site Builder VDP Styles
    - This file contains styles specific to the Vehicle Detail Page (VDP)
    - These styles are compiled and loaded only on VDP pages
    - You can check if it compiled here:
        wp-content > uploads > sb-asset-cache > sb-vdp.css
*/
```

## Validation Results

All new tests pass, confirming the automation now matches real-world patterns:

- ✅ Creates exactly 3 Site Builder files
- ✅ Includes standard map components with correct specifications
- ✅ Uses exact responsive breakpoints (920px)
- ✅ Implements proper file headers
- ✅ Preserves existing styles when files already exist
- ✅ Extracts legacy styles using pattern recognition

## Impact

The script now automates the **exact same process** that developers perform manually in real SBM PRs, ensuring:

1. **Consistency** with production patterns
2. **Reliability** based on proven real-world implementations
3. **Completeness** covering all aspects found in actual PRs
4. **Accuracy** matching exact specifications and formatting

This analysis transformed the script from a theoretical implementation to a **production-ready automation** that replicates the actual SBM process used by the development team.
