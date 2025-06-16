"""
SCSS processor for SBM Tool V2.

Handles SCSS processing for migration workflow based on real Stellantis SBM patterns.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import re
from sbm.config import Config
from sbm.utils.logger import get_logger
from sbm.oem.factory import OEMHandlerFactory


class SCSSProcessor:
    """Handles SCSS processing for migration based on real SBM patterns."""
    
    def __init__(self, config: Config):
        """Initialize SCSS processor."""
        self.config = config
        self.logger = get_logger("scss")
        self.oem_factory = OEMHandlerFactory(config)
    
    def process_theme(self, slug: str) -> Dict[str, Any]:
        """
        Process SCSS for theme migration following real SBM patterns.
        
        Based on analysis of 20+ real Stellantis SBM PRs, this creates:
        - sb-inside.scss (new file with map components and general styles)
        - sb-vdp.scss (modified/new with VDP-specific styles)
        - sb-vrp.scss (modified/new with VRP-specific styles)
        """
        self.logger.info(f"Processing SCSS for {slug} using real SBM patterns")
        
        theme_path = self.config.get_theme_path(slug)
        if not theme_path.exists():
            raise FileNotFoundError(f"Theme directory not found: {theme_path}")
        
        results = {
            "success": True,
            "slug": slug,
            "files_created": [],
            "files_modified": [],
            "styles_migrated": 0,
            "map_components_added": False,
            "legacy_styles_preserved": []
        }
        
        # Process each Site Builder file
        results.update(self._create_sb_inside(theme_path, slug))
        results.update(self._process_sb_vdp(theme_path, slug))
        results.update(self._process_sb_vrp(theme_path, slug))
        
        self.logger.info(f"SCSS processing completed for {slug}")
        return results
    
    def _create_sb_inside(self, theme_path: Path, slug: str) -> Dict[str, Any]:
        """Create sb-inside.scss with map components and general styles."""
        sb_inside_path = theme_path / "sb-inside.scss"
        
        # Standard map components that appear in all real SBM PRs
        map_components = self._get_standard_map_components()
        
        # Extract any existing general styles from legacy files
        existing_styles = self._extract_general_styles(theme_path)
        
        # Get OEM-specific styles (FCA for Stellantis dealers)
        oem_handler = self.oem_factory.get_handler(slug)
        additional_styles = oem_handler.get_additional_styles("sb-inside")
        oem_styles_content = "\n\n".join(additional_styles) if additional_styles else ""
        
        content = f"""/*
\tSite Builder Inside Styles
\t- This file contains styles for general site components
\t- Includes map components and other shared styles
\t- You can check if it compiled here:
\t\twp-content > uploads > sb-asset-cache > sb-inside.css
*/

{existing_styles}

/* MAP ROW **************************************************/

#mapRow {{
\tposition: relative;
\t.mapwrap {{
\t\theight: 250px; /* Mobile first - 250px default */
\t}}
}}

#map-canvas {{
\theight:100%;
}}

/* DIRECTIONS BOX **************************************************/


#directionsBox {{
\tpadding: 50px 0;
\ttext-align: left;
\twidth: 400px;
\tposition: absolute;
\ttop:200px;
\tleft: 50px;
\tbackground: #fff;
\ttext-align: left;
\tcolor: #111;
\tfont-family: 'Lato', sans-serif;
\t.getdirectionstext {{
\t\tdisplay: inline-block;
\t\tfont-size: 24px;
\t\tmargin: 0;
\t}}
\t.locationtext {{
\t\ttext-transform: uppercase;
\t\tfont-weight: 700;
\t\tmargin-bottom: 20px;
\t}}
\t.address {{
\t\tmargin-bottom: 20px;
\t}}
}}

/* Responsive Breakpoints - Site Builder Standards */

/* Mobile default styles above */

/* Tablet - 768px and up */
@media (min-width: 768px) {{
\t#mapRow .mapwrap {{
\t\theight: 400px;
\t}}
}}

