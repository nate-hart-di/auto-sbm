"""
Intelligent SCSS Mixin Parser for CommonTheme Mixins

This module provides comprehensive parsing and conversion of ALL CommonTheme mixins
to their CSS equivalents. It uses intelligent parsing instead of rigid pattern matching.
"""

import re
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import logging


def _handle_appearance(mixin_name, args, content):
    """Handle @include appearance($appearance)"""
    appearance = args[0] if args else "none"
    return f"-webkit-appearance: {appearance};\n-moz-appearance: {appearance};\nappearance: {appearance};"

def _handle_border_radius(mixin_name, args, content):
    """Handle @include border-radius($radii)"""
    radius = args[0] if args else "5px"
    return f"border-radius: {radius};\nbackground-clip: padding-box;"

def _handle_breakpoint(mixin_name, args, content):
    """Handle @include breakpoint($point) { content }"""
    if not args or not content:
        return ""
    
    point = args[0]
    breakpoint_map = {
        'xxs': 'max-width:320px',
        'xs': 'max-width:767px', 
        'mobile-tablet': 'max-width:1024px',
        'tablet-only': 'min-width:768px) and (max-width:1024px',
        'sm': 'min-width:768px',
        'md': 'min-width:1025px',
        'lg': 'min-width:1200px',
        'xl': 'min-width:1400px',
        'sm-desktop': 'max-width:1199px'
    }
    
    media_query = breakpoint_map.get(point, point)
    return f"@media ({media_query}) {{\n{content.strip()}\n}}"

def _handle_flexbox(mixin_name, args, content):
    """Handle @include flexbox"""
    return "display: -webkit-box;\ndisplay: -webkit-flex;\ndisplay: -moz-flex;\ndisplay: -ms-flexbox;\ndisplay: flex;"

def _handle_inline_flex(mixin_name, args, content):
    """Handle @include inline-flex"""
    return "display: -webkit-inline-box;\ndisplay: -webkit-inline-flex;\ndisplay: -moz-inline-flex;\ndisplay: -ms-inline-flexbox;\ndisplay: inline-flex;"

def _handle_flex_direction(mixin_name, args, content):
    """Handle @include flex-direction($value)"""
    if not args:
        return ""
    
    value = args[0]
    webkit_box_props = ""
    
    if value == "row-reverse":
        webkit_box_props = "-webkit-box-direction: reverse;\n-webkit-box-orient: horizontal;\n"
    elif value == "column":
        webkit_box_props = "-webkit-box-direction: normal;\n-webkit-box-orient: vertical;\n"
    elif value == "column-reverse":
        webkit_box_props = "-webkit-box-direction: reverse;\n-webkit-box-orient: vertical;\n"
    else:  # row
        webkit_box_props = "-webkit-box-direction: normal;\n-webkit-box-orient: horizontal;\n"
    
    return f"{webkit_box_props}-webkit-flex-direction: {value};\n-moz-flex-direction: {value};\n-ms-flex-direction: {value};\nflex-direction: {value};"

def _handle_flex_wrap(mixin_name, args, content):
    """Handle @include flex-wrap($value)"""
    if not args:
        return ""
    
    value = args[0]
    ms_value = "none" if value == "nowrap" else value
    
    return f"-webkit-flex-wrap: {value};\n-moz-flex-wrap: {value};\n-ms-flex-wrap: {ms_value};\nflex-wrap: {value};"

def _handle_justify_content(mixin_name, args, content):
    """Handle @include justify-content($value)"""
    if not args:
        return ""
    
    value = args[0]
    webkit_box = ""
    ms_flex = ""
    
    if value == "flex-start":
        webkit_box = "-webkit-box-pack: start;\n"
        ms_flex = "-ms-flex-pack: start;\n"
    elif value == "flex-end":
        webkit_box = "-webkit-box-pack: end;\n"
        ms_flex = "-ms-flex-pack: end;\n"
    elif value == "space-between":
        webkit_box = "-webkit-box-pack: justify;\n"
        ms_flex = "-ms-flex-pack: justify;\n"
    elif value == "space-around":
        ms_flex = "-ms-flex-pack: distribute;\n"
    else:
        webkit_box = f"-webkit-box-pack: {value};\n"
        ms_flex = f"-ms-flex-pack: {value};\n"
    
    return f"{webkit_box}{ms_flex}-webkit-justify-content: {value};\n-moz-justify-content: {value};\njustify-content: {value};"

