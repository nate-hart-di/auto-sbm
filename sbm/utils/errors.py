"""
Error handling for SBM Tool V2.

Comprehensive error classes with helpful suggestions for recovery and debugging.
"""

from typing import Optional, Dict, Any, List


class SBMError(Exception):
    """Base exception for SBM Tool V2."""
    
    def __init__(self, message: str, suggestion: Optional[str] = None, 
                 details: Optional[Dict[str, Any]] = None):
        """
        Initialize SBM error.
        
        Args:
            message: Error message
            suggestion: Helpful suggestion for recovery
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.suggestion = suggestion
        self.details = details or {}
    
    def __str__(self) -> str:
        """String representation with suggestion."""
        result = self.message
        if self.suggestion:
            result += f"\nSuggestion: {self.suggestion}"
        return result


class ConfigurationError(SBMError):
    """Configuration-related errors."""
    
    def __init__(self, message: str, missing_vars: Optional[List[str]] = None):
        suggestion = None
        if missing_vars:
            suggestion = (
                f"Please set the following environment variables: {', '.join(missing_vars)}. "
                f"Copy env.example to .env and configure the required settings."
            )
        else:
            suggestion = "Check your environment configuration and ensure all required settings are present."
        
        super().__init__(message, suggestion, {"missing_vars": missing_vars})


class ValidationError(SBMError):
    """Validation-related errors."""
    
    def __init__(self, message: str, field: Optional[str] = None, 
                 expected: Optional[str] = None, actual: Optional[str] = None):
        suggestion = None
        if field and expected:
            suggestion = f"Expected {field} to be {expected}"
            if actual:
                suggestion += f", but got {actual}"
        else:
            suggestion = "Please check the input values and try again."
        
        super().__init__(message, suggestion, {
            "field": field,
            "expected": expected,
            "actual": actual
        })


class GitError(SBMError):
    """Git operation errors."""
    
    def __init__(self, message: str, command: Optional[str] = None, 
                 exit_code: Optional[int] = None, output: Optional[str] = None):
        suggestions = {
            "not a git repository": "Ensure you're in the correct DI Websites Platform directory.",
            "branch already exists": "Use 'git branch -D <branch>' to delete the existing branch first.",
            "nothing to commit": "No changes detected. Check if files were modified correctly.",
            "permission denied": "Check your Git credentials and repository access permissions.",
            "merge conflict": "Resolve merge conflicts manually and commit the changes.",
        }
        
        suggestion = None
        for error_pattern, error_suggestion in suggestions.items():
            if error_pattern.lower() in message.lower():
                suggestion = error_suggestion
                break
        
        if not suggestion:
            suggestion = "Check Git status and repository state. Ensure you have proper permissions."
        
        super().__init__(message, suggestion, {
            "command": command,
            "exit_code": exit_code,
            "output": output
        })


class SCSSError(SBMError):
    """SCSS processing errors."""
    
    def __init__(self, message: str, file_path: Optional[str] = None, 
                 line_number: Optional[int] = None, syntax_error: Optional[str] = None):
        suggestion = None
        
        if "syntax error" in message.lower():
            suggestion = "Check SCSS syntax for missing semicolons, brackets, or invalid nesting."
        elif "variable" in message.lower():
            suggestion = "Ensure all SCSS variables are properly defined and imported."
        elif "mixin" in message.lower():
            suggestion = "Check mixin definitions and ensure they're properly included."
        elif "import" in message.lower():
            suggestion = "Verify import paths and ensure referenced files exist."
        else:
            suggestion = "Review SCSS file for syntax errors and validate against SCSS standards."
        
        super().__init__(message, suggestion, {
            "file_path": file_path,
            "line_number": line_number,
            "syntax_error": syntax_error
        })



class OEMError(SBMError):
    """OEM handler errors."""
    
    def __init__(self, message: str, oem: Optional[str] = None, 
                 slug: Optional[str] = None, brand: Optional[str] = None):
        suggestion = None
        
        if "not found" in message.lower():
            suggestion = f"Check if the OEM handler for '{oem}' is properly implemented."
        elif "brand" in message.lower():
            suggestion = f"Verify brand detection patterns for '{brand}' in the OEM configuration."
        elif "stellantis" in message.lower():
            suggestion = "Check Stellantis brand patterns and ensure enhanced mode is enabled."
        else:
            suggestion = "Review OEM configuration and brand detection patterns."
        
        super().__init__(message, suggestion, {
            "oem": oem,
            "slug": slug,
            "brand": brand
        })


class FileOperationError(SBMError):
    """File operation errors."""
    
    def __init__(self, message: str, file_path: Optional[str] = None, 
                 operation: Optional[str] = None, permissions: Optional[bool] = None):
        suggestions = {
            "not found": "Ensure the file or directory exists and the path is correct.",
            "permission denied": "Check file permissions and ensure you have write access.",
            "already exists": "Use force mode to overwrite existing files if intended.",
            "disk full": "Free up disk space and try again.",
            "read-only": "Change file permissions to allow writing.",
        }
        
        suggestion = None
        for error_pattern, error_suggestion in suggestions.items():
            if error_pattern.lower() in message.lower():
                suggestion = error_suggestion
                break
        
        if not suggestion:
            suggestion = "Check file path, permissions, and disk space availability."
        
        super().__init__(message, suggestion, {
            "file_path": file_path,
            "operation": operation,
            "permissions": permissions
        })


class ThemeError(SBMError):
    """Theme-related errors."""
    
    def __init__(self, message: str, slug: Optional[str] = None, 
                 theme_path: Optional[str] = None):
        suggestion = None
        
        if "not found" in message.lower():
            suggestion = (
                f"Ensure the dealer theme '{slug}' exists in the dealer-themes directory. "
                f"Check the slug spelling and verify the theme is properly set up."
            )
        elif "invalid" in message.lower():
            suggestion = "Check theme structure and ensure all required files are present."
        else:
            suggestion = "Verify theme configuration and directory structure."
        
        super().__init__(message, suggestion, {
            "slug": slug,
            "theme_path": theme_path
        })


class MigrationError(SBMError):
    """Migration workflow errors."""
    
    def __init__(self, message: str, step: Optional[str] = None, 
                 slug: Optional[str] = None, partial_success: bool = False):
        suggestion = None
        
        if step:
            suggestions = {
                "initialization": "Check site startup with 'just start {slug} prod' command.",
                "file_creation": "Verify Site Builder file templates and permissions.",
                "style_migration": "Check SCSS processing and transformation rules.",
                "validation": "Review validation rules and fix any syntax errors.",
                "git_operations": "Check Git repository state and permissions.",
            }
            suggestion = suggestions.get(step, f"Review the {step} step for errors.")
        
        if partial_success:
            suggestion = (
                f"{suggestion} Some steps completed successfully - "
                f"check logs for details on what succeeded."
            )
        
        if not suggestion:
            suggestion = "Check migration logs for detailed error information."
        
        super().__init__(message, suggestion, {
            "step": step,
            "slug": slug,
            "partial_success": partial_success
        })


def format_error_for_display(error: Exception) -> Dict[str, Any]:
    """
    Format an error for display in the UI.
    
    Args:
        error: Exception to format
        
    Returns:
        Dictionary with formatted error information
    """
    if isinstance(error, SBMError):
        return {
            "type": error.__class__.__name__,
            "message": error.message,
            "suggestion": error.suggestion,
            "details": error.details
        }
    else:
        return {
            "type": error.__class__.__name__,
            "message": str(error),
            "suggestion": "Check the error message and try again.",
            "details": {}
        } 
