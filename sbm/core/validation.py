"""
Simplified validation engine for SBM Tool V2.

Focuses on essential validations: SCSS syntax errors and SBM guideline compliance.
"""

import os
import re
import subprocess
from typing import Dict, Any, List
from pathlib import Path

from sbm.config import Config
from sbm.utils.logger import get_logger
from sbm.utils.errors import ValidationError


class ValidationEngine:
    """Simplified validator for dealer themes - focuses on syntax and SBM compliance."""
    
    def __init__(self, config: Config):
        """Initialize validation engine."""
        self.config = config
        self.logger = get_logger("validation")
    
    def validate_theme(self, slug: str) -> Dict[str, Any]:
        """
        Basic validation - just check if theme exists.
        
        Args:
            slug: Dealer theme slug
            
        Returns:
            Validation results dictionary
        """
        self.logger.info(f"Validating theme: {slug}")
        
        theme_dir = self.config.di_platform_dir / "dealer-themes" / slug
        if not theme_dir.exists():
            return {
                "valid": False,
                "errors": [f"Theme directory not found: {theme_dir}"],
                "checks": {}
            }
        
        return {
            "valid": True,
            "checks": {
                "theme_exists": True
            }
        }
    
    def validate_migrated_files(self, slug: str) -> Dict[str, Any]:
        """
        Validate migrated SB files for syntax errors and SBM compliance.
        
        This is the ONLY validation that matters after migration:
        1. Check SCSS syntax errors
        2. Verify SBM guideline compliance for Stellantis
        
        Args:
            slug: Dealer theme slug
            
        Returns:
            Validation results with only essential checks
        """
        self.logger.info(f"Validating migrated files for {slug}...")
        
        theme_dir = self.config.di_platform_dir / "dealer-themes" / slug
        self.logger.info(f"Looking for theme files in: {theme_dir}")
        
        # Check if theme directory exists
        if not theme_dir.exists():
            self.logger.error(f"Theme directory not found: {theme_dir}")
            return {
                "scss_syntax": {"passed": False, "errors": [f"Theme directory not found: {theme_dir}"]},
                "sbm_compliance": {"passed": False, "issues": ["Theme directory missing"]},
                "overall": False
            }
        
        results = {
            "scss_syntax": {"passed": True, "errors": []},
            "sbm_compliance": {"passed": True, "issues": []},
            "overall": True
        }
        
        # 1. Check SCSS syntax errors in generated sb-*.scss files
        # Check BOTH theme root directory AND css subdirectory
        theme_scss_files = [
            theme_dir / "sb-inside.scss",
            theme_dir / "sb-vdp.scss", 
            theme_dir / "sb-vrp.scss"
        ]
        
        css_scss_files = [
            theme_dir / "css" / "sb-inside.scss",
            theme_dir / "css" / "sb-vdp.scss", 
            theme_dir / "css" / "sb-vrp.scss"
        ]
        
        # Combine all possible locations
        all_scss_files = theme_scss_files + css_scss_files
        
        self.logger.info("Checking for generated SCSS files in multiple locations:")
        self.logger.info(f"  Theme root: {theme_dir}")
        self.logger.info(f"  CSS subdir: {theme_dir / 'css'}")
        
        syntax_errors = []
        found_files = []
        
        for scss_file in all_scss_files:
            self.logger.info(f"  Checking: {scss_file}")
            if scss_file.exists():
                file_size = scss_file.stat().st_size
                relative_path = scss_file.relative_to(theme_dir)
                self.logger.success(f"    ✅ Found: {relative_path} ({file_size} bytes)")
                
                # Only process each unique filename once
                if scss_file.name not in found_files:
                    found_files.append(scss_file.name)
                    errors = self._check_scss_syntax(scss_file)
                    if errors:
                        syntax_errors.extend([f"{scss_file.name}: {error}" for error in errors])
                        self.logger.warning(f"    ⚠️  Syntax errors in {scss_file.name}: {errors}")
                    else:
                        self.logger.success(f"    ✅ Syntax OK: {scss_file.name}")
            else:
                self.logger.debug(f"    ❌ Not found: {scss_file.relative_to(theme_dir)}")
        
        # If no files found, show what files DO exist
        if not found_files:
            self.logger.warning("No sb-*.scss files found, checking what files exist:")
            existing_files = []
            if theme_dir.exists():
                existing_files.extend(theme_dir.glob("*.scss"))
            css_dir = theme_dir / "css"
            if css_dir.exists():
                existing_files.extend(css_dir.glob("*.scss"))
            
            if existing_files:
                self.logger.info(f"Found {len(existing_files)} other SCSS files:")
                for f in existing_files[:10]:  # Show first 10
                    relative_path = f.relative_to(theme_dir)
                    self.logger.info(f"    - {relative_path}")
        
        if syntax_errors:
            results["scss_syntax"]["passed"] = False
            results["scss_syntax"]["errors"] = syntax_errors
            results["overall"] = False
        
        # Show what files were actually found
        if found_files:
            self.logger.info(f"Found {len(found_files)} generated SCSS files: {', '.join(found_files)}")
        else:
            self.logger.warning("No generated sb-*.scss files found")
            
        # 2. Check SBM guideline compliance for Stellantis dealers
        if self._is_stellantis_dealer(slug):
            self.logger.info(f"Running Stellantis compliance checks for {slug}...")
            compliance_issues = self._check_stellantis_compliance(theme_dir)
            if compliance_issues:
                results["sbm_compliance"]["passed"] = False
                results["sbm_compliance"]["issues"] = compliance_issues
                results["overall"] = False
                self.logger.warning(f"Stellantis compliance issues: {compliance_issues}")
            else:
                self.logger.info("✅ Stellantis compliance checks passed")
        else:
            self.logger.info(f"Skipping Stellantis compliance checks for {slug} (not a Stellantis dealer)")
        
        # Report results
        if results["overall"]:
            self.logger.success("✅ All validation checks passed")
        else:
            self.logger.warning("⚠️  Validation issues found - review before proceeding")
            
        return results
    
    def _check_scss_syntax(self, scss_file: Path) -> List[str]:
        """Check SCSS file for syntax errors."""
        errors = []
        try:
            with open(scss_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Remove comments before checking quotes to avoid false positives
            # Remove /* */ block comments
            content_no_comments = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
            # Remove // line comments
            content_no_comments = re.sub(r'//.*?(?=\n|$)', '', content_no_comments, flags=re.MULTILINE)
            
            # Basic syntax checks
            if content.count('{') != content.count('}'):
                errors.append("Mismatched curly braces")
            
            if content.count('(') != content.count(')'):
                errors.append("Mismatched parentheses")
                
            # Check for unclosed strings (excluding comments)
            single_quotes = content_no_comments.count("'") - content_no_comments.count("\\'")
            double_quotes = content_no_comments.count('"') - content_no_comments.count('\\"')
            
            if single_quotes % 2 != 0:
                errors.append("Unclosed single quote")
            if double_quotes % 2 != 0:
                errors.append("Unclosed double quote")
            
            # Check for stray characters that commonly cause issues
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                line = line.strip()
                # Skip comment lines
                if line.startswith('//') or line.startswith('/*') or '*/' in line:
                    continue
                    
                if line.endswith('%') and not line.endswith('100%') and not any(x in line for x in ['width', 'height', 'font-size', '@media']):
                    errors.append(f"Line {i}: Stray '%' character at end of line")
                if line.endswith('&') and not line.endswith('&&'):
                    errors.append(f"Line {i}: Incomplete SCSS parent selector '&'")
                if line.count('@') > line.count('@media') + line.count('@import') + line.count('@include') + line.count('@mixin'):
                    errors.append(f"Line {i}: Possible invalid '@' character")
                    
        except Exception as e:
            errors.append(f"Failed to read file: {e}")
            
        return errors
    
    def _is_stellantis_dealer(self, slug: str) -> bool:
        """Check if dealer is Stellantis brand."""
        stellantis_brands = ['chrysler', 'dodge', 'jeep', 'ram', 'fiat', 'cdjr', 'fca']
        return any(brand in slug.lower() for brand in stellantis_brands)
    
    def _check_stellantis_compliance(self, theme_dir: Path) -> List[str]:
        """Check Stellantis-specific SBM compliance."""
        issues = []
        
        # Check both possible locations for sb-inside.scss
        sb_inside_locations = [
            theme_dir / "sb-inside.scss",
            theme_dir / "css" / "sb-inside.scss"
        ]
        
        sb_inside_file = None
        for location in sb_inside_locations:
            if location.exists():
                sb_inside_file = location
                break
        
        if sb_inside_file:
            try:
                with open(sb_inside_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for required map components for Stellantis
                if '#mapRow' not in content:
                    issues.append("Missing required #mapRow styles for Stellantis dealers")
                    
                if '#directionsBox' not in content:
                    issues.append("Missing required #directionsBox styles for Stellantis dealers")
                    
                # Check for proper responsive breakpoints (768px, 1024px - NOT 920px)
                if '920px' in content:
                    issues.append("Found non-standard 920px breakpoint - should use 768px or 1024px")
                    
            except Exception as e:
                issues.append(f"Failed to check sb-inside.scss: {e}")
        else:
            issues.append("Missing sb-inside.scss file")
            
        return issues


def validate_theme(slug: str, config: Config) -> Dict[str, Any]:
    """Legacy validation function for compatibility."""
    engine = ValidationEngine(config)
    return engine.validate_theme(slug)


def validate_scss(slug: str, config: Config) -> Dict[str, Any]:
    """Validate SCSS files for a theme - simplified to just syntax checks."""
    engine = ValidationEngine(config)
    
    # Just run the migrated file validation
    return engine.validate_migrated_files(slug) 
