"""
Fullauto mode implementation for SBM.

This module provides fully automated migration capabilities that bypass
all user prompts except for actual compilation errors.
"""

from typing import Any, Dict, Optional
import click
from sbm.utils.logger import logger


class FullautoMode:
    """
    Manages fullauto mode behavior and configuration.
    
    Fullauto mode bypasses all interactive prompts except for actual errors
    that require user intervention (compilation errors, network failures, etc).
    """

    def __init__(self, enabled: bool = False):
        """
        Initialize fullauto mode.
        
        Args:
            enabled: Whether fullauto mode is active
        """
        self.enabled = enabled
        self._original_confirm = None

    def __enter__(self):
        """Enter fullauto mode context."""
        if self.enabled:
            logger.info("Entering fullauto mode - bypassing user prompts")
            set_fullauto_active(True)
            self._patch_click_confirm()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit fullauto mode context."""
        if self.enabled:
            self._restore_click_confirm()
            set_fullauto_active(False)
            logger.info("Exiting fullauto mode")

    def _patch_click_confirm(self):
        """Patch click.confirm to auto-respond 'yes' in fullauto mode."""
        self._original_confirm = click.confirm
        
        def fullauto_confirm(text, default=True, abort=False, prompt_suffix=": ", 
                           show_default=True, err=False):
            """Auto-confirm replacement that logs the bypassed prompt."""
            logger.debug(f"Fullauto mode: Auto-confirming prompt: {text}")
            
            # Handle special cases where we should still prompt
            if self._should_still_prompt(text):
                return self._original_confirm(
                    text, default, abort, prompt_suffix, show_default, err
                )
            
            # Auto-respond with default value
            return default
        
        click.confirm = fullauto_confirm

    def _restore_click_confirm(self):
        """Restore original click.confirm function."""
        if self._original_confirm:
            click.confirm = self._original_confirm

    def _should_still_prompt(self, text: str) -> bool:
        """
        Determine if a prompt should still be shown even in fullauto mode.
        
        Args:
            text: The prompt text
            
        Returns:
            True if the prompt should still be shown (for critical errors)
        """
        critical_keywords = [
            "compilation failed",
            "error",
            "failed to",
            "cannot continue",
            "critical",
            "fatal"
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in critical_keywords)

    def get_migration_params(self) -> Dict[str, Any]:
        """
        Get migration parameters for fullauto mode.
        
        Returns:
            Dictionary of parameters for migrate_dealer_theme
        """
        if not self.enabled:
            return {}
            
        return {
            'interactive_review': False,
            'interactive_git': False,
            'interactive_pr': False
        }

    def get_post_migration_params(self) -> Dict[str, Any]:
        """
        Get post-migration parameters for fullauto mode.
        
        Returns:
            Dictionary of parameters for run_post_migration_workflow
        """
        if not self.enabled:
            return {}
            
        return {
            'interactive_review': False,
            'interactive_git': False,
            'interactive_pr': False
        }

    def handle_compilation_error(self, error_info: Dict[str, Any]) -> str:
        """
        Handle compilation errors in fullauto mode.
        
        Args:
            error_info: Error information dictionary
            
        Returns:
            Action to take ('retry', 'skip', 'abort')
        """
        if not self.enabled:
            # In interactive mode, let the normal prompt system handle it
            return 'prompt'
        
        error_type = error_info.get('type', 'unknown')
        logger.warning(f"Fullauto mode: Handling compilation error: {error_type}")
        
        # Auto-retry for fixable errors
        fixable_errors = ['undefined_variable', 'undefined_mixin', 'syntax_error']
        if error_type in fixable_errors:
            logger.info("Fullauto mode: Auto-retrying fixable compilation error")
            return 'retry'
        
        # For unfixable errors, we need to abort or skip based on severity
        if error_type == 'invalid_css':
            logger.warning("Fullauto mode: Skipping invalid CSS error")
            return 'skip'
        
        # For unknown errors, abort to prevent infinite loops
        logger.error("Fullauto mode: Aborting due to unhandled error type")
        return 'abort'


def create_fullauto_context(enabled: bool = False) -> FullautoMode:
    """
    Create a fullauto mode context manager.
    
    Args:
        enabled: Whether to enable fullauto mode
        
    Returns:
        FullautoMode context manager
    """
    return FullautoMode(enabled=enabled)


def patch_error_recovery_for_fullauto(original_func):
    """
    Decorator to patch error recovery functions for fullauto mode.
    
    Args:
        original_func: The original error recovery function
        
    Returns:
        Patched function that respects fullauto mode
    """
    def wrapper(*args, **kwargs):
        # Check if we're in fullauto mode (could be passed as kwarg or detected)
        fullauto = kwargs.pop('fullauto', False)
        
        if fullauto:
            # In fullauto mode, attempt automatic fixes but don't prompt
            logger.info("Fullauto mode: Attempting automatic error recovery")
            return original_func(*args, **kwargs, interactive=False)
        else:
            # Normal interactive mode
            return original_func(*args, **kwargs)
    
    return wrapper


# Global fullauto state for modules that need to check it
_fullauto_active = False


def is_fullauto_active() -> bool:
    """Check if fullauto mode is currently active."""
    return _fullauto_active


def set_fullauto_active(active: bool):
    """Set the global fullauto state."""
    global _fullauto_active
    _fullauto_active = active