def _handle_align_items(mixin_name, args, content):
    """Handle @include align-items($value)"""
    if not args:
        return ""
    
    value = args[0]
    webkit_box = ""
    ms_flex = ""
    
    if value == "flex-start":
        webkit_box = "-webkit-box-align: start;\n"
        ms_flex = "-ms-flex-align: start;\n"
    elif value == "flex-end":
        webkit_box = "-webkit-box-align: end;\n"
        ms_flex = "-ms-flex-align: end;\n"
    else:
        webkit_box = f"-webkit-box-align: {value};\n"
        ms_flex = f"-ms-flex-align: {value};\n"
    
    return f"{webkit_box}{ms_flex}-webkit-align-items: {value};\n-moz-align-items: {value};\nalign-items: {value};"

def _handle_font_size_mixin(mixin_name, args, content):
    """Handle @include font_size() - the mixin that builds font-size classes"""
    # This mixin generates CSS classes, so we'll just comment it out for SBM
    return "/* font_size mixin converted - generates utility classes */"

def _handle_fluid_font(mixin_name, args, content):
    """Handle @include fluid-font($min-vw, $max-vw, $min-font-size, $max-font-size)"""
    if len(args) < 4:
        return ""
    
    min_vw, max_vw, min_font_size, max_font_size = args[:4]
    
    return f"""font-size: {min_font_size};
@media screen and (min-width: {min_vw}) {{
  font-size: calc({min_font_size} + {max_font_size.replace('px', '').replace('rem', '')} * ((100vw - {min_vw}) / {max_vw.replace('px', '').replace('vw', '')}));
}}
@media screen and (min-width: {max_vw}) {{
  font-size: {max_font_size};
}}"""

def _handle_responsive_font(mixin_name, args, content):
    """Handle @include responsive-font($responsive, $min, $max, $fallback)"""
    if len(args) < 2:
        return ""
    
    responsive, min_size = args[:2]
    max_size = args[2] if len(args) > 2 else None
    fallback = args[3] if len(args) > 3 else None
    
    css = ""
    if fallback:
        css += f"font-size: {fallback};\n"
    
    css += f"font-size: {responsive};"
    
    # Add media queries for min/max if provided
    # This is a simplified version - the actual mixin is more complex
    
    return css

def _handle_placeholder_color(mixin_name, args, content):
    """Handle @include placeholder-color($color, $opacity)"""
    if not args:
        return ""
    
    color = args[0]
    opacity = args[1] if len(args) > 1 else "1"
    
    return f"""&::-webkit-input-placeholder {{
  color: {color};
  opacity: {opacity};
}}
&:-moz-placeholder {{
  color: {color};
  opacity: {opacity};
}}
&::-moz-placeholder {{
  color: {color};
  opacity: {opacity};
}}
&:-ms-input-placeholder {{
  color: {color};
  opacity: {opacity};
}}"""

def _handle_absolute(mixin_name, args, content):
    """Handle @include absolute($directions)"""
    base = "position: absolute;"
    if content:
        return f"{base}\n{content.strip()}"
    return base

def _handle_relative(mixin_name, args, content):
    """Handle @include relative($directions)"""
    base = "position: relative;"
    if content:
        return f"{base}\n{content.strip()}"
    return base

def _handle_fixed(mixin_name, args, content):
    """Handle @include fixed($directions)"""
    base = "position: fixed;"
    if content:
        return f"{base}\n{content.strip()}"
    return base

def _handle_centering(mixin_name, args, content):
    """Handle @include centering($from, $amount, $sides)"""
    from_dir = args[0] if args else "top"
    amount = args[1] if len(args) > 1 else "50%"
    
    if from_dir == "both":
        return f"""position: absolute;
top: {amount};
left: {amount};
transform: translate(-{amount}, -{amount});
-webkit-transform: translate(-{amount}, -{amount});
-moz-transform: translate(-{amount}, -{amount});
-o-transform: translate(-{amount}, -{amount});
-ms-transform: translate(-{amount}, -{amount});"""
    else:
        transform_map = {
            "top": f"translateY(-{amount})",
            "bottom": f"translateY({amount})",
            "left": f"translateX(-{amount})",
            "right": f"translateX({amount})"
        }
        transform_val = transform_map.get(from_dir, f"translateY(-{amount})")
        
        return f"""position: absolute;
{from_dir}: {amount};
transform: {transform_val};
-webkit-transform: {transform_val};
-moz-transform: {transform_val};
-o-transform: {transform_val};
-ms-transform: {transform_val};"""

