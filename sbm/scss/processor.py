"""
SCSS processor for the SBM tool, using the libsass library.
"""
import os
import re
import sass
from typing import Dict

from ..utils.logger import logger
from ..utils.path import get_dealer_theme_dir, get_common_theme_path

class SCSSProcessor:
    """
    Transforms legacy SCSS to modern, Site-Builder-compatible SCSS
    by using the libsass compiler.
    """
    
    def __init__(self, slug: str):
        self.slug = slug
        self.theme_dir = get_dealer_theme_dir(slug)
        self.common_theme_path = get_common_theme_path()

    def _get_include_paths(self) -> list[str]:
        """Returns the list of include paths for the SASS compiler."""
        return [
            os.path.join(self.theme_dir, 'css'),
            os.path.join(self.common_theme_path, 'css')
        ]

    def _post_process_css(self, css_content: str) -> str:
        """
        Performs cleanup on the compiled CSS.
        """
        # Replace absolute image paths with relative ones expected by Site Builder
        theme_path_str = '/wp-content/themes/DealerInspireDealerTheme/'
        css_content = css_content.replace(f'url({theme_path_str}images/', 'url(../images/')
        
        # Remove empty rulesets
        css_content = re.sub(r'[^}]*\{\s*\}', '', css_content, flags=re.DOTALL)
        
        return css_content

    def transform_scss_content(self, content: str) -> str:
        """
        Performs transformations on SCSS content using libsass.
        """
        logger.info(f"Performing SCSS transformation for {self.slug} using libsass...")

        try:
            compiled_css = sass.compile(
                string=content,
                include_paths=self._get_include_paths(),
                output_style='expanded'
            )
            
            # Post-process the compiled CSS to clean it up
            processed_content = self._post_process_css(compiled_css)
            
            return processed_content
            
        except sass.SassError as e:
            logger.error(f"Libsass compilation failed for {self.slug}.", exc_info=True)
            logger.error(f"Libsass error: {e}")
            return f"/* SBM: FAILED TO COMPILE WITH LIBSASS. CHECK LOGS. ERROR: {e} */\n{content}"
        except Exception as e:
            logger.error(f"An unexpected error occurred during Libsass processing for {self.slug}.", exc_info=True)
            return f"/* SBM: UNEXPECTED ERROR. CHECK LOGS. */\n{content}"

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
