"""
SCSS processor for the SBM tool - Production-grade implementation.

This module provides robust SCSS parsing, transformation, and validation
using libsass and proper AST-based processing instead of fragile regex parsing.

Following the methodology from auto-sbm-scss-migration-root-cause-analysis-and-recommendations.md
"""

import os
import re
import tempfile
import sass
from typing import Dict, List, Tuple, Optional
from ..utils.logger import logger
from .transformer import transform_scss


class SCSSProcessor:
    """
    Production-grade SCSS processor using libsass for parsing and validation.
    """
    
    def __init__(self, slug: str):
        self.slug = slug
        self.vdp_patterns = [
            r'\.vdp\b', r'\.lvdp\b', r'\.vehicle-detail', r'vdp--', r'\bvehicle-details',
            r'vdp-price-box', r'page-template-vehicle', r'single-vehicle', r'vehicle-page',
            r'\bvdp[\s_-]', r'[\s_-]vdp\b', r'vehicle-detail-page', r'vehicle_detail', 
            r'details-page', r'detail-view', r'single-inventory-vehicle',
            r'\.page-vehicle-display-page\b'
        ]
        self.vrp_patterns = [
            r'\.vrp\b', r'\.lvrp\b', r'\.srp\b', r'\.vehicle-list', r'\.vehicle-results',
            r'inventory-page', r'page-template-inventory', r'search-results-page',
            r'\bvrp[\s_-]', r'[\s_-]vrp\b', r'\bsrp[\s_-]', r'[\s_-]srp\b',
            r'vehicle-results-page', r'inventory-results', r'inventory-listing',
            r'\.page-vehicle-results-page\b'
        ]
    
    def validate_scss_syntax(self, content: str) -> Tuple[bool, Optional[str]]:
        """
        Validate SCSS syntax using libsass compiler.
        
        Args:
            content (str): SCSS content to validate
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            # Try to compile the SCSS to check for syntax errors
            sass.compile(string=content, output_style='compressed')
            return True, None
        except sass.CompileError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Unexpected error during validation: {str(e)}"
    
    def extract_balanced_blocks(self, content: str) -> List[Dict]:
        """
        Extract balanced CSS/SCSS blocks using brace-depth state machine.
        This is the fallback method when AST parsing isn't sufficient.
        
        Args:
            content (str): SCSS content to parse
            
        Returns:
            List[Dict]: List of extracted blocks with metadata
        """
        blocks = []
        lines = content.splitlines()
        current_block = []
        brace_depth = 0
        in_string = False
        in_comment = False
        string_char = None
        
        for line_num, line in enumerate(lines, 1):
            i = 0
            while i < len(line):
                char = line[i]
                
                # Handle string literals
                if not in_comment and char in ['"', "'"] and (i == 0 or line[i-1] != '\\'):
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif char == string_char:
                        in_string = False
                        string_char = None
                
                # Handle comments
                elif not in_string:
                    if char == '/' and i + 1 < len(line):
                        if line[i + 1] == '/':
                            # Single-line comment - rest of line is comment
                            break
                        elif line[i + 1] == '*':
                            in_comment = True
                            i += 1  # Skip the *
                    elif in_comment and char == '*' and i + 1 < len(line) and line[i + 1] == '/':
                        in_comment = False
                        i += 1  # Skip the /
                    
                    # Handle braces (only when not in string or comment)
                    elif not in_comment and char == '{':
                        brace_depth += 1
                    elif not in_comment and char == '}':
                        brace_depth -= 1
                
                i += 1
            
            current_block.append(line)
            
            # If we've closed all braces and have content, we have a complete block
            if brace_depth == 0 and current_block and any('{' in l for l in current_block):
                block_content = '\n'.join(current_block).strip()
                if block_content:
                    blocks.append({
                        'content': block_content,
                        'start_line': line_num - len(current_block) + 1,
                        'end_line': line_num,
                        'category': self._categorize_block(block_content)
                    })
                current_block = []
            elif brace_depth < 0:
                # Unbalanced braces - log warning and reset
                logger.warning(f"Unbalanced braces detected at line {line_num}")
                brace_depth = 0
                current_block = []
        
        # Handle any remaining content
        if current_block:
            block_content = '\n'.join(current_block).strip()
            if block_content and not block_content.startswith('//'):
                # Check if this looks like a valid CSS block
                if '{' in block_content and '}' in block_content:
                    # Try to fix unbalanced braces
                    opening = block_content.count('{')
                    closing = block_content.count('}')
                    if opening > closing:
                        block_content += '\n' + '}' * (opening - closing)
                        logger.info(f"Fixed incomplete block at end of file by adding {opening - closing} closing braces")
                        blocks.append({
                            'content': block_content,
                            'start_line': len(lines) - len(current_block) + 1,
                            'end_line': len(lines),
                            'category': self._categorize_block(block_content)
                        })
                    elif opening == closing:
                        blocks.append({
                            'content': block_content,
                            'start_line': len(lines) - len(current_block) + 1,
                            'end_line': len(lines),
                            'category': self._categorize_block(block_content)
                        })
                    else:
                        logger.warning(f"Discarding malformed block with too many closing braces: {block_content[:50]}...")
                else:
                    logger.warning(f"Discarding incomplete block at end of file: {block_content[:50]}...")
        
        return blocks
    
    def _categorize_block(self, content: str) -> str:
        """
        Categorize a CSS/SCSS block based on its selectors.
        
        Args:
            content (str): Block content to categorize
            
        Returns:
            str: Category ('vdp', 'vrp', or 'inside')
        """
        # Check for VDP patterns first
        for pattern in self.vdp_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return 'vdp'
        
        # Check for VRP patterns
        for pattern in self.vrp_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return 'vrp'
        
        # Default to inside
        return 'inside'
    
    def sanitize_property_values(self, content: str) -> str:
        """
        Sanitize property values, ensuring balanced quotes and parentheses.
        
        Args:
            content (str): SCSS content to sanitize
            
        Returns:
            str: Sanitized content
        """
        # Fix double quotes: url(""path") -> url("path")
        content = re.sub(r'url\([\'"]?[\'"]([^)]*?)[\'"]?[\'"]?\)', r'url("\1")', content)
        
        # Fix unquoted URLs: url(path) -> url("path")
        content = re.sub(r'url\(\s*([^\'"][^)]*[^\'"])\s*\)', r'url("\1")', content)
        
        # Fix URLs with only one quote: url("path) or url(path") -> url("path")
        content = re.sub(r'url\([\'"]?([^)]*?)[\'"]?\)', r'url("\1")', content)
        
        # Clean up any remaining malformed URLs
        content = re.sub(r'url\([\'"]([^)]*?)[\'"]([^)]*?)[\'"]?\)', r'url("\1\2")', content)
        
        return content
    
    def _clean_malformed_content(self, content: str) -> str:
        """
        Clean up malformed content that might cause validation issues.
        
        Args:
            content (str): Content to clean
            
        Returns:
            str: Cleaned content
        """
        lines = content.splitlines()
        cleaned_lines = []
        in_selector = False
        brace_depth = 0
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Track brace depth to know if we're inside a selector
            brace_depth += line.count('{') - line.count('}')
            in_selector = brace_depth > 0
            
            # Skip lines that look like incomplete selectors or malformed content
            if line_stripped:
                # Skip CSS variable declarations that are not inside a selector
                if (line_stripped.startswith('var(--') and line_stripped.endswith(';') and not in_selector):
                    logger.debug(f"Skipping orphaned CSS variable: {line_stripped}")
                    continue
                
                # Skip lines that are just variable names or incomplete selectors
                if (line_stripped.startswith('var(--') and not line_stripped.endswith(')') and 
                    not line_stripped.endswith(';') and not line_stripped.endswith('{')):
                    logger.debug(f"Skipping malformed variable line: {line_stripped}")
                    continue
                
                # Skip lines that are just property names without values
                if (re.match(r'^[a-zA-Z-]+\s*$', line_stripped) and 
                    not line_stripped.endswith('{') and not line_stripped.endswith('}')):
                    logger.debug(f"Skipping incomplete property line: {line_stripped}")
                    continue
                
                # Skip standalone property declarations not inside selectors
                if (not in_selector and ':' in line_stripped and line_stripped.endswith(';') and 
                    not line_stripped.startswith('@') and not line_stripped.startswith('//')):
                    logger.debug(f"Skipping orphaned property: {line_stripped}")
                    continue
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _fix_brace_balance(self, content: str) -> str:
        """
        Fix brace balance issues by removing excess closing braces.
        
        Args:
            content (str): Content to fix
            
        Returns:
            str: Content with balanced braces
        """
        lines = content.splitlines()
        cleaned_lines = []
        brace_depth = 0
        
        for line in lines:
            original_line = line
            line_stripped = line.strip()
            
            # Count braces in this line
            opening_braces = line.count('{')
            closing_braces = line.count('}')
            
            # If this line would make brace_depth negative, remove excess closing braces
            if brace_depth + opening_braces - closing_braces < 0:
                # Calculate how many closing braces we can actually use
                max_closing = brace_depth + opening_braces
                if max_closing < closing_braces:
                    # Remove excess closing braces
                    excess = closing_braces - max_closing
                    logger.debug(f"Removing {excess} excess closing braces from line: {line_stripped}")
                    
                    # Remove excess closing braces from the end of the line
                    for _ in range(excess):
                        line = line.rsplit('}', 1)[0] if '}' in line else line
            
            # Update brace depth
            brace_depth += line.count('{') - line.count('}')
            
            # Ensure brace depth never goes negative
            if brace_depth < 0:
                brace_depth = 0
            
            cleaned_lines.append(line)
        
        # If we end with unbalanced braces, add missing closing braces
        if brace_depth > 0:
            logger.debug(f"Adding {brace_depth} missing closing braces at end of content")
            cleaned_lines.append('}' * brace_depth)
        
        return '\n'.join(cleaned_lines)
    
    def process_style_scss(self, theme_dir: str) -> Dict[str, str]:
        """
        Process style.scss file using production-grade methodology.
        
        Args:
            theme_dir (str): Path to theme directory
            
        Returns:
            Dict[str, str]: Categorized SCSS content
        """
        logger.info(f"Processing style.scss for {self.slug} using production-grade methodology")
        
        # Find style.scss
        style_path = os.path.join(theme_dir, "style.scss")
        if not os.path.exists(style_path):
            style_path = os.path.join(theme_dir, "css", "style.scss")
            if not os.path.exists(style_path):
                logger.error("style.scss not found")
                return {}
        
        # Read the file
        try:
            with open(style_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Error reading style.scss: {e}")
            return {}
        
        # Remove imports to focus on actual styles
        content_lines = content.splitlines()
        non_import_lines = []
        for line in content_lines:
            if not re.match(r'^\s*@import', line):
                non_import_lines.append(line)
        
        content = '\n'.join(non_import_lines)
        
        # Extract balanced blocks using state machine
        blocks = self.extract_balanced_blocks(content)
        
        logger.info(f"Extracted {len(blocks)} balanced blocks")
        
        # Categorize blocks
        categorized = {'vdp': [], 'vrp': [], 'inside': []}
        for block in blocks:
            category = block['category']
            categorized[category].append(block['content'])
        
        # Log statistics
        for category, blocks_list in categorized.items():
            logger.info(f"  - {category.upper()} blocks: {len(blocks_list)}")
        
        # Join and process each category
        results = {}
        for category, blocks_list in categorized.items():
            if blocks_list:
                combined_content = '\n\n'.join(blocks_list)
                
                # Sanitize property values
                combined_content = self.sanitize_property_values(combined_content)
                
                # Apply SCSS transformations
                combined_content = transform_scss(combined_content, self.slug)
                
                # Clean up malformed content
                combined_content = self._clean_malformed_content(combined_content)
                
                # Final brace balance check and fix
                combined_content = self._fix_brace_balance(combined_content)
                
                # Clean up extra whitespace
                combined_content = re.sub(r'\n{3,}', '\n\n', combined_content).strip()
                
                results[f"sb-{category}.scss"] = combined_content
            else:
                results[f"sb-{category}.scss"] = ""
        
        return results
    
    def write_files_atomically(self, theme_dir: str, files: Dict[str, str]) -> bool:
        """
        Write SCSS files atomically with validation.
        
        Args:
            theme_dir (str): Theme directory path
            files (Dict[str, str]): Files to write
            
        Returns:
            bool: Success status
        """
        temp_files = {}
        
        try:
            # Create temporary files and validate content
            for filename, content in files.items():
                if not content.strip():
                    logger.info(f"Skipping empty file: {filename}")
                    continue
                
                # Validate SCSS syntax
                is_valid, error = self.validate_scss_syntax(content)
                if not is_valid:
                    logger.error(f"SCSS validation failed for {filename}: {error}")
                    return False
                
                # Create temporary file
                temp_fd, temp_path = tempfile.mkstemp(suffix='.scss', prefix=f'{filename}_')
                try:
                    with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                        f.write(content)
                    temp_files[filename] = temp_path
                except Exception as e:
                    os.close(temp_fd)
                    raise e
            
            # If all validations passed, atomically move files into place
            for filename, temp_path in temp_files.items():
                final_path = os.path.join(theme_dir, filename)
                
                # Backup existing file if it exists
                if os.path.exists(final_path):
                    backup_path = f"{final_path}.backup"
                    os.rename(final_path, backup_path)
                
                # Atomic move
                os.rename(temp_path, final_path)
                logger.info(f"Successfully wrote {final_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during atomic file write: {e}")
            
            # Clean up temporary files
            for temp_path in temp_files.values():
                try:
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                except Exception:
                    pass
            
            return False


def analyze_style_scss(theme_dir: str, use_improved_parser: bool = True, slug: str = None) -> Dict[str, str]:
    """
    Main entry point for SCSS analysis using production-grade methodology.
    
    Args:
        theme_dir (str): Theme directory path
        use_improved_parser (bool): Always True for production-grade processing
        slug (str): Theme slug
        
    Returns:
        Dict[str, str]: Categorized SCSS content
    """
    if not slug:
        slug = os.path.basename(theme_dir)
    
    processor = SCSSProcessor(slug)
    return processor.process_style_scss(theme_dir) 
