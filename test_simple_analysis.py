import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add the sbm package to the path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sbm'))

from sbm.core.git import GitOperations
from sbm.config import Config

class TestSimpleAnalysis(unittest.TestCase):
    """Test the simple, honest manual change detection."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = Config({})
        self.git_ops = GitOperations(self.config)
    
    @patch('subprocess.run')
    def test_landersmclartycdjr_simple_analysis(self, mock_run):
        """Test simple analysis with the landersmclartycdjr example."""
        # Simulate the actual diff from your example
        landersmclartycdjr_diff = """diff --git a/dealer-themes/landersmclartycdjr/sb-inside.scss b/dealer-themes/landersmclartycdjr/sb-inside.scss
index 1234567..abcdefg 100644
--- a/dealer-themes/landersmclartycdjr/sb-inside.scss
+++ b/dealer-themes/landersmclartycdjr/sb-inside.scss
@@ -195,0 +195,30 @@
+// Adding vrp.css styles for testing
+#results-page .vehicle-description-text a{
+	color: #333;
+}
+
+//adding vdp.css styles for testing
+#ctabox-premium-features {
+  border: 3px solid #eee;
+  padding: 10px;
+  font-size: 13px;
+  max-height: 240px;
+  overflow-y: auto;
+  width: 100%;
+  .features-link {
+    color: $primary;
+  }
+  .list-group-item {
+    padding: 10px 15px;
+    margin: 10px 0;
+    color: #333;
+    background: #f7f7f7;
+    border-radius: 0 !important;
+    border: none;
+    h3 {
+      margin-top: 0;
+      font-size: 15px;
+    }
+  }
+}"""
        
        mock_run.side_effect = [
            # git diff --unified=3
            MagicMock(stdout=landersmclartycdjr_diff, returncode=0),
            # git diff --name-only
            MagicMock(stdout="dealer-themes/landersmclartycdjr/sb-inside.scss\n", returncode=0)
        ]
        
        manual_analysis = self.git_ops._detect_manual_changes()
        
        # Should detect manual changes
        self.assertTrue(manual_analysis['has_manual_changes'])
        
        # Should count 29 lines (actual + lines in the diff, excluding the comment line)
        self.assertEqual(manual_analysis['estimated_manual_lines'], 29)
        
        # Should track file line counts
        self.assertIn('sb-inside.scss', manual_analysis['file_line_counts'])
        self.assertEqual(manual_analysis['file_line_counts']['sb-inside.scss'], 29)
        
        # Should have simple description
        descriptions = manual_analysis['change_descriptions']
        self.assertEqual(len(descriptions), 1)
        self.assertIn('Manual changes to sb-inside.scss (29 lines)', descriptions[0])
        self.assertIn('please add details if needed', descriptions[0])
    
    @patch('subprocess.run')
    def test_pr_content_with_simple_analysis(self, mock_run):
        """Test PR content generation with simple analysis."""
        simple_diff = """diff --git a/dealer-themes/testdealer/sb-inside.scss b/dealer-themes/testdealer/sb-inside.scss
@@ -10,0 +10,5 @@
+.custom-style {
+  color: red;
+  padding: 10px;
+}
+"""
        
        mock_run.side_effect = [
            # _analyze_migration_changes
            MagicMock(stdout="A\tdealer-themes/testdealer/sb-inside.scss\n", returncode=0),
            # _detect_manual_changes git diff
            MagicMock(stdout=simple_diff, returncode=0),
            # _detect_manual_changes git diff --name-only
            MagicMock(stdout="dealer-themes/testdealer/sb-inside.scss\n", returncode=0)
        ]
        
        pr_content = self.git_ops._build_stellantis_pr_content("testdealer", "testdealer-sbm0725", {})
        
        # Should contain simple, honest description
        self.assertIn('Manual changes to sb-inside.scss (4 lines) - please add details if needed', pr_content['body'])
        
        # Should NOT contain any of the old generic descriptions
        unwanted_phrases = [
            'Improved interactive states',
            'Enhanced responsive design',
            'Applied custom color schemes',
            'Fine-tuned spacing and layout',
            'Adding vehicle results page',
            'Modified premium features'
        ]
        for phrase in unwanted_phrases:
            self.assertNotIn(phrase, pr_content['body'])
    
    @patch('subprocess.run')
    def test_no_manual_changes(self, mock_run):
        """Test when no manual changes exist."""
        mock_run.side_effect = [
            # git diff --unified=3 (empty)
            MagicMock(stdout="", returncode=0),
            # git diff --name-only (empty)
            MagicMock(stdout="", returncode=0)
        ]
        
        manual_analysis = self.git_ops._detect_manual_changes()
        
        self.assertFalse(manual_analysis['has_manual_changes'])
        self.assertEqual(manual_analysis['estimated_manual_lines'], 0)
        self.assertEqual(len(manual_analysis['change_descriptions']), 0)
        self.assertEqual(len(manual_analysis['file_line_counts']), 0)

if __name__ == '__main__':
    unittest.main() 
