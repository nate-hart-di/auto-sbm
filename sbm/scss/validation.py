"""
SCSS Validation and User Confirmation Module

This module provides comprehensive validation of SCSS conversion and 
user confirmation workflow for any unconverted content.
"""

import re
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import logging
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm, Prompt
from rich.text import Text


class SCSSValidationError(Exception):
    """Raised when SCSS validation fails."""
    pass


class SCSSValidator:
    """
    Comprehensive SCSS validation with user confirmation workflow.
    
    This validator ensures NO unconverted SCSS makes it through the pipeline.
    """
    
    def __init__(self):
        self.console = Console()
        self.logger = logging.getLogger(__name__)
        
    def validate_and_confirm(self, content: str, file_name: str) -> Tuple[bool, str]:
        """
        Validate SCSS conversion and get user confirmation if issues found.
        
        Args:
            content: The processed SCSS content
            file_name: Name of the file being validated
            
        Returns:
            (success: bool, final_content: str)
            
        Raises:
            SCSSValidationError: If validation fails and user chooses not to proceed
        """
        validation_results = self._comprehensive_validation(content)
        
        if self._is_fully_converted(validation_results):
            # Perfect conversion - no user interaction needed
            self.console.print(f"✅ [green]{file_name}[/green] - Perfect SCSS conversion!")
            return True, content
        
        # Issues found - show detailed report and get user confirmation
        return self._handle_validation_issues(content, file_name, validation_results)
    
    def _comprehensive_validation(self, content: str) -> Dict[str, List[str]]:
        """
        Perform comprehensive validation of SCSS conversion.
        
        Checks for:
        - Remaining @include statements
        - Remaining $variables
        - Remaining SCSS functions
        - Non-compliant breakpoints
        - Missing CSS variable conversions
        """
        results = {
            'remaining_mixins': [],
            'remaining_variables': [],
            'remaining_functions': [],
            'non_compliant_breakpoints': [],
            'missing_css_variables': [],
            'other_issues': []
        }
        
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Skip comments
            if stripped.startswith('//') or stripped.startswith('/*'):
                continue
            
            # Check for remaining @include statements
            mixin_matches = re.findall(r'@include\s+[^;]+;', line)
            for match in mixin_matches:
                results['remaining_mixins'].append(f"Line {line_num}: {match}")
            
            # Check for remaining SCSS variables (but not CSS variables)
            variable_matches = re.findall(r'\$[a-zA-Z0-9_-]+', line)
            for match in variable_matches:
                results['remaining_variables'].append(f"Line {line_num}: {match}")
            
            # Check for non-compliant breakpoints
            if re.search(r'@media.*920px', line):
                results['non_compliant_breakpoints'].append(f"Line {line_num}: 920px breakpoint (should be 768px or 1024px)")
            
            # Check for SCSS functions that should be converted
            scss_functions = ['darken(', 'lighten(', 'saturate(', 'desaturate(', 'rgba($', 'mix(']
            for func in scss_functions:
                if func in line:
                    results['remaining_functions'].append(f"Line {line_num}: {func}...")
            
            # Check for hardcoded colors that should be CSS variables
            hex_colors = re.findall(r'#[0-9a-fA-F]{3,6}', line)
            for color in hex_colors:
                if not re.search(rf'var\([^)]*{re.escape(color)}[^)]*\)', line):
                    results['missing_css_variables'].append(f"Line {line_num}: {color} (should use CSS variable)")
        
        # Remove duplicates
        for key in results:
            results[key] = list(set(results[key]))
        
        return results
    
    def _is_fully_converted(self, validation_results: Dict[str, List[str]]) -> bool:
        """Check if SCSS is fully converted (no issues found)."""
        return all(len(issues) == 0 for issues in validation_results.values())
    
    def _handle_validation_issues(self, content: str, file_name: str, validation_results: Dict[str, List[str]]) -> Tuple[bool, str]:
        """
        Handle validation issues with user confirmation workflow.
        """
        self.console.print()
        self.console.print(Panel(
            f"[red]🚨 SCSS VALIDATION ISSUES FOUND[/red]\n\n"
            f"File: [yellow]{file_name}[/yellow]\n"
            f"Issues must be resolved before proceeding with Site Builder Migration.",
            title="SCSS Validation Report",
            border_style="red"
        ))
        
        # Create detailed issue report
        self._display_detailed_report(validation_results)
        
        # Show options to user
        self.console.print("\n[yellow]Options:[/yellow]")
        self.console.print("1. [red]Stop migration[/red] - Fix issues manually and re-run")
        self.console.print("2. [yellow]Continue anyway[/yellow] - Proceed with unconverted SCSS (NOT RECOMMENDED)")
        self.console.print("3. [blue]Manual fix[/blue] - Edit the content now")
        
        choice = Prompt.ask(
            "\nWhat would you like to do?",
            choices=["1", "2", "3", "stop", "continue", "fix"],
            default="1"
        )
        
        if choice in ["1", "stop"]:
            self._show_fix_instructions(validation_results)
            raise SCSSValidationError(f"SCSS validation failed for {file_name}. Please fix issues and re-run.")
        
        elif choice in ["2", "continue"]:
            if self._confirm_risky_proceed():
                self.console.print("[red]⚠️  Proceeding with unconverted SCSS - this may cause issues![/red]")
                return True, content
            else:
                raise SCSSValidationError("User chose not to proceed with unconverted SCSS.")
        
        elif choice in ["3", "fix"]:
            return self._manual_fix_workflow(content, file_name, validation_results)
        
        return False, content
    
    def _display_detailed_report(self, validation_results: Dict[str, List[str]]):
        """Display detailed validation report."""
        
        table = Table(title="SCSS Validation Issues", show_header=True, header_style="bold magenta")
        table.add_column("Issue Type", style="cyan", no_wrap=True)
        table.add_column("Count", style="red", justify="center")
        table.add_column("Details", style="white")
        
        issue_types = {
            'remaining_mixins': 'Unconverted Mixins',
            'remaining_variables': 'SCSS Variables',
            'remaining_functions': 'SCSS Functions',
            'non_compliant_breakpoints': 'Non-compliant Breakpoints',
            'missing_css_variables': 'Missing CSS Variables'
        }
        
        for key, title in issue_types.items():
            issues = validation_results[key]
            if issues:
                details = "\n".join(issues[:3])  # Show first 3 issues
                if len(issues) > 3:
                    details += f"\n... and {len(issues) - 3} more"
                
                table.add_row(title, str(len(issues)), details)
        
        self.console.print(table)
    
    def _show_fix_instructions(self, validation_results: Dict[str, List[str]]):
        """Show instructions for fixing validation issues."""
        
        self.console.print("\n[yellow]🔧 How to fix these issues:[/yellow]")
        
        if validation_results['remaining_mixins']:
            self.console.print("\n[red]Unconverted Mixins:[/red]")
            self.console.print("• These mixins were not recognized by the CommonTheme parser")
            self.console.print("• Either add them to the mixin definitions or convert manually")
            self.console.print("• Example: @include flexbox; → display: flex;")
        
        if validation_results['remaining_variables']:
            self.console.print("\n[red]SCSS Variables:[/red]")
            self.console.print("• Convert to CSS custom properties")
            self.console.print("• Example: $primary → var(--primary)")
            self.console.print("• Example: $white → var(--white, #fff)")
        
        if validation_results['remaining_functions']:
            self.console.print("\n[red]SCSS Functions:[/red]")
            self.console.print("• Convert to CSS equivalents or CSS variables")
            self.console.print("• Example: darken($primary, 10%) → var(--primary-dark)")
        
        if validation_results['non_compliant_breakpoints']:
            self.console.print("\n[red]Non-compliant Breakpoints:[/red]")
            self.console.print("• Use Site Builder standard breakpoints")
            self.console.print("• 920px → 768px (tablet) or 1024px (desktop)")
        
        if validation_results['missing_css_variables']:
            self.console.print("\n[red]Missing CSS Variables:[/red]")
            self.console.print("• Wrap hex colors in CSS variables with fallbacks")
            self.console.print("• Example: #fff → var(--white, #fff)")
    
    def _confirm_risky_proceed(self) -> bool:
        """Get explicit confirmation for risky proceed option."""
        
        self.console.print("\n[red]⚠️  WARNING: Proceeding with unconverted SCSS is risky![/red]")
        self.console.print("This may cause:")
        self.console.print("• Broken styles in Site Builder")
        self.console.print("• Compilation errors")
        self.console.print("• Failed PR reviews")
        self.console.print("• Non-compliant theme code")
        
        return Confirm.ask("\nAre you absolutely sure you want to proceed?", default=False)
    
    def _manual_fix_workflow(self, content: str, file_name: str, validation_results: Dict[str, List[str]]) -> Tuple[bool, str]:
        """
        Manual fix workflow - allow user to edit content directly.
        """
        self.console.print(f"\n[blue]Manual Fix Mode for {file_name}[/blue]")
        self.console.print("You can now edit the content to fix the issues.")
        self.console.print("When done, the content will be re-validated.")
        
        # Show current content with line numbers
        self._show_content_with_line_numbers(content)
        
        # Get edited content from user
        self.console.print("\n[yellow]Enter your fixed content (end with '###END###' on a new line):[/yellow]")
        
        fixed_lines = []
        while True:
            line = input()
            if line.strip() == '###END###':
                break
            fixed_lines.append(line)
        
        fixed_content = '\n'.join(fixed_lines)
        
        # Re-validate the fixed content
        new_validation = self._comprehensive_validation(fixed_content)
        
        if self._is_fully_converted(new_validation):
            self.console.print("✅ [green]Fixed content passes validation![/green]")
            return True, fixed_content
        else:
            self.console.print("❌ [red]Fixed content still has issues.[/red]")
            return self._handle_validation_issues(fixed_content, file_name, new_validation)
    
    def _show_content_with_line_numbers(self, content: str):
        """Show content with line numbers for easier editing."""
        
        self.console.print("\n[cyan]Current content with line numbers:[/cyan]")
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            self.console.print(f"[dim]{line_num:3d}:[/dim] {line}")
        
        self.console.print()
    
    def create_validation_report(self, validation_results: Dict[str, List[str]], file_name: str) -> str:
        """
        Create a detailed validation report for logging/documentation.
        """
        report_lines = [
            f"SCSS Validation Report for {file_name}",
            "=" * 50,
            ""
        ]
        
        total_issues = sum(len(issues) for issues in validation_results.values())
        
        if total_issues == 0:
            report_lines.append("✅ PERFECT CONVERSION - No issues found!")
        else:
            report_lines.append(f"❌ {total_issues} issues found:")
            report_lines.append("")
            
            for issue_type, issues in validation_results.items():
                if issues:
                    report_lines.append(f"{issue_type.replace('_', ' ').title()}:")
                    for issue in issues:
                        report_lines.append(f"  - {issue}")
                    report_lines.append("")
        
        return '\n'.join(report_lines) 
