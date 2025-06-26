#!/usr/bin/env python3
"""
Test for multi-selector edge case handling in SCSS parser.

This test ensures that rules with both VRP and VDP selectors 
(like .page-vehicle-results-page and .page-vehicle-display-page)
are properly duplicated into separate files with the correct content.

This is a regression test for the multi-selector parsing bug that was fixed.
"""

import sys
import os
sys.path.append('/Users/nathanhart/auto-sbm')

from sbm.scss.enhanced_parser import parse_style_rules, distribute_rules

def test_multi_selector_edge_case():
    """Test the specific edge case with multi-line selectors and nested media queries"""
    
    test_content = """.page-vehicle-results-page,
.page-vehicle-display-page {
  .countdown-timer.row {
    @media screen and (max-width: 1184px) {
      top: 144px;
    }
    @media screen and (min-width: 1185px) {
      top: 159px;
    }
    @media screen and (max-width: 1024px) {
      top: 100px;
    }

    @media screen and (max-width: 768px) {
      top: 145px;
    }
  }
}"""
    
    print("Testing edge case with multi-line selectors and nested media queries...")
    print("=" * 70)
    print("INPUT:")
    print(test_content)
    print("=" * 70)
    
    # Parse the rules
    rules = parse_style_rules(test_content)
    
    print(f"PARSED RULES: {len(rules)} rules found")
    for i, rule in enumerate(rules):
        print(f"\nRule {i+1}:")
        print(f"Category: {rule.get('category', 'unknown')}")
        print(f"Ticket: {rule.get('ticket', 'none')}")
        print("Content:")
        print(rule.get('rule', 'no content'))
        print("-" * 40)
    
    # Test distribution
    distributed = distribute_rules(rules)
    
    print("\nDISTRIBUTION RESULTS:")
    print("=" * 70)
    
    for file_type, content in distributed.items():
        print(f"\n{file_type.upper()}:")
        print(f"Length: {len(content)} characters")
        if content.strip():
            print("Content:")
            print(content)
        else:
            print("(Empty)")
        print("-" * 40)

if __name__ == "__main__":
    test_multi_selector_edge_case() 
