"""
Intelligent SCSS Mixin Parser for CommonTheme Mixins

This module provides comprehensive parsing and conversion of ALL CommonTheme mixins
to their CSS equivalents. It uses intelligent parsing instead of rigid pattern matching.
"""

import re
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import logging


def _handle_border_radius(mixin_name, args, content):
    radius = args[0] if args else "5px"
    return f"border-radius: {radius};"

def _handle_font_size(mixin_name, args, content):
    size_px = args[0] if args else "16"
    size_rem = int(size_px) / 16
    return f"font-size: {size_px}px; /* {size_rem}rem */"

def _handle_placeholder(mixin_name, args, content):
    if not content:
        return ""
    
    # In SBM, we can often just output the raw content for placeholders
    return f"&::placeholder {{\n  {content.strip()}\n}}"

def _handle_button_variant(mixin_name, args, content):
    if len(args) < 3:
        return "" # Not enough args
    color = args[0]
    bg = args[1]
    border = args[2]
    return f"color: {color}; background-color: {bg}; border-color: {border};"

def _handle_button_size(mixin_name, args, content):
    if len(args) < 4:
        return ""
    padding_y = args[0]
    padding_x = args[1]
    font_size = args[2]
    border_radius = args[3]
    return f"padding: {padding_y} {padding_x}; font-size: {font_size}; border-radius: {border_radius};"

def _handle_content_block_mixin(mixin_name, args, content):
    """
    Generic handler for mixins that simply wrap a content block.
    This effectively "unwraps" the content by removing the @include.
    """
    if content:
        return content.strip()
    return ""

# Master dictionary mapping mixin names to their handler functions
MIXIN_TRANSFORMATIONS = {
    "border-radius": _handle_border_radius,
    "font-size": _handle_font_size,
    "placeholder": _handle_placeholder,
    # Handlers for Stellantis OEM Theme
    "button-variant": _handle_button_variant,
    "button-size": _handle_button_size,
    # Generic content block handler
    "pz-font-defaults": _handle_content_block_mixin,
}

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
        # More complex regex to handle nested parentheses and content blocks
        self.mixin_pattern = re.compile(
            r'@include\s+([\w-]+)\s*(?:\((.*?)\))?\s*({)?', re.DOTALL)
        self.brace_counter = 0
    
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
        Parses the SCSS content to find all @include statements and replaces
        them with their CSS equivalents based on CommonTheme definitions.
        """
        self.conversion_errors = []
        self.unconverted_mixins = []
        
        processed_content = self._find_and_replace_mixins(content)

        return processed_content, self.conversion_errors, self.unconverted_mixins
    
    def _find_and_replace_mixins(self, content: str) -> str:
        """Recursively finds and replaces mixins in the content."""
        
        # Use a replacer function with re.sub
        def replacer(match):
            mixin_name = match.group(1)
            raw_args = match.group(2)
            has_content_block = match.group(3) == '{'

            args = [arg.strip() for arg in raw_args.split(',')] if raw_args else []
            
            mixin_content = None
            if has_content_block:
                # If there's a content block, we need to find its end
                start_index = match.end()
                end_index, block_content = self._find_closing_brace(content, start_index)
                
                # The full text of the mixin call including its block
                full_mixin_text = content[match.start():end_index]
                mixin_content = block_content
            else:
                full_mixin_text = match.group(0)

            # Check for a function handler first
            if mixin_name in MIXIN_TRANSFORMATIONS:
                handler = MIXIN_TRANSFORMATIONS[mixin_name]
                # The handler is responsible for the entire replacement
                return handler(mixin_name, args, mixin_content)

            # Fallback to simple dictionary replacement if no handler
            if mixin_name in self.mixin_definitions:
                template = self.mixin_definitions[mixin_name]
                if '{param}' in template:
                    param = ", ".join(args)
                    return template.format(param=param)
                return template

            # If no conversion rule found, log it and return the original text
            self.logger.warning(f"Unknown mixin: {full_mixin_text[:80]}")
            self.unconverted_mixins.append(full_mixin_text)
            return full_mixin_text

        # We need a loop to handle nested mixins, recursively processing from the inside out.
        # A simple re.sub won't work for nesting. For now, we'll do one pass.
        # A more robust solution might require a proper parser.
        
        # For now, let's just use re.sub and see how far we get.
        # This will be revisited if nesting proves to be a major issue.
        processed_content = re.sub(self.mixin_pattern, replacer, content)

        # This logic is flawed for nesting. A better approach is needed.
        # Let's try to manually iterate through matches.
        
        output = ""
        last_index = 0
        for match in self.mixin_pattern.finditer(content):
            output += content[last_index:match.start()]
            
            mixin_name = match.group(1)
            raw_args = match.group(2)
            has_content_block = match.group(3) == '{'
            args = [arg.strip() for arg in raw_args.split(',')] if raw_args else []
            
            mixin_content = None
            full_mixin_original_text = match.group(0)
            
            end_of_match = match.end()

            if has_content_block:
                end_index, block_content = self._find_closing_brace(content, match.end())
                if end_index != -1:
                    mixin_content = block_content
                    # The full text including the block
                    full_mixin_original_text = content[match.start():end_index]
                    end_of_match = end_index # Move cursor past the block

            replacement = ""
            # Check for a function handler first
            if mixin_name in MIXIN_TRANSFORMATIONS:
                handler = MIXIN_TRANSFORMATIONS[mixin_name]
                replacement = handler(mixin_name, args, mixin_content)
            # Fallback to simple dictionary replacement
            elif mixin_name in self.mixin_definitions:
                template = self.mixin_definitions[mixin_name]
                param_str = ", ".join(args)
                replacement = template.format(param=param_str) # Basic replacement
            else:
                self.logger.warning(f"Unknown mixin: {full_mixin_original_text.splitlines()[0]}")
                self.unconverted_mixins.append(full_mixin_original_text)
                replacement = full_mixin_original_text
            
            output += replacement
            last_index = end_of_match

        output += content[last_index:]
        return output


    def _find_closing_brace(self, text: str, start_index: int) -> Tuple[int, str]:
        """Finds the matching closing brace for a block starting at start_index."""
        brace_level = 1
        for i in range(start_index, len(text)):
            if text[i] == '{':
                brace_level += 1
            elif text[i] == '}':
                brace_level -= 1
                if brace_level == 0:
                    # Return end index (after brace) and content (inside braces)
                    return i + 1, text[start_index:i]
        return -1, "" # Not found

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
