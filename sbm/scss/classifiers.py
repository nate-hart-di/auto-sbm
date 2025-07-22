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
        
        current_rule = []
        brace_depth = 0
        in_excluded_rule = False
        current_selector = ""
        rule_start_line = 0
        
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Skip empty lines and comments
            if not stripped or stripped.startswith('//') or stripped.startswith('/*'):
                if not in_excluded_rule:
                    filtered_lines.append(line)
                continue
            
            # Track brace depth
            open_braces = line.count('{')
            close_braces = line.count('}')
            
            if open_braces > 0 and not in_excluded_rule:
                # Potential start of CSS rule
                current_selector = self._extract_selector(line)
                should_exclude, reason = self.should_exclude_selector(current_selector)
                
                if should_exclude:
                    in_excluded_rule = True
                    rule_start_line = line_num
                    current_rule = [line]
                    exclusions.append(ExclusionMatch(
                        pattern=reason,
                        selector=current_selector,
                        rule_content=line,
                        line_number=line_num
                    ))
                    brace_depth = open_braces - close_braces
                    logger.debug(f"Excluding rule: {current_selector} at line {line_num}")
                    continue
            
            if in_excluded_rule:
                current_rule.append(line)
                brace_depth += open_braces - close_braces
                
                if brace_depth <= 0:
                    # End of excluded rule
                    logger.debug(f"Excluded rule complete: {current_selector} ({len(current_rule)} lines)")
                    in_excluded_rule = False
                    current_rule = []
                    current_selector = ""
                continue
            
            # Keep non-excluded lines
            filtered_lines.append(line)
        
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