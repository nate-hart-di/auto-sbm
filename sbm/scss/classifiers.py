"""Style classification system for filtering header/footer/navigation styles.

CRITICAL BUSINESS REQUIREMENT: Header, footer, and navigation styles MUST NOT be 
migrated to Site Builder because Site Builder uses the same classes, causing conflicts.
"""

import re
import logging
from typing import List, Pattern, Set, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ExclusionMatch:
    """Details about an excluded style match."""
    pattern: str
    selector: str
    rule_content: str
    line_number: int


class StyleClassifier:
    """Classify CSS/SCSS rules to determine exclusion from Site Builder migration."""
    
    # Header patterns - CRITICAL: These must not be migrated
    HEADER_PATTERNS = [
        r'\.header\b', r'#header\b', r'\.main-header\b',
        r'\.site-header\b', r'\.page-header\b', r'\.top-header\b',
        r'\.header-\w+', r'\[data-header\]', r'\.brand-header\b'
    ]
    
    # Navigation patterns - CRITICAL: These must not be migrated  
    NAVIGATION_PATTERNS = [
        r'\.nav\b', r'\.navigation\b', r'\.main-nav\b',
        r'\.navbar\b', r'\.menu\b', r'\.primary-menu\b',
        r'\.nav-\w+', r'\.menu-\w+', r'\[data-nav\]',
        r'\.desktop-nav\b', r'\.mobile-nav\b', r'\.mega-menu\b',
        r'\.menu-item\b', r'\.nav-item\b', r'\.dropdown-menu\b'
    ]
    
    # Footer patterns - CRITICAL: These must not be migrated
    FOOTER_PATTERNS = [
        r'\.footer\b', r'#footer\b', r'\.main-footer\b',
        r'\.site-footer\b', r'\.page-footer\b', r'\.bottom-footer\b',
        r'\.footer-\w+', r'\[data-footer\]', r'\.footer-content\b'
    ]
    
    def __init__(self):
        """Initialize classifier with compiled patterns."""
        self.exclusion_patterns = self._compile_patterns()
        self.exclusion_stats = {
            'header_exclusions': 0,
            'nav_exclusions': 0, 
            'footer_exclusions': 0,
            'total_rules_processed': 0
        }
    
    def _compile_patterns(self) -> List[Pattern]:
        """Compile all exclusion patterns for performance."""
        all_patterns = (
            self.HEADER_PATTERNS + 
            self.NAVIGATION_PATTERNS + 
            self.FOOTER_PATTERNS
        )
        return [re.compile(pattern, re.IGNORECASE) for pattern in all_patterns]
    
    def should_exclude_selector(self, selector: str) -> Tuple[bool, str]:
        """
        Check if a CSS selector should be excluded from migration.
        
        Returns:
            (should_exclude: bool, reason: str)
        """
        for pattern in self.exclusion_patterns:
            if pattern.search(selector):
                return True, f"Matched exclusion pattern: {pattern.pattern}"
        return False, ""
    
    def filter_scss_content(self, content: str, theme_slug: str) -> Tuple[str, List[ExclusionMatch]]:
        """
        Remove excluded styles from SCSS content.
        
        Returns:
            (filtered_content: str, exclusion_matches: List[ExclusionMatch])
        """
        lines = content.split('\n')
        filtered_lines = []
        exclusions = []
        
        current_rule_lines = []
        in_excluded_rule = False
        current_selector_parts = []
        rule_start_line = 0
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Skip empty lines and comments
            if not stripped or stripped.startswith('//') or stripped.startswith('/*'):
                if not in_excluded_rule:
                    filtered_lines.append(line)
                i += 1
                continue
            
            # Check if this line contains selectors (ends with comma or has opening brace)
            has_opening_brace = '{' in line
            ends_with_comma = stripped.endswith(',')
            
            if not in_excluded_rule:
                # Start collecting selector parts if this looks like a selector
                if ends_with_comma or has_opening_brace:
                    if not current_selector_parts:  # Starting new rule
                        rule_start_line = i + 1
                    
                    # Extract selector from this line
                    if has_opening_brace:
                        selector_part = line.split('{')[0].strip()
                    else:
                        selector_part = stripped.rstrip(',').strip()
                    
                    current_selector_parts.append(selector_part)
                    
                    # If we hit an opening brace, we have the complete selector
                    if has_opening_brace:
                        full_selector = ' '.join(current_selector_parts)
                        should_exclude, reason = self.should_exclude_selector(full_selector)
                        
                        if should_exclude:
                            in_excluded_rule = True
                            current_rule_lines = []
                            
                            # Add all selector lines to excluded rule
                            for j in range(rule_start_line - 1, i + 1):
                                current_rule_lines.append(lines[j])
                            
                            exclusions.append(ExclusionMatch(
                                pattern=reason,
                                selector=full_selector,
                                rule_content=full_selector,
                                line_number=rule_start_line
                            ))
                            logger.debug(f"Excluding rule: {full_selector} at lines {rule_start_line}-{i+1}")
                        else:
                            # Not excluded, add all selector lines to output
                            for j in range(rule_start_line - 1, i + 1):
                                filtered_lines.append(lines[j])
                        
                        # Reset selector collection
                        current_selector_parts = []
                    
                else:
                    # Not a selector line, just add it if we're not collecting selectors
                    if not current_selector_parts:
                        filtered_lines.append(line)
            
            else:  # in_excluded_rule
                current_rule_lines.append(line)
                
                # Count braces to find end of rule
                if '}' in line:
                    close_braces = line.count('}')
                    open_braces = line.count('{')
                    
                    # Simple heuristic: if we see closing brace, rule might be ending
                    if close_braces > 0:
                        in_excluded_rule = False
                        logger.debug(f"Excluded rule complete: {len(current_rule_lines)} lines")
                        current_rule_lines = []
            
            i += 1
        
        self._update_stats(exclusions)
        
        if exclusions:
            logger.info(f"Excluded {len(exclusions)} header/footer/nav styles from {theme_slug}")
        
        return '\n'.join(filtered_lines), exclusions
    
    def _extract_selector(self, line: str) -> str:
        """Extract CSS selector from a line containing opening brace."""
        if '{' in line:
            return line.split('{')[0].strip()
        return line.strip()
    
    def _update_stats(self, exclusions: List[ExclusionMatch]):
        """Update exclusion statistics."""
        for exclusion in exclusions:
            pattern_lower = exclusion.pattern.lower()
            if 'header' in pattern_lower:
                self.exclusion_stats['header_exclusions'] += 1
            elif any(nav_term in pattern_lower for nav_term in ['nav', 'menu']):
                self.exclusion_stats['nav_exclusions'] += 1  
            elif 'footer' in pattern_lower:
                self.exclusion_stats['footer_exclusions'] += 1
        
        self.exclusion_stats['total_rules_processed'] = len(exclusions)
    
    def get_exclusion_summary(self) -> str:
        """Get human-readable summary of exclusion statistics."""
        stats = self.exclusion_stats
        return (
            f"Header: {stats['header_exclusions']}, "
            f"Navigation: {stats['nav_exclusions']}, "
            f"Footer: {stats['footer_exclusions']}, "
            f"Total: {stats['total_rules_processed']} excluded rules"
        )