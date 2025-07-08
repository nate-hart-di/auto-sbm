I'll help you understand the map shortcode detection and map partial/style migration functionality. Let me search for relevant code related to map functionality in the repository.

Now let me get the detailed code for the core functions analyzer to understand how map shortcode detection works:

Now let me check how this is integrated into the workflow:

Now let me check the test files to understand the expected behavior better:

Now let me check the demo file to see what the expected output should be:

Now let me search for any configuration or settings related to map migration to understand potential issues:

Let me check the Config class to understand how the common_theme_dir is set up:

Now let me look for any error handling or debugging information by checking the actual usage of the functions analyzer:

Let me check if there are any recent test failures or issues by looking at the test runner files:

Now let me search for any specific issues with the path handling or file operations:

Based on my analysis of the code, I can now provide you with a comprehensive understanding of the map shortcode detection and migration functionality, along with potential issues and fixes.

## How Map Shortcode Detection Currently Works

The map shortcode detection and migration functionality is implemented in `sbm/core/functions_analyzer.py::FunctionsAnalyzer`. Here's how it works:

### 1. **Detection Process** (`sbm/core/functions_analyzer.py::FunctionsAnalyzer._find_map_shortcodes`)
- Scans `functions.php` for shortcodes containing keywords: "map", "direction", or "location"
- Uses regex patterns to find `add_shortcode()` calls
- Extracts shortcode name, definition, and template path
- Determines if the template references CommonTheme

### 2. **Migration Assessment** (`sbm/core/functions_analyzer.py::FunctionsAnalyzer._assess_migration_requirements`)
- Checks each detected map shortcode for CommonTheme references
- Identifies partials and SCSS files that need migration
- Creates migration plan with source/destination paths

### 3. **Migration Execution** (`sbm/core/functions_analyzer.py::FunctionsAnalyzer.migrate_map_dependencies`)
- Copies PHP partials from CommonTheme to dealer theme
- Migrates associated SCSS styles to `sb-inside.scss`

## Identified Issues

After analyzing the code, I found several potential problems:

### **Issue 1: Path Resolution Problems**
The `sbm/core/functions_analyzer.py::FunctionsAnalyzer._migrate_partial` method has a critical path resolution issue:

```python
source_path = self.config.common_theme_dir / partial_info["source_path"]
```

The problem is that `partial_info["source_path"]` often contains relative paths like `"../../DealerInspireCommonTheme/partials/map/dealer-map"`, but the code tries to join this with `common_theme_dir`, creating invalid paths.

### **Issue 2: SCSS Path Calculation**
The `sbm/core/functions_analyzer.py::FunctionsAnalyzer._find_associated_scss` method doesn't properly handle CommonTheme CSS directory structure.

### **Issue 3: Template Path Extraction**
The regex patterns in `sbm/core/functions_analyzer.py::FunctionsAnalyzer._extract_template_path` may not catch all template path variations.

## Proposed Fixes

Here are the specific fixes needed:

### **Fix 1: Correct Path Resolution in `_migrate_partial`**

The method needs to properly resolve CommonTheme paths:

```python
def _migrate_partial(self, theme_path: Path, partial_info: Dict[str, str], results: Dict[str, Any]) -> None:
    """Migrate a single partial file from CommonTheme to DealerTheme."""
    source_path_str = partial_info["source_path"]
    
    # Handle different CommonTheme path formats
    if "DealerInspireCommonTheme/" in source_path_str:
        # Extract relative path after DealerInspireCommonTheme/
        relative_path = source_path_str.split("DealerInspireCommonTheme/", 1)[1]
        source_path = self.config.common_theme_dir / relative_path
    elif source_path_str.startswith("../../DealerInspireCommonTheme/"):
        # Handle relative references
        relative_path = source_path_str.replace("../../DealerInspireCommonTheme/", "")
        source_path = self.config.common_theme_dir / relative_path
    else:
        # Direct path within CommonTheme
        source_path = self.config.common_theme_dir / source_path_str
    
    # Add .php extension if not present
    if not source_path.suffix:
        source_path = source_path.with_suffix('.php')
    
    destination_path = theme_path / partial_info["destination_path"]
    if not destination_path.suffix:
        destination_path = destination_path.with_suffix('.php')
    
    # Create destination directory if needed
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Copy the file
    if source_path.exists():
        destination_path.write_text(source_path.read_text())
        results["files_copied"].append(str(destination_path.relative_to(theme_path)))
        self.logger.info(f" Copied partial: {source_path_str}")
    else:
        self.logger.error(f" Source partial not found: {source_path}")
        raise FileNotFoundError(f"Source partial not found: {source_path}")
```

