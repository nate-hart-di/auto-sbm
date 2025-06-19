"""
User Review Module for SBM Tool V2.

Handles manual review step in the migration workflow, allowing users to make
additional changes and tracking automated vs manual modifications.
"""

import hashlib
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from sbm.config import Config
from sbm.utils.logger import get_logger


class UserReviewManager:
    """Manages the user review step in migration workflow."""
    
    def __init__(self, config: Config):
        """Initialize user review manager."""
        self.config = config
        self.logger = get_logger("user_review")
        self.automated_state: Dict[str, Any] = {}
        self.manual_state: Dict[str, Any] = {}
    
    def start_review_session(self, slug: str, automated_files: List[str]) -> Dict[str, Any]:
        """
        Start a user review session after automated migration.
        
        Args:
            slug: Dealer theme slug
            automated_files: List of files created/modified by automation
            
        Returns:
            Review session results
        """
        self.logger.info("🔍 Starting user review session...")
        
        # Capture automated state
        self.automated_state = self._capture_file_state(slug, automated_files)
        
        # Display review instructions
        self._display_review_instructions(slug, automated_files)
        
        # Wait for user confirmation
        self._wait_for_user_confirmation()
        
        # Capture manual state after user review
        self.manual_state = self._capture_file_state(slug, automated_files)
        
        # Analyze changes
        changes_analysis = self._analyze_changes()
        
        self.logger.success("✅ User review session completed!")
        
        return {
            "automated_files": automated_files,
            "automated_state": self.automated_state,
            "manual_state": self.manual_state,
            "changes_analysis": changes_analysis,
            "user_made_changes": changes_analysis["has_manual_changes"],
            "timestamp": time.time()
        }
    
    def _capture_file_state(self, slug: str, files: List[str]) -> Dict[str, Any]:
        """Capture current state of specified files."""
        theme_path = self.config.get_theme_path(slug)
        state = {
            "timestamp": time.time(),
            "files": {}
        }
        
        for filename in files:
            file_path = theme_path / filename
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding='utf-8')
                    state["files"][filename] = {
                        "exists": True,
                        "size": len(content),
                        "lines": len(content.split('\n')),
                        "hash": hashlib.md5(content.encode()).hexdigest(),
                        "last_modified": file_path.stat().st_mtime
                    }
                except Exception as e:
                    state["files"][filename] = {
                        "exists": True,
                        "error": str(e)
                    }
            else:
                state["files"][filename] = {"exists": False}
        
        return state
    
    def _display_review_instructions(self, slug: str, automated_files: List[str]) -> None:
        """Display review instructions to the user."""
        theme_path = self.config.get_theme_path(slug)
        
        self.logger.info("")
        self.logger.info("=" * 80)
        self.logger.info("👥 USER REVIEW SESSION - MANUAL CHANGES WELCOME")
        self.logger.info("=" * 80)
        self.logger.info(f"🏪 Dealer: {slug}")
        self.logger.info(f"📁 Theme Directory: {theme_path}")
        self.logger.info("")
        self.logger.info("📋 AUTOMATED MIGRATION COMPLETED:")
        
        for filename in automated_files:
            file_path = theme_path / filename
            if file_path.exists():
                size = file_path.stat().st_size
                self.logger.info(f"   ✅ {filename} ({size} bytes)")
            else:
                self.logger.warning(f"   ⚠️  {filename} (not found)")
        
        self.logger.info("")
        self.logger.info("🔍 REVIEW INSTRUCTIONS:")
        self.logger.info("   1. Open the files above in your editor")
        self.logger.info("   2. Review the automated SCSS migration")
        self.logger.info("   3. Make any additional changes you need")
        self.logger.info("   4. Save all files when you're done")
        self.logger.info("   5. Type 'done' below to continue")
        self.logger.info("")
        self.logger.info("💡 TIP: The automation will track your changes separately")
        self.logger.info("      so we can improve the migration logic!")
        self.logger.info("")
        self.logger.info("🎯 COMMON MANUAL IMPROVEMENTS:")
        self.logger.info("   • Add brand-specific styling")
        self.logger.info("   • Adjust responsive breakpoints")
        self.logger.info("   • Fine-tune color schemes")
        self.logger.info("   • Add custom animations/transitions")
        self.logger.info("   • Optimize for specific dealer needs")
        self.logger.info("")
        self.logger.info("=" * 80)
    
    def _wait_for_user_confirmation(self) -> None:
        """Wait for user to complete their review."""
        self.logger.info("⏳ Waiting for you to complete your review...")
        self.logger.info("💬 Type 'done' when you have finished your manual changes:")
        
        while True:
            try:
                user_input = input("   👤 Review status: ").strip().lower()
                
                if user_input == 'done':
                    self.logger.success("✅ Review marked as complete!")
                    break
                elif user_input in ['help', '?']:
                    self.logger.info("   💡 Commands:")
                    self.logger.info("      'done' - Continue with automation")
                    self.logger.info("      'help' - Show this help")
                elif user_input in ['status', 'files']:
                    self._show_current_status()
                else:
                    self.logger.warning(f"   ❓ Unknown command: '{user_input}'")
                    self.logger.info("   💬 Type 'done' to continue, or 'help' for options")
                    
            except KeyboardInterrupt:
                self.logger.warning("\n⚠️  Review interrupted. Type 'done' to continue or Ctrl+C again to exit.")
                continue
            except EOFError:
                self.logger.warning("\n⚠️  Input ended. Assuming review is complete.")
                break
    
    def _show_current_status(self) -> None:
        """Show current file status during review."""
        self.logger.info("📄 Current file status:")
        for filename, file_info in self.automated_state["files"].items():
            if file_info.get("exists"):
                self.logger.info(f"   📝 {filename} - {file_info.get('size', 0)} bytes")
            else:
                self.logger.info(f"   ❌ {filename} - not found")
    
    def _analyze_changes(self) -> Dict[str, Any]:
        """Analyze changes between automated and manual states."""
        analysis = {
            "has_manual_changes": False,
            "files_modified": [],
            "files_unchanged": [],
            "size_changes": {},
            "content_changes": {},
            "summary": ""
        }
        
        for filename in self.automated_state["files"].keys():
            auto_file = self.automated_state["files"][filename]
            manual_file = self.manual_state["files"].get(filename, {})
            
            if not auto_file.get("exists") or not manual_file.get("exists"):
                continue
            
            # Check for content changes
            auto_hash = auto_file.get("hash")
            manual_hash = manual_file.get("hash")
            
            if auto_hash != manual_hash:
                analysis["has_manual_changes"] = True
                analysis["files_modified"].append(filename)
                
                # Track size changes
                auto_size = auto_file.get("size", 0)
                manual_size = manual_file.get("size", 0)
                size_diff = manual_size - auto_size
                
                analysis["size_changes"][filename] = {
                    "automated_size": auto_size,
                    "manual_size": manual_size,
                    "difference": size_diff
                }
                
                # Track line changes
                auto_lines = auto_file.get("lines", 0)
                manual_lines = manual_file.get("lines", 0)
                line_diff = manual_lines - auto_lines
                
                analysis["content_changes"][filename] = {
                    "automated_lines": auto_lines,
                    "manual_lines": manual_lines,
                    "line_difference": line_diff
                }
                
                self.logger.info(f"   📝 {filename}: {size_diff:+d} bytes, {line_diff:+d} lines")
            else:
                analysis["files_unchanged"].append(filename)
        
        # Generate summary
        if analysis["has_manual_changes"]:
            modified_count = len(analysis["files_modified"])
            analysis["summary"] = f"User made manual changes to {modified_count} file(s)"
            self.logger.success(f"✅ Manual changes detected in {modified_count} file(s)")
        else:
            analysis["summary"] = "No manual changes made"
            self.logger.info("ℹ️  No manual changes detected")
        
        return analysis
    
    def generate_commit_messages(self, review_result: Dict[str, Any]) -> Dict[str, str]:
        """Generate commit messages for automated and manual changes."""
        automated_files = review_result["automated_files"]
        changes_analysis = review_result["changes_analysis"]
        
        # Base automated commit message
        automated_msg = "SBM FE Audit - Automated Migration"
        if automated_files:
            automated_msg += f" - Created/Modified {', '.join(automated_files)}"
        
        # Manual changes commit message (if needed)
        manual_msg = None
        if changes_analysis["has_manual_changes"]:
            modified_files = changes_analysis["files_modified"]
            manual_msg = f"SBM FE Audit - Manual Refinements - Updated {', '.join(modified_files)}"
        
        return {
            "automated_commit": automated_msg,
            "manual_commit": manual_msg,
            "combined_commit": self._generate_combined_commit_message(review_result)
        }
    
    def _generate_combined_commit_message(self, review_result: Dict[str, Any]) -> str:
        """Generate a combined commit message covering both automated and manual work."""
        automated_files = review_result["automated_files"]
        changes_analysis = review_result["changes_analysis"]
        
        msg_parts = ["SBM FE Audit"]
        
        # Automated work
        if automated_files:
            msg_parts.append(f"Automated: {', '.join(automated_files)}")
        
        # Manual work
        if changes_analysis["has_manual_changes"]:
            modified_files = changes_analysis["files_modified"]
            msg_parts.append(f"Manual: {', '.join(modified_files)}")
        
        return " - ".join(msg_parts)
    
    def get_pr_description_sections(self, review_result: Dict[str, Any]) -> Dict[str, str]:
        """Generate PR description sections for automated vs manual work."""
        automated_files = review_result["automated_files"]
        changes_analysis = review_result["changes_analysis"]
        
        # Automated section
        automated_section = "### 🤖 Automated Migration\n"
        if automated_files:
            automated_section += "The SBM tool automatically migrated the following files:\n"
            for filename in automated_files:
                automated_section += f"- `{filename}`\n"
        else:
            automated_section += "No automated changes\n"
        
        # Manual section
        manual_section = "### 👤 Manual Refinements\n"
        if changes_analysis["has_manual_changes"]:
            modified_files = changes_analysis["files_modified"]
            manual_section += "Developer made additional manual improvements to:\n"
            for filename in modified_files:
                size_change = changes_analysis["size_changes"].get(filename, {})
                size_diff = size_change.get("difference", 0)
                manual_section += f"- `{filename}` ({size_diff:+d} bytes)\n"
            
            manual_section += "\n**Manual changes help improve the automation** - these will be reviewed to enhance future migrations.\n"
        else:
            manual_section += "No manual changes were needed - automation was sufficient!\n"
        
        return {
            "automated_section": automated_section,
            "manual_section": manual_section
        } 
