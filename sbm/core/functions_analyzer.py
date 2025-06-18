"""
Functions.php analyzer for SBM Tool V2.

Analyzes dealer theme functions.php files for map shortcodes and other CommonTheme dependencies
that need to be migrated during the SBM process.
"""

import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from sbm.config import Config
from sbm.utils.logger import get_logger


class FunctionsAnalyzer:
    """
    Analyzes functions.php files for map shortcodes and CommonTheme dependencies.
    
    This class identifies shortcodes that reference CommonTheme partials and determines
    what needs to be migrated to maintain functionality after SBM migration.
    """
    
    def __init__(self, config: Config):
        """Initialize the functions analyzer."""
        self.config = config
        self.logger = get_logger("functions_analyzer")
    
    def analyze_functions_file(self, theme_path: Path) -> Dict[str, Any]:
        """
        Analyze functions.php for map shortcodes and CommonTheme dependencies.
        
        Args:
            theme_path: Path to the dealer theme directory
            
        Returns:
            Analysis results containing shortcode information and migration requirements
        """
        self.logger.info("🔍 Analyzing functions.php for map shortcodes and dependencies...")
        
        functions_file = theme_path / "functions.php"
        if not functions_file.exists():
            self.logger.warning("⚠️  No functions.php file found")
            return self._empty_analysis_result()
        
        try:
            with open(functions_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self.logger.error(f"❌ Failed to read functions.php: {e}")
            return self._empty_analysis_result()
        
        # Analyze the content
        analysis = {
            "functions_file_exists": True,
            "map_shortcodes": self._find_map_shortcodes(content),
            "commontheme_dependencies": self._find_commontheme_dependencies(content),
            "migration_required": False,
            "partials_to_migrate": [],
            "styles_to_migrate": [],
            "warnings": [],
            "recommendations": []
        }
        
        # Determine migration requirements
        self._assess_migration_requirements(analysis, theme_path)
        
        return analysis
    
    def _find_map_shortcodes(self, content: str) -> List[Dict[str, str]]:
        """Find map-related shortcodes in functions.php content."""
        shortcodes = []
        
        # Pattern to match add_shortcode calls with map-related names
        map_patterns = [
            r"add_shortcode\s*\(\s*['\"]([^'\"]*map[^'\"]*)['\"]",  # Contains "map"
            r"add_shortcode\s*\(\s*['\"]([^'\"]*direction[^'\"]*)['\"]",  # Contains "direction"
            r"add_shortcode\s*\(\s*['\"]([^'\"]*location[^'\"]*)['\"]",  # Contains "location"
        ]
        
        for pattern in map_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                shortcode_name = match.group(1)
                
                # Find the complete shortcode definition
                start_pos = match.start()
                brace_count = 0
                in_function = False
                end_pos = start_pos
                
                for i, char in enumerate(content[start_pos:], start_pos):
                    if char == '{':
                        brace_count += 1
                        in_function = True
                    elif char == '}':
                        brace_count -= 1
                        if in_function and brace_count == 0:
                            end_pos = i + 1
                            break
                
                shortcode_def = content[start_pos:end_pos]
                template_path = self._extract_template_path(shortcode_def)
                
                shortcodes.append({
                    "name": shortcode_name,
                    "definition": shortcode_def,
                    "template_path": template_path,
                    "is_commontheme_reference": self._is_commontheme_reference(template_path)
                })
        
        return shortcodes
    
    def _find_commontheme_dependencies(self, content: str) -> List[Dict[str, str]]:
        """Find references to CommonTheme partials and includes."""
        dependencies = []
        
        # Pattern to match get_template_part calls with CommonTheme paths
        template_patterns = [
            r"get_template_part\s*\(\s*['\"]([^'\"]*partials[^'\"]*)['\"]",
            r"get_scoped_template_part\s*\(\s*['\"]([^'\"]*partials[^'\"]*)['\"]",
            r"include[^;]*['\"]([^'\"]*DealerInspireCommonTheme[^'\"]*)['\"]",
            r"require[^;]*['\"]([^'\"]*DealerInspireCommonTheme[^'\"]*)['\"]"
        ]
        
        for pattern in template_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                path = match.group(1)
                dependencies.append({
                    "path": path,
                    "type": "template_part" if "get_template_part" in match.group(0) else "include",
                    "full_match": match.group(0)
                })
        
        return dependencies
    
    def _extract_template_path(self, shortcode_def: str) -> Optional[str]:
        """Extract template path from shortcode definition."""
        # Look for get_template_part, include, or require statements
        patterns = [
            r"get_template_part\s*\(\s*['\"]([^'\"]*)['\"]",
            r"get_scoped_template_part\s*\(\s*['\"]([^'\"]*)['\"]",
            r"include\s*['\"]([^'\"]*\.php)['\"]",
            r"require\s*['\"]([^'\"]*\.php)['\"]"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, shortcode_def, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _is_commontheme_reference(self, template_path: Optional[str]) -> bool:
        """Check if template path references CommonTheme."""
        if not template_path:
            return False
        
        # Check for CommonTheme references
        commontheme_indicators = [
            "DealerInspireCommonTheme",
            "../../DealerInspireCommonTheme",
            "../DealerInspireCommonTheme"
        ]
        
        return any(indicator in template_path for indicator in commontheme_indicators)
    
    def _assess_migration_requirements(self, analysis: Dict[str, Any], theme_path: Path) -> None:
        """Assess what migration steps are required based on the analysis."""
        migration_needed = False
        
        # Check each map shortcode
        for shortcode in analysis["map_shortcodes"]:
            if shortcode["is_commontheme_reference"]:
                migration_needed = True
                analysis["partials_to_migrate"].append({
                    "shortcode": shortcode["name"],
                    "source_path": shortcode["template_path"],
                    "destination_path": self._calculate_destination_path(shortcode["template_path"])
                })
                
                # Check for associated SCSS files
                scss_path = self._find_associated_scss(shortcode["template_path"])
                if scss_path:
                    analysis["styles_to_migrate"].append(scss_path)
            else:
                # Local partial - check if it exists
                local_partial = theme_path / "partials" / f"{shortcode['template_path']}.php"
                if not local_partial.exists():
                    analysis["warnings"].append(
                        f"Shortcode '{shortcode['name']}' references missing partial: {shortcode['template_path']}"
                    )
        
        # Check CommonTheme dependencies
        for dep in analysis["commontheme_dependencies"]:
            if "partials" in dep["path"]:
                migration_needed = True
                analysis["partials_to_migrate"].append({
                    "type": "dependency",
                    "source_path": dep["path"], 
                    "destination_path": self._calculate_destination_path(dep["path"])
                })
        
        analysis["migration_required"] = migration_needed
        
        # Add recommendations
        if migration_needed:
            analysis["recommendations"].append(
                "Map shortcodes reference CommonTheme partials that need migration"
            )
            analysis["recommendations"].append(
                "Run SBM with map migration option to copy required partials and styles"
            )
        else:
            analysis["recommendations"].append(
                "No CommonTheme map dependencies found - migration can proceed normally"
            )
    
    def _calculate_destination_path(self, source_path: str) -> str:
        """Calculate destination path in DealerTheme for a CommonTheme partial."""
        # Remove CommonTheme prefix if present
        if "DealerInspireCommonTheme/" in source_path:
            relative_path = source_path.split("DealerInspireCommonTheme/", 1)[1]
        else:
            relative_path = source_path
        
        # Ensure it starts with partials/ if it's a partial
        if not relative_path.startswith("partials/") and "partials/" in relative_path:
            # Extract the partials portion
            partials_index = relative_path.find("partials/")
            relative_path = relative_path[partials_index:]
        
        return relative_path
    
    def _find_associated_scss(self, template_path: str) -> Optional[str]:
        """Find SCSS file associated with a template partial."""
        # Convert template path to potential SCSS path
        if template_path.endswith(".php"):
            scss_path = template_path[:-4] + ".scss"
        else:
            scss_path = template_path + ".scss"
        
        # Add underscore prefix for SCSS partials
        path_parts = scss_path.split("/")
        if path_parts:
            filename = path_parts[-1]
            if not filename.startswith("_"):
                path_parts[-1] = "_" + filename
                scss_path = "/".join(path_parts)
        
        return scss_path
    
    def _empty_analysis_result(self) -> Dict[str, Any]:
        """Return empty analysis result when functions.php doesn't exist."""
        return {
            "functions_file_exists": False,
            "map_shortcodes": [],
            "commontheme_dependencies": [],
            "migration_required": False,
            "partials_to_migrate": [],
            "styles_to_migrate": [],
            "warnings": ["No functions.php file found"],
            "recommendations": ["No map shortcode analysis possible - check if map styles exist in style.scss"]
        }
    
    def migrate_map_dependencies(self, theme_path: Path, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate map-related partials and styles identified in the analysis.
        
        Args:
            theme_path: Path to the dealer theme directory
            analysis: Results from analyze_functions_file
            
        Returns:
            Migration results
        """
        if not analysis["migration_required"]:
            self.logger.info("✅ No map migration required")
            return {
                "success": True,
                "files_copied": [],
                "styles_migrated": [],
                "message": "No migration required"
            }
        
        self.logger.info("🚀 Starting map dependency migration...")
        
        results = {
            "success": True,
            "files_copied": [],
            "styles_migrated": [],
            "errors": []
        }
        
        # Migrate partials
        for partial in analysis["partials_to_migrate"]:
            try:
                self._migrate_partial(theme_path, partial, results)
            except Exception as e:
                self.logger.error(f"❌ Failed to migrate partial {partial['source_path']}: {e}")
                results["errors"].append(f"Partial migration failed: {partial['source_path']}")
                results["success"] = False
        
        # Migrate styles
        for style_path in analysis["styles_to_migrate"]:
            try:
                self._migrate_style(theme_path, style_path, results)
            except Exception as e:
                self.logger.error(f"❌ Failed to migrate style {style_path}: {e}")
                results["errors"].append(f"Style migration failed: {style_path}")
        
        if results["success"]:
            self.logger.success("✅ Map dependency migration completed successfully")
        else:
            self.logger.error("❌ Map dependency migration completed with errors")
        
        return results
    
    def _migrate_partial(self, theme_path: Path, partial_info: Dict[str, str], results: Dict[str, Any]) -> None:
        """Migrate a single partial file from CommonTheme to DealerTheme."""
        source_path = self.config.common_theme_dir / partial_info["source_path"] 
        destination_path = theme_path / partial_info["destination_path"]
        
        # Create destination directory if needed
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy the file
        if source_path.exists():
            destination_path.write_text(source_path.read_text())
            results["files_copied"].append(str(destination_path.relative_to(theme_path)))
            self.logger.info(f"✅ Copied partial: {partial_info['source_path']}")
        else:
            raise FileNotFoundError(f"Source partial not found: {source_path}")
    
    def _migrate_style(self, theme_path: Path, style_path: str, results: Dict[str, Any]) -> None:
        """Migrate SCSS styles to sb-inside.scss."""
        source_scss = self.config.common_theme_dir / "css" / style_path
        
        if not source_scss.exists():
            self.logger.warning(f"⚠️  Associated SCSS not found: {source_scss}")
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
        self.logger.info(f"✅ Migrated SCSS: {style_path}") 