/* Desktop - 1024px and up */
@media (min-width: 1024px) {{
\t#mapRow .mapwrap {{
\t\theight: 600px;
\t}}
\t
\t#directionsBox {{
\t\tmax-width: 45%;
\t}}
}}

/* Mobile - below 768px */
@media (max-width: 767px) {{
\t#mapRow {{
\t\t.mapwrap {{
\t\t    height: 250px;
\t\t}}
\t\t#directionsBox {{
\t\t\twidth: unset;
\t\t\theight: 100%;
\t\t\ttop: 0;
\t\t\tleft: 0;
\t\t\tpadding: 20px;
\t\t\tmax-width: 90%;
\t\t}}
\t}}
}}

{oem_styles_content}"""
        
        # Write the file
        with open(sb_inside_path, 'w') as f:
            f.write(content.strip())
        
        return {
            "files_created": ["sb-inside.scss"],
            "map_components_added": True
        }
    
    def _process_sb_vdp(self, theme_path: Path, slug: str) -> Dict[str, Any]:
        """Process sb-vdp.scss with VDP-specific styles."""
        sb_vdp_path = theme_path / "sb-vdp.scss"
        
        # Extract VDP styles from legacy files
        vdp_styles = self._extract_vdp_styles(theme_path)
        
        # Create the complete file content with proper header
        content = f"""/*
\tLoads on Site Builder VDP (Classic OR HotWheels if DT Override is toggled on)

\tDocumentation: https://dealerinspire.atlassian.net/wiki/spaces/WDT/pages/498572582/SCSS+Set+Up

\t- After updating you'll need to generate the css in Site Builder settings
\t- You can check if it compiled here:
\t\twp-content > uploads > sb-asset-cache > sb-vdp.css
*/

{vdp_styles}"""
        
        # Always write the complete content (overwrite existing file)
        with open(sb_vdp_path, 'w') as f:
            f.write(content.strip())
        
        if sb_vdp_path.exists():
            return {"files_modified": ["sb-vdp.scss"]}
        else:
            return {"files_created": ["sb-vdp.scss"]}
    
    def _process_sb_vrp(self, theme_path: Path, slug: str) -> Dict[str, Any]:
        """Process sb-vrp.scss with VRP-specific styles."""
        sb_vrp_path = theme_path / "sb-vrp.scss"
        
        # Extract VRP styles from legacy files
        vrp_styles = self._extract_vrp_styles(theme_path)
        
        # Create the complete file content with proper header
        content = f"""/*
\tLoads on Site Builder VRP (Classic OR Lightning if DT Override is toggled on)

\tDocumentation: https://dealerinspire.atlassian.net/wiki/spaces/WDT/pages/498572582/SCSS+Set+Up

\t- After updating you'll need to generate the css in Site Builder settings
\t- You can check if it compiled here:
\t\twp-content > uploads > sb-asset-cache > sb-vrp.css
*/

{vrp_styles}"""
        
        # Always write the complete content (overwrite existing file)
        with open(sb_vrp_path, 'w') as f:
            f.write(content.strip())
        
        if sb_vrp_path.exists():
            return {"files_modified": ["sb-vrp.scss"]}
        else:
            return {"files_created": ["sb-vrp.scss"]}
    
    def _get_standard_map_components(self) -> str:
        """Get standard map components that appear in all SBM PRs."""
        return """/* MAP ROW **************************************************/

#mapRow {
\tposition: relative;
\t.mapwrap {
\t\theight: 600px;
\t}
}

#map-canvas {
\theight:100%;
}

/* DIRECTIONS BOX **************************************************/

#directionsBox {
\tpadding: 50px 0;
\ttext-align: left;
\twidth: 400px;
\tposition: absolute;
\ttop:200px;
\tleft: 50px;
\tbackground: #fff;
\ttext-align: left;
\tcolor: #111;
\tfont-family: 'Lato', sans-serif;
\t.getdirectionstext {
\t\tdisplay: inline-block;
\t\tfont-size: 24px;
\t\tmargin: 0;
\t}
\t.locationtext {
\t\ttext-transform: uppercase;
\t\tfont-weight: 700;
\t\tmargin-bottom: 20px;
\t}
\t.address {
\t\tmargin-bottom: 20px;
\t}
}