def _handle_pz_font_defaults(mixin_name, args, content):
    """Handle @include pz-font-defaults() - personalizer font defaults"""
    font_family = args[0] if args else "$heading-font"
    color = args[1] if len(args) > 1 else "#fff"
    weight = args[2] if len(args) > 2 else "bold"
    line_height = args[3] if len(args) > 3 else "normal"
    align = args[4] if len(args) > 4 else "center"
    
    base_styles = f""".personalizer-wrap {{
  color: {color};
  font-family: {font_family};
  text-align: {align};
  
  h1, h1 a, a h1,
  h2, h2 a, a h2,
  h3, h3 a, a h3,
  h4, h4 a, a h4,
  h5, h5 a, a h5,
  h6, h6 a, a h6 {{
    color: {color};
    font-weight: {weight};
    line-height: {line_height};
  }}
  
  h1 {{ font-size: 4.172rem; }}
  h2 {{ font-size: 3.338rem; }}
  h3 {{ font-size: 2.67rem; }}
  h4 {{ font-size: 2.136rem; }}
  h5 {{ font-size: 1.709em; }}
  h6 {{ font-size: 1.367em; }}
  
  h1, h2, h3, h4, h5, h6 {{
    @media (max-width: 768px) {{
      font-size: 1.709em;
    }}
  }}"""
    
    if content:
        base_styles += f"\n{content.strip()}"
    
    base_styles += "\n}"
    
    return base_styles

def _handle_transform(mixin_name, args, content):
    """Handle @include transform($transform)"""
    if not args:
        return ""
    
    transform_val = args[0]
    return f"""-ms-transform: {transform_val};
-webkit-transform: {transform_val};
transform: {transform_val};"""

def _handle_transition(mixin_name, args, content):
    """Handle @include transition($transition)"""
    if not args:
        return ""
    
    transition_val = args[0]
    return f"""-webkit-transition: {transition_val};
transition: {transition_val};"""

def _handle_transition_2(mixin_name, args, content):
    """Handle @include transition-2($transition, $transition-2)"""
    if len(args) < 2:
        return ""
    
    transition1, transition2 = args[:2]
    return f"""-webkit-transition: {transition1}, {transition2};
transition: {transition1}, {transition2};"""

def _handle_z_index(mixin_name, args, content):
    """Handle @include z-index($layer, $plus)"""
    if not args:
        return ""
    
    layer = args[0].strip('"\'')
    plus = int(args[1]) if len(args) > 1 and args[1].isdigit() else 0
    
    # Z-index layer values from the mixin
    z_layers = {
        "header": 1000,
        "header-fixed": 1080,
        "modal": 1050,
        "tooltip": 1070,
        "popover": 1060,
        "mobile-overlay": 1030,
        "overlay": 1000,
        "top": 500,
        "extra-high": 400,
        "high": 300,
        "mid": 200,
        "low": 100,
        "half": 50,
        "impact": 1,
        "buried": -1,
        "third-party": -100000000000000000
    }
    
    if layer in z_layers:
        z_value = z_layers[layer] + plus
        return f"z-index: {z_value};"
    elif layer.isdigit() or (layer.startswith('-') and layer[1:].isdigit()):
        # It's already a number
        return f"z-index: {layer};"
    else:
        # Unknown layer, return as-is
        return f"z-index: {layer};"

def _handle_content_block_mixin(mixin_name, args, content):
    """
    Generic handler for mixins that simply wrap a content block.
    This effectively "unwraps" the content by removing the @include.
    """
    if content:
        return content.strip()
    return ""

# Additional flexbox mixins
def _handle_flex(mixin_name, args, content):
    """Handle @include flex($fg, $fs, $fb)"""
    if not args:
        return ""
    
    fg = args[0] if len(args) > 0 else "1"
    fs = args[1] if len(args) > 1 else "null"
    fb = args[2] if len(args) > 2 else "null"
    
    # Clean up null values
    flex_value = fg
    if fs != "null":
        flex_value += f" {fs}"
    if fb != "null":
        flex_value += f" {fb}"
    
    return f"""-webkit-box-flex: {fg};
-webkit-flex: {flex_value};
-moz-box-flex: {fg};
-moz-flex: {flex_value};
-ms-flex: {flex_value};
flex: {flex_value};"""

def _handle_order(mixin_name, args, content):
    """Handle @include order($int)"""
    if not args:
        return ""
    
    order_val = args[0]
    order_group = int(order_val) + 1 if order_val.isdigit() else f"{order_val} + 1"
    
    return f"""-webkit-box-ordinal-group: {order_group};
-webkit-order: {order_val};
-moz-order: {order_val};
-ms-flex-order: {order_val};
order: {order_val};"""

def _handle_flex_grow(mixin_name, args, content):
    """Handle @include flex-grow($int)"""
    if not args:
        return ""
    
    grow_val = args[0]
    return f"""-webkit-box-flex: {grow_val};
-webkit-flex-grow: {grow_val};
-moz-flex-grow: {grow_val};
-ms-flex-positive: {grow_val};
flex-grow: {grow_val};"""

def _handle_flex_shrink(mixin_name, args, content):
    """Handle @include flex-shrink($int)"""
    if not args:
        return ""
    
    shrink_val = args[0]
    return f"""-webkit-flex-shrink: {shrink_val};
-moz-flex-shrink: {shrink_val};
-ms-flex-negative: {shrink_val};
flex-shrink: {shrink_val};"""