### **Fix 2: Improve SCSS Path Resolution in `_migrate_style`**

```python
def _migrate_style(self, theme_path: Path, style_path: str, results: Dict[str, Any]) -> None:
    """Migrate SCSS styles to sb-inside.scss."""
    # Try multiple potential SCSS locations
    potential_paths = [
        self.config.common_theme_dir / "css" / style_path,
        self.config.common_theme_dir / "scss" / style_path,
        self.config.common_theme_dir / style_path
    ]
    
    source_scss = None
    for path in potential_paths:
        if path.exists():
            source_scss = path
            break
    
    if not source_scss:
        self.logger.warning(f"  Associated SCSS not found in any location: {style_path}")
        # Try with underscore prefix for SCSS partials
        underscore_style = "_" + Path(style_path).name
        underscore_path = Path(style_path).parent / underscore_style
        for base_path in [self.config.common_theme_dir / "css", self.config.common_theme_dir / "scss"]:
            potential_underscore = base_path / underscore_path
            if potential_underscore.exists():
                source_scss = potential_underscore
                break
    
    if not source_scss:
        self.logger.warning(f"  SCSS file not found: {style_path}")
        return
    
    # Read the SCSS content
    scss_content = source_scss.read_text()
    
    # Add to sb-inside.scss
    sb_inside_path = theme_path / "sb-inside.scss"
    
    additional_content = f"""

/* MIGRATED FROM {style_path} **************************************************/

{scss_content}
"""
    
    # Append to sb-inside.scss
    with open(sb_inside_path, 'a') as f:
        f.write(additional_content)
    
    results["styles_migrated"].append(style_path)
    self.logger.info(f" Migrated SCSS: {style_path}")
```

### **Fix 3: Enhanced Template Path Extraction**

Update the `sbm/core/functions_analyzer.py::FunctionsAnalyzer._extract_template_path` method:

```python
def _extract_template_path(self, shortcode_def: str) -> Optional[str]:
    """Extract template path from shortcode definition."""
    # Look for get_template_part, include, or require statements
    patterns = [
        r"get_template_part\s*\(\s*['\"]([^'\"]*)['\"]",
        r"get_scoped_template_part\s*\(\s*['\"]([^'\"]*)['\"]",
        r"include\s*['\"]([^'\"]*\.php)['\"]",
        r"require\s*['\"]([^'\"]*\.php)['\"]",
        r"include_once\s*['\"]([^'\"]*\.php)['\"]",
        r"require_once\s*['\"]([^'\"]*\.php)['\"]"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, shortcode_def, re.IGNORECASE | re.DOTALL)
        if match:
            path = match.group(1).strip()
            # Clean up the path
            path = path.replace('\\', '/')  # Normalize path separators
            # Remove .php extension for get_template_part calls since they don't use it
            if "get_template_part" in pattern and path.endswith('.php'):
                path = path[:-4]
            return path
    
    return None
```

### **Fix 4: Add Better Error Handling and Debugging**

Add debugging information to help identify issues:

```python
def analyze_functions_file(self, theme_path: Path) -> Dict[str, Any]:
    """
    Analyze functions.php for map shortcodes and CommonTheme dependencies.
    """
    self.logger.info(f" Analyzing functions.php for map shortcodes and dependencies...")
    self.logger.debug(f" Theme path: {theme_path}")
    self.logger.debug(f" CommonTheme dir: {self.config.common_theme_dir}")
    
    functions_file = theme_path / "functions.php"
    if not functions_file.exists():
        self.logger.warning("  No functions.php file found")
        return self._empty_analysis_result()
    
    # ... rest of the method
```

## Testing the Fixes

To test these fixes, you should:

1. **Run the existing tests** to ensure they still pass:
   ```bash
   python -m pytest tests/test_functions_analyzer.py -v
   ```

2. **Test with a real dealer theme** that has map shortcodes:
   ```bash
   python test_sb_inside_demo.py
   ```

3. **Add debug logging** to see exactly what paths are being generated and accessed.

The main issues appear to be in path resolution and file discovery. The fixes I've provided should resolve the CommonTheme path handling problems and make the SCSS migration more robust.