@media (max-width: 920px){
\t#mapRow {
\t\t.mapwrap {
\t\t    height: 250px;
\t\t}
\t\t#directionsBox {
\t\t\twidth: unset;
\t\t\theight: 100%;
\t\t\ttop: 0;
\t\t\tleft: 0;
\t\t\tpadding: 20px;
\t\t\tmax-width: 45%;
\t\t}
\t}
}"""
    
    def _extract_general_styles(self, theme_path: Path) -> str:
        """Extract general styles from legacy files for sb-inside.scss."""
        # Look for existing styles in legacy files - prioritize inside.scss and style.scss
        legacy_files = ["inside.scss", "style.scss", "home.scss", "custom.scss"]
        extracted_styles = []
        
        for legacy_file in legacy_files:
            file_path = theme_path / "css" / legacy_file
            if file_path.exists():
                self.logger.info(f"Extracting general styles from {legacy_file}")
                content = file_path.read_text()
                
                # For inside.scss, take most content (it's for inside pages)
                if legacy_file == "inside.scss":
                    # Remove imports and variables, keep the actual styles
                    filtered_content = self._filter_imports_and_variables(content)
                    if filtered_content.strip():
                        processed_styles = self._process_legacy_content(filtered_content)
                        extracted_styles.append(f"// Migrated from {legacy_file}")
                        extracted_styles.append(processed_styles)
                
                # For style.scss, extract non-header/footer/homepage styles
                elif legacy_file == "style.scss":
                    general_styles = self._filter_general_styles_from_main(content)
                    if general_styles.strip():
                        processed_styles = self._process_legacy_content(general_styles)
                        extracted_styles.append(f"// Migrated from {legacy_file}")
                        extracted_styles.append(processed_styles)
        
        return "\n\n".join(extracted_styles) if extracted_styles else ""
    
    def _extract_vdp_styles(self, theme_path: Path) -> str:
        """Extract VDP-specific styles from legacy files."""
        legacy_files = ["lvdp.scss", "vdp.scss"]
        extracted_styles = []
        
        for legacy_file in legacy_files:
            file_path = theme_path / "css" / legacy_file
            if file_path.exists():
                self.logger.info(f"Extracting VDP styles from {legacy_file}")
                content = file_path.read_text()
                
                # Remove imports and variables, keep the actual styles
                filtered_content = self._filter_imports_and_variables(content)
                if filtered_content.strip():
                    processed_styles = self._process_legacy_content(filtered_content)
                    extracted_styles.append(f"// Migrated from {legacy_file}")
                    extracted_styles.append(processed_styles)
        
        # Also extract VDP-specific styles from style.scss
        style_file = theme_path / "css" / "style.scss"
        if style_file.exists():
            content = style_file.read_text()
            vdp_styles = self._filter_vdp_styles_from_main(content)
            if vdp_styles.strip():
                processed_styles = self._process_legacy_content(vdp_styles)
                extracted_styles.append("// VDP styles migrated from style.scss")
                extracted_styles.append(processed_styles)
        
        return "\n\n".join(extracted_styles) if extracted_styles else ""
    
    def _extract_vrp_styles(self, theme_path: Path) -> str:
        """Extract VRP-specific styles from legacy files."""
        legacy_files = ["lvrp.scss", "vrp.scss"]
        extracted_styles = []
        
        for legacy_file in legacy_files:
            file_path = theme_path / "css" / legacy_file
            if file_path.exists():
                self.logger.info(f"Extracting VRP styles from {legacy_file}")
                content = file_path.read_text()
                
                # Remove imports and variables, keep the actual styles
                filtered_content = self._filter_imports_and_variables(content)
                if filtered_content.strip():
                    processed_styles = self._process_legacy_content(filtered_content)
                    extracted_styles.append(f"// Migrated from {legacy_file}")
                    extracted_styles.append(processed_styles)
        
        # Also extract VRP-specific styles from style.scss
        style_file = theme_path / "css" / "style.scss"
        if style_file.exists():
            content = style_file.read_text()
            vrp_styles = self._filter_vrp_styles_from_main(content)
            if vrp_styles.strip():
                processed_styles = self._process_legacy_content(vrp_styles)
                extracted_styles.append("// VRP styles migrated from style.scss")
                extracted_styles.append(processed_styles)
        
        return "\n\n".join(extracted_styles) if extracted_styles else ""

    def _filter_imports_and_variables(self, content: str) -> str:
        """Remove imports, variables, and comments, keep actual CSS/SCSS styles."""
        lines = content.split('\n')
        filtered_lines = []
        in_comment_block = False
        
        for line in lines:
            stripped = line.strip()
            
            # Skip empty lines
            if not stripped:
                continue
                
            # Handle multi-line comments
            if '/*' in stripped and '*/' not in stripped:
                in_comment_block = True
                continue
            if in_comment_block and '*/' in stripped:
                in_comment_block = False
                continue
            if in_comment_block:
                continue
                
            # Skip single-line comments
            if stripped.startswith('//'):
                continue
                
            # Skip imports
            if stripped.startswith('@import'):
                continue
                
            # Skip variable declarations (but keep CSS custom properties)
            if stripped.startswith('$') and ':' in stripped:
                continue
                
            # Keep everything else (actual styles)
            filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)

    def _filter_general_styles_from_main(self, content: str) -> str:
        """Extract general/inside page styles from style.scss, excluding header/footer/homepage."""
        # Remove imports and variables first
        filtered_content = self._filter_imports_and_variables(content)
        
        # Split into sections and filter out header/footer/homepage sections
        lines = filtered_content.split('\n')
        filtered_lines = []
        skip_section = False
        
        for line in lines:
            stripped = line.strip().lower()
            
            # Check for sections to skip
            if any(keyword in stripped for keyword in [
                'header', 'footer', 'navigation', 'navbar', 'homepage', 'home page',
                'prefooter', 'device header', 'algolia search'
            ]):
                # If it's a comment indicating a section, skip this section
                if stripped.startswith('//') or stripped.startswith('/*'):
                    skip_section = True
                    continue
            
            # Reset skip when we hit a new section comment
            if (stripped.startswith('//') or stripped.startswith('/*')) and 'custom' in stripped:
                skip_section = False
            
            # Include line if we're not skipping
            if not skip_section:
                filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)

    def _filter_vdp_styles_from_main(self, content: str) -> str:
        """Extract VDP-specific styles from style.scss."""
        # Look for VDP-related patterns in the content
        vdp_patterns = [
            r'#vehicleDetails.*?(?=\n\s*[#\.]|\n\s*$|$)',
            r'\.vdp-.*?(?=\n\s*[#\.]|\n\s*$|$)',
            r'#price-box.*?(?=\n\s*[#\.]|\n\s*$|$)',
            r'#ctabox.*?(?=\n\s*[#\.]|\n\s*$|$)',
            r'\.calculate-your-payment.*?(?=\n\s*[#\.]|\n\s*$|$)'
        ]
        
        extracted = []
        for pattern in vdp_patterns:
            matches = re.findall(pattern, content, re.DOTALL | re.MULTILINE)
            extracted.extend(matches)
        
        return "\n\n".join(extracted) if extracted else ""

    def _filter_vrp_styles_from_main(self, content: str) -> str:
        """Extract VRP-specific styles from style.scss."""
        # Look for VRP-related patterns in the content
        vrp_patterns = [
            r'#results-page.*?(?=\n\s*[#\.]|\n\s*$|$)',
            r'#lvrp-results-wrapper.*?(?=\n\s*[#\.]|\n\s*$|$)',
            r'\.vehicle.*?(?=\n\s*[#\.]|\n\s*$|$)',
            r'\.hit.*?(?=\n\s*[#\.]|\n\s*$|$)',
            r'\.lightning.*?(?=\n\s*[#\.]|\n\s*$|$)',
            r'\.result-wrap.*?(?=\n\s*[#\.]|\n\s*$|$)'
        ]
        
        extracted = []
        for pattern in vrp_patterns:
            matches = re.findall(pattern, content, re.DOTALL | re.MULTILINE)
            extracted.extend(matches)
        
        return "\n\n".join(extracted) if extracted else ""

    def _process_legacy_content(self, content: str) -> str:
        """
        Process legacy SCSS content to be Site Builder compatible.
        
        This includes:
        - Replacing mixins with CSS equivalents
        - Updating breakpoints to standard values
        - Converting to CSS variables where appropriate
        """
        processed = content
        
        # Replace common mixins with CSS equivalents
        mixin_replacements = {
            # Flexbox mixins
            '@include flexbox();': 'display: flex;',
            '@include inline-flex();': 'display: inline-flex;',
            '@include flex-direction(row);': 'flex-direction: row;',
            '@include flex-direction(column);': 'flex-direction: column;',
            '@include flex-wrap(wrap);': 'flex-wrap: wrap;',
            '@include flex-wrap(nowrap);': 'flex-wrap: nowrap;',
            '@include align-items(center);': 'align-items: center;',
            '@include align-items(flex-start);': 'align-items: flex-start;',
            '@include align-items(flex-end);': 'align-items: flex-end;',
            '@include align-items(stretch);': 'align-items: stretch;',
            '@include justify-content(center);': 'justify-content: center;',
            '@include justify-content(space-between);': 'justify-content: space-between;',
            '@include justify-content(space-around);': 'justify-content: space-around;',
            '@include justify-content(flex-start);': 'justify-content: flex-start;',
            '@include justify-content(flex-end);': 'justify-content: flex-end;',
            
            # Transform & Transition mixins
            '@include transition(all 0.3s);': 'transition: all 0.3s;',
            '@include transition(all 0.2s);': 'transition: all 0.2s;',
            '@include transition(all 0.5s);': 'transition: all 0.5s;',
            
            # Box model mixins (specific values only - variables handled by regex)
            '@include box-sizing(border-box);': 'box-sizing: border-box;',
            '@include box-sizing(content-box);': 'box-sizing: content-box;',
            
            # Appearance mixins
            '@include appearance(none);': 'appearance: none; -webkit-appearance: none; -moz-appearance: none;',
            
            # Utility mixins
            '@include clearfix();': '&::after { content: ""; display: table; clear: both; }',
            '@include visually-hidden();': 'position: absolute !important; width: 1px !important; height: 1px !important; padding: 0 !important; margin: -1px !important; overflow: hidden !important; clip: rect(0, 0, 0, 0) !important; border: 0 !important;',
            
            # Placeholder styling
            '@include placeholder-color;': '&::placeholder { color: var(--placeholder-color, #999); } &::-webkit-input-placeholder { color: var(--placeholder-color, #999); } &::-moz-placeholder { color: var(--placeholder-color, #999); opacity: 1; }',
        }
        
        # Apply basic mixin replacements (but skip commented lines)
        lines = processed.split('\n')
        processed_lines = []
        
        for line in lines:
            stripped = line.strip()
            # Skip commented lines
            if stripped.startswith('//') or stripped.startswith('/*'):
                processed_lines.append(line)
                continue
            
            # Apply replacements to non-commented lines
            processed_line = line
            for mixin, css in mixin_replacements.items():
                processed_line = processed_line.replace(mixin, css)
            processed_lines.append(processed_line)
        
        processed = '\n'.join(processed_lines)
        
        # Handle more complex mixin patterns with regex
        import re
        
        # Replace positioning mixins
        processed = re.sub(
            r'@include absolute\(\(([^)]+)\)\);',
            lambda m: f'position: absolute; {self._parse_position_params(m.group(1))}',
            processed
        )
        
        processed = re.sub(
            r'@include relative\(\(([^)]+)\)\);',
            lambda m: f'position: relative; {self._parse_position_params(m.group(1))}',
            processed
        )
        
        processed = re.sub(
            r'@include fixed\(\(([^)]+)\)\);',
            lambda m: f'position: fixed; {self._parse_position_params(m.group(1))}',
            processed
        )
        
        # Replace centering mixin
        processed = re.sub(
            r'@include centering\(both\);',
            'position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);',
            processed
        )
        
        # Replace transform mixins (avoid commented lines)
        processed = re.sub(
            r'@include rotate\(([^;]+)\);',
            r'transform: rotate(\1);',
            processed
        )
        
        processed = re.sub(
            r'@include transform\(([^;]+)\);',
            r'transform: \1;',
            processed
        )
        
        # Replace border-radius mixins (including variables)
        processed = re.sub(
            r'@include border-radius\(([^;]+)\);',
            r'border-radius: \1;',
            processed
        )
        
        # Replace transition mixins (including variables)
        processed = re.sub(
            r'@include transition\(([^;]+)\);',
            r'transition: \1;',
            processed
        )
        
        # Replace font-size mixins
        processed = re.sub(
            r'@include font_size\((\d+)\);',
            r'font-size: \1px;',
            processed
        )
        
        # Replace list-padding mixins
        processed = re.sub(
            r'@include list-padding\(left,\s*([^;]+)\);',
            r'padding-left: \1;',
            processed
        )
        
        processed = re.sub(
            r'@include list-padding\(right,\s*([^;]+)\);',
            r'padding-right: \1;',
            processed
        )
        
        processed = re.sub(
            r'@include list-padding\(top,\s*([^;]+)\);',
            r'padding-top: \1;',
            processed
        )
        
        processed = re.sub(
            r'@include list-padding\(bottom,\s*([^;]+)\);',
            r'padding-bottom: \1;',
            processed
        )
        
        # Replace box-shadow mixins
        processed = re.sub(
            r'@include box-shadow\(([^;]+)\);',
            r'box-shadow: \1;',
            processed
        )
        
        # Replace animation mixins
        processed = re.sub(
            r'@include animation\([\'"]?([^\'";]+)[\'"]?\);',
            r'animation: \1;',
            processed
        )
        
        # Replace filter mixins
        processed = re.sub(
            r'@include filter\(([^;]+)\);',
            r'filter: \1;',
            processed
        )
        
        # Replace box-sizing mixins (with variables)
        processed = re.sub(
            r'@include box-sizing\(([^;]+)\);',
            r'box-sizing: \1;',
            processed
        )
        
        # Replace placeholder-color mixins with custom color
        processed = re.sub(
            r'@include placeholder-color\(([^;]+)\);',
            r'&::placeholder { color: \1; } &::-webkit-input-placeholder { color: \1; } &::-moz-placeholder { color: \1; opacity: 1; }',
            processed
        )
        
        # Replace responsive font mixins
        processed = re.sub(
            r'@include responsive-font\(([^,]+),\s*([^,]+),\s*([^;]+)\);',
            r'font-size: clamp(\2, \1, \3);',
            processed
        )
        
        # Replace z-index mixins with specific values
        z_index_map = {
            'modal': '1000',
            'overlay': '800',
            'dropdown': '600',
            'header': '400',
            'default': '1'
        }
        
        for name, value in z_index_map.items():
            processed = re.sub(
                rf'@include z-index\("{name}"\);',
                f'z-index: {value};',
                processed
            )
        
        # Replace gradient mixins
        processed = re.sub(
            r'@include gradient\(([^,]+),\s*([^;]+)\);',
            r'background: linear-gradient(to bottom, \1, \2);',
            processed
        )
        
        processed = re.sub(
            r'@include gradient-left-right\(([^,]+),\s*([^;]+)\);',
            r'background: linear-gradient(to right, \1, \2);',
            processed
        )
        
        # Replace breakpoint mixins with CommonTheme definitions
        # Based on /Users/nathanhart/di-websites-platform/app/dealer-inspire/wp-content/themes/DealerInspireCommonTheme/css/mixins/_breakpoints.scss
        breakpoint_map = {
            'xxs': '@media (max-width:320px)',
            'xs': '@media (max-width:767px)',
            'mobile-tablet': '@media (max-width:1024px)',
            'tablet-only': '@media (min-width:768px) and (max-width:1024px)',
            'sm': '@media (min-width:768px)',
            'md': '@media (min-width:1025px)',
            'lg': '@media (min-width:1200px)',
            'xl': '@media (min-width:1400px)',
            'sm-desktop': '@media (max-width:1199px)'
        }
        
        for name, media_query in breakpoint_map.items():
            processed = re.sub(
                rf"@include breakpoint\(['\"]?{name}['\"]?\)\s*{{",
                f'{media_query} {{',
                processed
            )
        
        # NOTE: Explicit media queries should migrate AS-IS
        # Only @include breakpoint() mixins should be replaced with CommonTheme definitions
        
        # Update image paths to use /wp-content/ format
        processed = re.sub(
            r"url\(['\"]?\.\.\/images\/([^'\"]*)['\"]?\)",
            r"url('/wp-content/themes/DealerInspireDealerTheme/images/\1')",
            processed
        )
        
        # Clean up any css/../ paths that might have been created
        processed = re.sub(
            r"/wp-content/themes/DealerInspireDealerTheme/css/\.\./images/",
            r"/wp-content/themes/DealerInspireDealerTheme/images/",
            processed
        )
        
        # Convert SCSS variables to CSS custom properties
        scss_variable_map = {
            '$primary': 'var(--primary)',
            '$secondary': 'var(--secondary)', 
            '$cta': 'var(--cta)',
            '$primaryhover': 'var(--primaryhover)',
            '$secondaryhover': 'var(--secondaryhover)',
            '$ctahover': 'var(--ctahover)',
            '$white': 'var(--white)',
            '$black': 'var(--black)',
            '$gray': 'var(--gray)',
            '$light-gray': 'var(--light-gray)',
            '$dark-gray': 'var(--dark-gray)',
        }
        
        for scss_var, css_var in scss_variable_map.items():
            # Use proper pattern for SCSS variables ($ is not a word character)
            # Look for the variable followed by semicolon, space, or end of line
            processed = re.sub(
                rf'{re.escape(scss_var)}(?=\s*[;\s]|$)',
                css_var,
                processed
            )
        
        # Convert darken() functions to actual hex values
        darken_conversions = {
            'darken(#008000,10%)': '#006600',  # Green darkened by 10%
            'darken(#008000, 10%)': '#006600',
            'darken(#2095cb, 10%)': '#1a7ba8',  # Blue darkened by 10%
            'darken(#2095cb,10%)': '#1a7ba8',
            'darken($primary, 10%)': 'var(--primaryhover)',
            'darken($primary,10%)': 'var(--primaryhover)',
            'darken($secondary, 10%)': 'var(--secondaryhover)',
            'darken($secondary,10%)': 'var(--secondaryhover)',
            'darken($cta, 10%)': 'var(--ctahover)',
            'darken($cta,10%)': 'var(--ctahover)',
        }
        
        for darken_func, replacement in darken_conversions.items():
            processed = processed.replace(darken_func, replacement)
        
        # Convert SCSS functions to CSS equivalents
        # Convert em() function to rem values (assuming 16px base)
        processed = re.sub(
            r'\bem\((\d+)\)',
            lambda m: f'{float(m.group(1)) / 16:.3f}rem',
            processed
        )
        
        # Convert get-mobile-size() function to direct pixel values
        processed = re.sub(
            r'get-mobile-size\(([^)]+)\)',
            r'\1',
            processed
        )
        
        # Convert common hex colors to CSS variables with fallbacks
        hex_color_map = {
            # Standard grayscale colors
            '#fff': 'var(--white, #fff)',
            '#ffffff': 'var(--white, #ffffff)',
            '#000': 'var(--black, #000)',
            '#000000': 'var(--black, #000000)',
            '#111': 'var(--hex-111, #111)',
            '#222': 'var(--hex-222, #222)',
            '#333': 'var(--hex-333, #333)',
            '#444': 'var(--hex-444, #444)',
            '#555': 'var(--hex-555, #555)',
            '#666': 'var(--hex-666, #666)',
            '#777': 'var(--hex-777, #777)',
            '#888': 'var(--hex-888, #888)',
            '#999': 'var(--hex-999, #999)',
            '#aaa': 'var(--hex-aaa, #aaa)',
            '#bbb': 'var(--hex-bbb, #bbb)',
            '#ccc': 'var(--hex-ccc, #ccc)',
            '#cccccc': 'var(--hex-cccccc, #cccccc)',
            '#ddd': 'var(--hex-ddd, #ddd)',
            '#eee': 'var(--hex-eee, #eee)',
            
            # Common brand/theme colors found in dealer sites
            '#008001': 'var(--green-008001, #008001)',  # Common green
            '#32CD32': 'var(--lime-green, #32CD32)',      # Lime green
            '#e20000': 'var(--red-e20000, #e20000)',      # Red
            '#093382': 'var(--blue-093382, #093382)',     # Dark blue
            '#1a5490': 'var(--blue-1a5490, #1a5490)',    # Medium blue
            '#f8f9fa': 'var(--light-gray-f8f9fa, #f8f9fa)', # Light gray
            '#e9ecef': 'var(--light-gray-e9ecef, #e9ecef)', # Light gray
            '#f1f3f4': 'var(--light-gray-f1f3f4, #f1f3f4)', # Light gray
            '#e8eaed': 'var(--light-gray-e8eaed, #e8eaed)', # Light gray
            '#1a1a1a': 'var(--dark-gray-1a1a1a, #1a1a1a)', # Dark gray
            '#f7f7f7': 'var(--light-gray-f7f7f7, #f7f7f7)', # Very light gray
            '#afafaf': 'var(--gray-afafaf, #afafaf)',     # Medium gray
            
            # Additional common hex patterns (6-character versions)
            '#111111': 'var(--hex-111111, #111111)',
            '#222222': 'var(--hex-222222, #222222)',
            '#333333': 'var(--hex-333333, #333333)',
            '#444444': 'var(--hex-444444, #444444)',
            '#555555': 'var(--hex-555555, #555555)',
            '#666666': 'var(--hex-666666, #666666)',
            '#777777': 'var(--hex-777777, #777777)',
            '#888888': 'var(--hex-888888, #888888)',
            '#999999': 'var(--hex-999999, #999999)',
            '#aaaaaa': 'var(--hex-aaaaaa, #aaaaaa)',
            '#bbbbbb': 'var(--hex-bbbbbb, #bbbbbb)',
            '#dddddd': 'var(--hex-dddddd, #dddddd)',
            '#eeeeee': 'var(--hex-eeeeee, #eeeeee)',
        }
        
        for hex_color, css_var in hex_color_map.items():
            # Use proper pattern for hex colors (# is not a word character)
            # Look for the hex color followed by semicolon, space, or end of line
            processed = re.sub(
                rf'{re.escape(hex_color)}(?=\s*[;\s]|$)',
                css_var,
                processed,
                flags=re.IGNORECASE
            )
        
        return processed
    
    def _parse_position_params(self, params: str) -> str:
        """Parse position parameters from mixin calls."""
        # Simple parser for position parameters like "top:0, left:0"
        result = []
        for param in params.split(','):
            param = param.strip()
            if ':' in param:
                prop, value = param.split(':', 1)
                result.append(f'{prop.strip()}: {value.strip()};')
        return ' '.join(result)

    def _filter_general_styles(self, content: str) -> str:
        """Filter content for general styles (not VDP/VRP specific) - DEPRECATED, use _filter_general_styles_from_main."""
        return self._filter_general_styles_from_main(content)
    
    def _filter_vdp_styles(self, content: str) -> str:
        """Filter content for VDP-specific styles - DEPRECATED, use _filter_vdp_styles_from_main."""
        return self._filter_vdp_styles_from_main(content)
    
    def _filter_vrp_styles(self, content: str) -> str:
        """Filter content for VRP-specific styles - DEPRECATED, use _filter_vrp_styles_from_main."""
        return self._filter_vrp_styles_from_main(content)
