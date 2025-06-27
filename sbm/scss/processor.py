"""
SCSS processor for the SBM tool.
This processor performs a targeted SCSS-to-SCSS transformation to produce
a clean, self-contained SCSS file with no external @import statements.
"""
import os
import re
from typing import Dict, List, Optional

from ..utils.logger import logger
from ..utils.path import get_dealer_theme_dir, get_common_theme_path

class SCSSProcessor:
    """
    Transforms legacy SCSS to modern, Site-Builder-compatible SCSS
    by parsing and inlining mixins, and removing imports.
    """
    
    def __init__(self, slug: str):
        self.slug = slug
        self.theme_dir = get_dealer_theme_dir(slug)
        self.common_theme_path = get_common_theme_path()
        self.mixins_path = os.path.join(self.common_theme_path, 'css', 'mixins')
        self.mixins: Dict[str, Dict] = {}

    def _load_mixins(self):
        """
        Parses all SCSS files in the mixins directory to build a map of mixins.
        This function is designed to handle nested curly braces in mixin bodies.
        """
        logger.info(f"Loading mixins from: {self.mixins_path}")
        if not os.path.isdir(self.mixins_path):
            logger.warning(f"Mixins directory not found: {self.mixins_path}")
            return

        mixin_pattern = re.compile(r'@mixin\s+([\w-]+)\s*(?:\(([^)]*)\))?\s*\{')

        for filename in os.listdir(self.mixins_path):
            if filename.endswith('.scss'):
                filepath = os.path.join(self.mixins_path, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                for match in mixin_pattern.finditer(content):
                    name = match.group(1)
                    args_str = match.group(2)
                    
                    args = []
                    if args_str:
                        args = [arg.strip().split(':')[0] for arg in args_str.split(',')]

                    body_start_index = match.end()
                    brace_level = 1
                    body_end_index = -1

                    for i in range(body_start_index, len(content)):
                        if content[i] == '{':
                            brace_level += 1
                        elif content[i] == '}':
                            brace_level -= 1
                            if brace_level == 0:
                                body_end_index = i
                                break
                    
                    if body_end_index != -1:
                        body = content[body_start_index:body_end_index].strip()
                        self.mixins[name] = {'args': args, 'body': body}
                        logger.debug(f"Loaded mixin: {name}({args})")

        logger.info(f"Loaded {len(self.mixins)} mixins.")
        
        # Register special handlers for complex mixins
        self.special_handlers = {
            'z-index': self._handle_z_index_mixin,
            'flexbox': self._handle_flexbox_mixin,
            'justify-content': self._handle_justify_content_mixin,
            'flex-grow': self._handle_flex_grow_mixin,
            'align-items': self._handle_align_items_mixin,
            'pz-font-defaults': self._handle_pz_font_defaults_mixin
        }

    def _handle_pz_font_defaults_mixin(self, args_str: Optional[str], content_block: Optional[str]) -> str:
        """
        Custom handler for the pz-font-defaults mixin.
        This handler wraps the provided content block in a .personalizer-wrap class.
        """
        if not content_block:
            return ""

        # The mixin applies a series of default styles and then includes the content.
        # For our purposes, we will just wrap the content in the .personalizer-wrap class.
        # A more advanced implementation could parse the arguments and generate the
        # h1-h6 styles, but this is a simpler, more direct approach.
        return f".personalizer-wrap {{\n{content_block.strip()}\n}}"

    def _handle_align_items_mixin(self, args_str: Optional[str], full_content: str) -> str:
        """
        Custom handler for the align-items mixin.
        This handler outputs the modern, standard 'align-items' property.
        """
        if not args_str:
            return "align-items: stretch;" # Default value
            
        value = args_str.strip()
        return f"align-items: {value};"

    def _handle_flex_grow_mixin(self, args_str: Optional[str], full_content: str) -> str:
        """
        Custom handler for the flex-grow mixin.
        This handler outputs the modern, standard 'flex-grow' property.
        """
        if not args_str:
            return "flex-grow: 0;" # Default value
            
        value = args_str.strip()
        return f"flex-grow: {value};"

    def _handle_justify_content_mixin(self, args_str: Optional[str], full_content: str) -> str:
        """
        Custom handler for the justify-content mixin.
        This handler outputs the modern, standard 'justify-content' property.
        """
        if not args_str:
            return "justify-content: flex-start;" # Default value
            
        value = args_str.strip()
        return f"justify-content: {value};"

    def _handle_flexbox_mixin(self, args_str: Optional[str], full_content: str) -> str:
        """
        Custom handler for the flexbox mixin.
        This handler outputs the modern, standard 'display: flex' property.
        """
        return "display: flex;"

    def _handle_z_index_mixin(self, args_str: Optional[str], full_content: str) -> str:
        """
        Custom handler for the z-index mixin.
        """
        # Default z-layers map from the common theme mixin
        z_layers = {
            "header": 1000, "header-fixed": 1080, "modal": 1050, "tooltip": 1070,
            "popover": 1060, "mobile-overlay": 1030, "overlay": 1000, "top": 500,
            "extra-high": 400, "high": 300, "mid": 200, "low": 100, "half": 50,
            "impact": 1, "buried": -1,
        }
        
        # A theme can override the $z-layers map. We'll do a simple parse for it.
        # This is a brittle and simplistic parser.
        map_match = re.search(r'\$z-layers:\s*\((.*?)\);', full_content, re.DOTALL)
        if map_match:
            theme_layers_str = map_match.group(1)
            # This regex is also simple, expects '"key": value,' format
            for name, value in re.findall(r'"([^"]+)":\s*(-?\d+)', theme_layers_str):
                z_layers[name] = int(value)

        if not args_str:
            return "/* SBM: z-index mixin called without arguments. */"

        args = [arg.strip() for arg in args_str.split(',')]
        layer = args[0].strip('"\'') # remove quotes
        plus = int(args[1]) if len(args) > 1 else 0

        if layer in z_layers:
            z_value = z_layers[layer] + plus
            return f"z-index: {z_value};"
        elif layer.isdigit() or (layer.startswith('-') and layer[1:].isdigit()):
            return f"z-index: {layer};"
        else:
            logger.warning(f"z-index layer '{layer}' not found. Omitting property.")
            return ""

    def _convert_variables_to_css_vars(self, content: str) -> str:
        """
        Converts all SCSS variables to CSS custom properties (variables)
        for Site Builder compatibility using a generic pattern.
        """
        logger.info("Converting all SCSS variables to CSS custom properties...")
        
        # Convert all SCSS variables ($foo) to CSS variables (var(--foo))
        # This regex looks for a dollar sign followed by one or more word characters
        # (letters, numbers, hyphen). It then uses a replacer function to format it.
        content = re.sub(r'\$([\w-]+)', r'var(--\1)', content)
        
        # Remove the now-unused SCSS variable declaration lines.
        # This will remove lines like `$primary: #000;`
        content = re.sub(r'^\s*\$[\w-]+\s*:.*?;', '', content, flags=re.MULTILINE)

        return content

    def _convert_image_paths(self, content: str) -> str:
        """
        Converts relative image paths to absolute Site Builder paths.
        e.g., ../images/foo.jpg -> /wp-content/themes/DealerInspireDealerTheme/images/foo.jpg
        """
        logger.info("Converting relative image paths...")
        
        path_pattern = re.compile(r"url\((['\"]?)\.\.\/images\/(.*?)(['\"]?)\)")
        replacement = r"url(\1/wp-content/themes/DealerInspireDealerTheme/images/\2\3)"
        
        content = path_pattern.sub(replacement, content)
        
        return content

    def _inline_mixins(self, content: str) -> str:
        """
        Replaces @include statements with the corresponding mixin body
        by using a replacer function with re.sub.
        """
        if not self.mixins:
            self._load_mixins()
        
        # This regex now handles both standard includes (e.g., @include mixin-name;)
        # and includes with content blocks (e.g., @include mixin-name { ... }).
        # It uses a non-capturing group (?:...) to handle optional parentheses.
        include_pattern = re.compile(r'@include\s+([\w-]+)(?:\s*\(([^)]*)\))?\s*(?:;|\{((?:[^{}]|\{[^{}]*\})*)\})')

        def _replacer(match):
            mixin_name = match.group(1)
            provided_args_str = match.group(2)
            content_block = match.group(3)

            # Check for a special handler first
            if mixin_name in self.special_handlers:
                # Pass both args and content block to all handlers for simplicity
                if mixin_name == 'pz-font-defaults':
                    return self.special_handlers[mixin_name](provided_args_str, content_block)
                else:
                    return self.special_handlers[mixin_name](provided_args_str, content)
            
            if mixin_name not in self.mixins:
                logger.warning(f"Mixin '{mixin_name}' not found. Skipping include.")
                return match.group(0) # Return the original @include line

            mixin = self.mixins[mixin_name]
            expected_args = mixin['args']
            body = mixin['body']

            if content_block:
                # Basic @content replacement
                body = body.replace('@content;', content_block.strip())
                body = body.replace('@content', content_block.strip())

            provided_args = []
            if provided_args_str:
                # This is a simplistic parser. It doesn't handle commas inside function calls.
                provided_args = [arg.strip() for arg in provided_args_str.split(',')]

            if len(provided_args) > len(expected_args):
                logger.warning(f"Too many arguments for mixin '{mixin_name}'. Expected {len(expected_args)}, got {len(provided_args)}.")
                return match.group(0)

            arg_map = dict(zip(expected_args, provided_args))

            # Replace argument variables with provided values
            for arg_name, arg_value in arg_map.items():
                # Simple string replacement. Assumes argument names are unique enough.
                # A more robust solution would use word boundaries: re.sub(r'\b' + re.escape(arg_name) + r'\b', ...)
                body = body.replace(arg_name, arg_value)
            
            return body

        return include_pattern.sub(_replacer, content)

    def _remove_imports(self, content: str) -> str:
        """
        Removes all @import statements from the SCSS content.
        """
        # Logic to remove all @import lines
        content = re.sub(r'@import\s+.*?;', '', content)
        return content

    def transform_scss_content(self, content: str) -> str:
        """
        Performs transformations on SCSS content.
        """
        logger.info(f"Performing SCSS transformation for {self.slug}...")

        try:
            # Step 1: Convert SCSS variables to CSS variables (var(--...))
            content = self._convert_variables_to_css_vars(content)

            # Step 2: Convert relative image paths to absolute paths
            content = self._convert_image_paths(content)

            # Step 3: Inline mixins
            content = self._inline_mixins(content)
            
            # Step 4: Remove imports
            processed_content = self._remove_imports(content)
            
            return processed_content
            
        except Exception as e:
            logger.error(f"An unexpected error occurred during SCSS processing for {self.slug}.", exc_info=True)
            return f"/* SBM: UNEXPECTED ERROR. CHECK LOGS. ERROR: {e} */\n{content}"

    def process_scss_file(self, file_path: str) -> str:
        """
        Reads an SCSS file and applies transformations.
        """
        if not os.path.exists(file_path):
            logger.warning(f"File not found, skipping: {file_path}")
            return ""
            
        with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        
        return self.transform_scss_content(content)
    
    def write_files_atomically(self, theme_dir: str, files: Dict[str, str]) -> bool:
        """
        Writes the transformed SCSS files to the theme directory.
        """
        try:
            for name, content in files.items():
                if not content:
                    logger.info(f"Skipping empty file: {name}")
                    continue
                
                final_path = os.path.join(theme_dir, name)
                with open(final_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                logger.info(f"Successfully wrote {final_path}")
            return True
        except Exception as e:
            logger.error(f"Error writing files atomically: {e}", exc_info=True)
            return False
