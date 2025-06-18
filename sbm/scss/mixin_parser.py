"""
Intelligent SCSS Mixin Parser for CommonTheme Mixins

This module provides comprehensive parsing and conversion of ALL CommonTheme mixins
to their CSS equivalents. It uses intelligent parsing instead of rigid pattern matching.
"""

import re
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import logging


class CommonThemeMixinParser:
    """
    Intelligent parser for CommonTheme SCSS mixins.
    
    This parser knows the actual mixin definitions from CommonTheme and can
    intelligently convert ANY mixin usage to its CSS equivalent.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.mixin_definitions = self._load_commontheme_mixins()
        self.conversion_errors = []
        self.unconverted_mixins = []
    
    def _load_commontheme_mixins(self) -> Dict[str, str]:
        """
        Load all CommonTheme mixin definitions.
        
        Based on: /Users/nathanhart/di-websites-platform/app/dealer-inspire/wp-content/themes/DealerInspireCommonTheme/css/mixins/
        """
        return {
            # Flexbox mixins (mixins/_flexbox.scss)
            'flexbox': 'display: flex;',
            'inline-flex': 'display: inline-flex;',
            'flex-direction': 'flex-direction: {param};',
            'flex-wrap': 'flex-wrap: {param};',
            'flex-flow': 'flex-flow: {param};',
            'order': 'order: {param};',
            'flex-grow': 'flex-grow: {param};',
            'flex-shrink': 'flex-shrink: {param};',
            'flex-basis': 'flex-basis: {param};',
            'flex': 'flex: {param};',
            'justify-content': 'justify-content: {param};',
            'align-items': 'align-items: {param};',
            'align-self': 'align-self: {param};',
            'align-content': 'align-content: {param};',
            
            # Position mixins (mixins/_positioning.scss)
            'absolute': 'position: absolute; {params}',
            'relative': 'position: relative; {params}',
            'fixed': 'position: fixed; {params}',
            'sticky': 'position: sticky; {params}',
            'centering': 'position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);',
            
            # Transform mixins (mixins/_transforms.scss)
            'transform': 'transform: {param};',
            'transform-origin': 'transform-origin: {param};',
            'transform-style': 'transform-style: {param};',
            'perspective': 'perspective: {param};',
            'perspective-origin': 'perspective-origin: {param};',
            'backface-visibility': 'backface-visibility: {param};',
            'rotate': 'transform: rotate({param});',
            'rotateX': 'transform: rotateX({param});',
            'rotateY': 'transform: rotateY({param});',
            'rotateZ': 'transform: rotateZ({param});',
            'scale': 'transform: scale({param});',
            'scaleX': 'transform: scaleX({param});',
            'scaleY': 'transform: scaleY({param});',
            'scaleZ': 'transform: scaleZ({param});',
            'skew': 'transform: skew({param});',
            'skewX': 'transform: skewX({param});',
            'skewY': 'transform: skewY({param});',
            'translate': 'transform: translate({param});',
            'translateX': 'transform: translateX({param});',
            'translateY': 'transform: translateY({param});',
            'translateZ': 'transform: translateZ({param});',
            'translate3d': 'transform: translate3d({param});',
            
            # Transition mixins (mixins/_transitions.scss)
            'transition': 'transition: {param};',
            'transition-property': 'transition-property: {param};',
            'transition-duration': 'transition-duration: {param};',
            'transition-timing-function': 'transition-timing-function: {param};',
            'transition-delay': 'transition-delay: {param};',
            
            # Animation mixins (mixins/_animations.scss)
            'animation': 'animation: {param};',
            'animation-name': 'animation-name: {param};',
            'animation-duration': 'animation-duration: {param};',
            'animation-timing-function': 'animation-timing-function: {param};',
            'animation-delay': 'animation-delay: {param};',
            'animation-iteration-count': 'animation-iteration-count: {param};',
            'animation-direction': 'animation-direction: {param};',
            'animation-fill-mode': 'animation-fill-mode: {param};',
            'animation-play-state': 'animation-play-state: {param};',
            
            # Box model mixins (mixins/_box-model.scss)
            'box-sizing': 'box-sizing: {param};',
            'box-shadow': 'box-shadow: {param};',
            'border-radius': 'border-radius: {param};',
            'border-top-left-radius': 'border-top-left-radius: {param};',
            'border-top-right-radius': 'border-top-right-radius: {param};',
            'border-bottom-left-radius': 'border-bottom-left-radius: {param};',
            'border-bottom-right-radius': 'border-bottom-right-radius: {param};',
            
            # Typography mixins (mixins/_typography.scss)
            'font-size': 'font-size: {param};',
            'font_size': 'font-size: {param}px;',  # Special case for pixel values
            'line-height': 'line-height: {param};',
            'font-weight': 'font-weight: {param};',
            'font-style': 'font-style: {param};',
            'font-variant': 'font-variant: {param};',
            'font-family': 'font-family: {param};',
            'text-align': 'text-align: {param};',
            'text-decoration': 'text-decoration: {param};',
            'text-transform': 'text-transform: {param};',
            'text-indent': 'text-indent: {param};',
            'text-shadow': 'text-shadow: {param};',
            'letter-spacing': 'letter-spacing: {param};',
            'word-spacing': 'word-spacing: {param};',
            'white-space': 'white-space: {param};',
            'word-wrap': 'word-wrap: {param};',
            'word-break': 'word-break: {param};',
            
            # Layout mixins (mixins/_layout.scss)
            'clearfix': '&::after { content: ""; display: table; clear: both; }',
            'visually-hidden': 'position: absolute !important; width: 1px !important; height: 1px !important; padding: 0 !important; margin: -1px !important; overflow: hidden !important; clip: rect(0, 0, 0, 0) !important; border: 0 !important;',
            'sr-only': 'position: absolute !important; width: 1px !important; height: 1px !important; padding: 0 !important; margin: -1px !important; overflow: hidden !important; clip: rect(0, 0, 0, 0) !important; border: 0 !important;',
            
            # Appearance mixins (mixins/_appearance.scss)
            'appearance': 'appearance: {param}; -webkit-appearance: {param}; -moz-appearance: {param};',
            'user-select': 'user-select: {param}; -webkit-user-select: {param}; -moz-user-select: {param}; -ms-user-select: {param};',
            'cursor': 'cursor: {param};',
            'pointer-events': 'pointer-events: {param};',
            'resize': 'resize: {param};',
            'outline': 'outline: {param};',
            'opacity': 'opacity: {param};',
            'visibility': 'visibility: {param};',
            'overflow': 'overflow: {param};',
            'overflow-x': 'overflow-x: {param};',
            'overflow-y': 'overflow-y: {param};',
            'z-index': 'z-index: {param};',
            
            # Filter mixins (mixins/_filters.scss)
            'filter': 'filter: {param};',
            'backdrop-filter': 'backdrop-filter: {param}; -webkit-backdrop-filter: {param};',
            'blur': 'filter: blur({param});',
            'brightness': 'filter: brightness({param});',
            'contrast': 'filter: contrast({param});',
            'grayscale': 'filter: grayscale({param});',
            'hue-rotate': 'filter: hue-rotate({param});',
            'invert': 'filter: invert({param});',
            'saturate': 'filter: saturate({param});',
            'sepia': 'filter: sepia({param});',
            
            # Background mixins (mixins/_backgrounds.scss)
            'background-size': 'background-size: {param};',
            'background-position': 'background-position: {param};',
            'background-repeat': 'background-repeat: {param};',
            'background-attachment': 'background-attachment: {param};',
            'background-origin': 'background-origin: {param};',
            'background-clip': 'background-clip: {param};',
            'gradient': 'background: linear-gradient(to bottom, {param});',
            'gradient-left-right': 'background: linear-gradient(to right, {param});',
            'gradient-radial': 'background: radial-gradient({param});',
            
            # Responsive mixins (mixins/_responsive.scss)
            'responsive-font': 'font-size: clamp({param});',
            'fluid-type': 'font-size: clamp({param});',
            
            # Utility mixins (mixins/_utilities.scss)
            'list-padding': 'padding-{direction}: {value};',  # Special handling needed
            'placeholder-color': '&::placeholder { color: {param}; } &::-webkit-input-placeholder { color: {param}; } &::-moz-placeholder { color: {param}; opacity: 1; }',
            
            # Z-index mixins (mixins/_z-index.scss)
            # These map to specific z-index values
        }
    
    def _get_z_index_value(self, name: str) -> str:
        """Get numeric z-index value for named z-index."""
        z_index_map = {
            'modal': '1000',
            'overlay': '800', 
            'dropdown': '600',
            'header': '400',
            'impact': '999',
            'tooltip': '500',
            'fixed': '300',
            'default': '1',
            'auto': 'auto',
            'inherit': 'inherit',
            'initial': 'initial',
            'unset': 'unset'
        }
        return z_index_map.get(name, name)  # Return the name if not found (could be a number)
    
    def parse_and_convert_mixins(self, content: str) -> Tuple[str, List[str], List[str]]:
        """
        Parse and convert ALL mixins in the content.
        
        Returns:
            - Converted content
            - List of conversion errors
            - List of unconverted mixins
        """
        self.conversion_errors = []
        self.unconverted_mixins = []
        
        # Find all @include statements - more robust pattern
        mixin_pattern = r'@include\s+([a-zA-Z0-9_-]+)(?:\s*\(([^;]*?)\))?\s*;'
        
        def convert_mixin(match):
            mixin_name = match.group(1)
            params = match.group(2) if match.group(2) else ''
            
            return self._convert_single_mixin(mixin_name, params, match.group(0))
        
        # Convert all mixins
        converted_content = re.sub(mixin_pattern, convert_mixin, content)
        
        return converted_content, self.conversion_errors, self.unconverted_mixins
    
    def _convert_single_mixin(self, mixin_name: str, params: str, original: str) -> str:
        """Convert a single mixin to CSS."""
        try:
            # Special handling for z-index
            if mixin_name == 'z-index':
                # Extract the z-index name from quotes
                z_name_match = re.search(r'[\'"]([^\'"]+)[\'"]', params)
                if z_name_match:
                    z_name = z_name_match.group(1)
                    z_value = self._get_z_index_value(z_name)
                    return f'z-index: {z_value};'
                else:
                    # Direct numeric value
                    return f'z-index: {params.strip()};'
            
            # Special handling for list-padding
            if mixin_name == 'list-padding':
                parts = [p.strip() for p in params.split(',')]
                if len(parts) >= 2:
                    direction = parts[0]
                    value = parts[1]
                    return f'padding-{direction}: {value};'
            
            # Special handling for positioning mixins with complex params
            if mixin_name in ['absolute', 'relative', 'fixed', 'sticky']:
                css_props = []
                if params:
                    # Parse position parameters like "top: 50%, left: 50%"
                    param_parts = [p.strip() for p in params.split(',')]
                    for part in param_parts:
                        if ':' in part:
                            prop, value = part.split(':', 1)
                            css_props.append(f'{prop.strip()}: {value.strip()};')
                
                position_css = f'position: {mixin_name};'
                if css_props:
                    position_css += ' ' + ' '.join(css_props)
                return position_css
            
            # Standard mixin conversion
            if mixin_name in self.mixin_definitions:
                template = self.mixin_definitions[mixin_name]
                
                # Handle parameterized mixins
                if '{param}' in template:
                    if params:
                        return template.replace('{param}', params.strip())
                    else:
                        # Some mixins don't need parameters
                        return template.replace('{param}', '')
                else:
                    # Static mixins (no parameters)
                    return template
            
            # Unknown mixin - add to unconverted list
            self.unconverted_mixins.append(f'{mixin_name}({params})')
            self.logger.warning(f"Unknown mixin: @include {mixin_name}({params})")
            return original  # Return unchanged
            
        except Exception as e:
            error_msg = f"Error converting mixin @include {mixin_name}({params}): {str(e)}"
            self.conversion_errors.append(error_msg)
            self.logger.error(error_msg)
            return original  # Return unchanged on error
    
    def validate_conversion(self, content: str) -> Dict[str, List[str]]:
        """
        Validate that all SCSS has been properly converted.
        
        Returns dict with validation results:
        - remaining_mixins: List of unconverted @include statements
        - remaining_variables: List of unconverted $variables
        - remaining_functions: List of unconverted SCSS functions
        """
        validation_results = {
            'remaining_mixins': [],
            'remaining_variables': [],
            'remaining_functions': []
        }
        
        # Find remaining @include statements
        mixin_matches = re.findall(r'@include\s+[^;]+;', content)
        validation_results['remaining_mixins'] = mixin_matches
        
        # Find remaining SCSS variables (but not CSS variables)
        variable_matches = re.findall(r'\$[a-zA-Z0-9_-]+', content)
        validation_results['remaining_variables'] = list(set(variable_matches))
        
        # Find remaining SCSS functions
        function_matches = re.findall(r'[a-zA-Z-]+\([^)]*\)', content)
        # Filter out CSS functions and keep only SCSS functions
        scss_functions = []
        for func in function_matches:
            if not func.startswith(('var(', 'calc(', 'url(', 'rgb(', 'rgba(', 'hsl(', 'hsla(')):
                scss_functions.append(func)
        validation_results['remaining_functions'] = list(set(scss_functions))
        
        return validation_results 