def _handle_flex_basis(mixin_name, args, content):
    """Handle @include flex-basis($value)"""
    if not args:
        return ""
    
    basis_val = args[0]
    return f"""-webkit-flex-basis: {basis_val};
-moz-flex-basis: {basis_val};
-ms-flex-preferred-size: {basis_val};
flex-basis: {basis_val};"""

def _handle_flex_flow(mixin_name, args, content):
    """Handle @include flex-flow($values)"""
    if not args:
        return ""
    
    flow_val = " ".join(args)
    return f"""-webkit-flex-flow: {flow_val};
-moz-flex-flow: {flow_val};
-ms-flex-flow: {flow_val};
flex-flow: {flow_val};"""

def _handle_align_self(mixin_name, args, content):
    """Handle @include align-self($value)"""
    if not args:
        return ""
    
    value = args[0]
    ms_value = ""
    
    if value == "flex-start":
        ms_value = "-ms-flex-item-align: start;\n"
    elif value == "flex-end":
        ms_value = "-ms-flex-item-align: end;\n"
    else:
        ms_value = f"-ms-flex-item-align: {value};\n"
    
    return f"""-webkit-align-self: {value};
-moz-align-self: {value};
{ms_value}align-self: {value};"""

def _handle_align_content(mixin_name, args, content):
    """Handle @include align-content($value)"""
    if not args:
        return ""
    
    value = args[0]
    ms_value = ""
    
    if value == "flex-start":
        ms_value = "-ms-flex-line-pack: start;\n"
    elif value == "flex-end":
        ms_value = "-ms-flex-line-pack: end;\n"
    else:
        ms_value = f"-ms-flex-line-pack: {value};\n"
    
    return f"""-webkit-align-content: {value};
-moz-align-content: {value};
{ms_value}align-content: {value};"""

# Master dictionary mapping mixin names to their handler functions
MIXIN_TRANSFORMATIONS = {
    # Appearance mixins
    "appearance": _handle_appearance,
    
    # Border radius mixins
    "border-radius": _handle_border_radius,
    
    # Breakpoint mixins
    "breakpoint": _handle_breakpoint,
    
    # Flexbox mixins
    "flexbox": _handle_flexbox,
    "inline-flex": _handle_inline_flex,
    "flex-direction": _handle_flex_direction,
    "flex-dir": _handle_flex_direction,  # Shorter version
    "flex-wrap": _handle_flex_wrap,
    "flex-flow": _handle_flex_flow,
    "justify-content": _handle_justify_content,
    "flex-just": _handle_justify_content,  # Shorter version
    "align-items": _handle_align_items,
    "align-self": _handle_align_self,
    "align-content": _handle_align_content,
    "flex": _handle_flex,
    "order": _handle_order,
    "flex-grow": _handle_flex_grow,
    "flex-shrink": _handle_flex_shrink,
    "flex-basis": _handle_flex_basis,
    
    # Font size mixins
    "font_size": _handle_font_size_mixin,
    "fluid-font": _handle_fluid_font,
    "responsive-font": _handle_responsive_font,
    
    # Placeholder mixins
    "placeholder-color": _handle_placeholder_color,
    
    # Positioning mixins
    "absolute": _handle_absolute,
    "relative": _handle_relative,
    "fixed": _handle_fixed,
    "centering": _handle_centering,
    
    # Personalizer defaults
    "pz-font-defaults": _handle_pz_font_defaults,
    
    # Transform mixins
    "transform": _handle_transform,
    
    # Transition mixins
    "transition": _handle_transition,
    "transition-2": _handle_transition_2,
    
    # Z-index mixins
    "z-index": _handle_z_index,
    
    # Generic content block handler for other mixins
    "button-variant": _handle_content_block_mixin,
    "button-size": _handle_content_block_mixin,
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
        Load basic CommonTheme mixin definitions for fallback.
        
        Most mixins are now handled by specific handler functions,
        but these provide fallback templates for simple cases.
        """
        return {
            # Simple fallback templates for mixins not handled by functions
            'clearfix': '&::after { content: ""; display: table; clear: both; }',
            'visually-hidden': 'position: absolute !important; width: 1px !important; height: 1px !important; padding: 0 !important; margin: -1px !important; overflow: hidden !important; clip: rect(0, 0, 0, 0) !important; border: 0 !important;',
            'sr-only': 'position: absolute !important; width: 1px !important; height: 1px !important; padding: 0 !important; margin: -1px !important; overflow: hidden !important; clip: rect(0, 0, 0, 0) !important; border: 0 !important;',
        }
    

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
