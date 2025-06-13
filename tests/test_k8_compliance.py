#!/usr/bin/env python3
"""
Test script to verify K8 SBM Guide compliance.
Tests all mixin conversions mentioned in the K8 guide.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sbm'))

from sbm.scss.processor import SCSSProcessor
from sbm.config import Config

def test_k8_mixin_conversions():
    """Test all mixin conversions from K8 SBM Guide."""
    
    # Initialize processor
    config = Config()
    processor = SCSSProcessor(config)
    
    # Test cases from K8 SBM Guide
    test_cases = [
        # 1. Positioning Mixins
        ('@include absolute((top: 0, left: 0));', 'position: absolute; top: 0; left: 0;'),
        ('@include centering(both);', 'position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);'),
        
        # 2. Flexbox Mixins
        ('@include flexbox();', 'display: flex;'),
        ('@include flex-direction(row);', 'flex-direction: row;'),
        ('@include align-items(center);', 'align-items: center;'),
        ('@include justify-content(space-between);', 'justify-content: space-between;'),
        
        # 3. Gradients
        ('@include gradient(#fff, #000);', 'background: linear-gradient(to bottom, #fff, #000);'),
        ('@include gradient-left-right(#fff, #000);', 'background: linear-gradient(to right, #fff, #000);'),
        
        # 4. Font & Typography
        ('@include responsive-font(4vw, 30px, 100px);', 'font-size: clamp(30px, 4vw, 100px);'),
        ('@include font_size(18);', 'font-size: 18px;'),
        
        # 5. Placeholder Styling
        ('@include placeholder-color;', '&::placeholder { color: var(--placeholder-color, #999); }'),
        ('@include placeholder-color(#red);', '&::placeholder { color: #red; }'),
        
        # 6. Z-Index
        ('@include z-index("modal");', 'z-index: 1000;'),
        ('@include z-index("overlay");', 'z-index: 800;'),
        
        # 7. Transform & Transition
        ('@include rotate(45deg);', 'transform: rotate(45deg);'),
        ('@include transition(all 0.3s);', 'transition: all 0.3s;'),
        ('@include transform(translateX(10px));', 'transform: translateX(10px);'),
        
        # 8. List Padding - NEW
        ('@include list-padding(left, 20px);', 'padding-left: 20px;'),
        ('@include list-padding(right, 15px);', 'padding-right: 15px;'),
        
        # 9. Appearance
        ('@include appearance(none);', 'appearance: none; -webkit-appearance: none; -moz-appearance: none;'),
        
        # 10. Box Model & Border - NEW
        ('@include border-radius(8px);', 'border-radius: 8px;'),
        ('@include box-shadow(0 2px 4px #0002);', 'box-shadow: 0 2px 4px #0002;'),
        ('@include box-sizing(border-box);', 'box-sizing: border-box;'),
        
        # 11. Breakpoints
        ("@include breakpoint('md') {", '@media (min-width: 768px) {'),
        ("@include breakpoint('lg') {", '@media (min-width: 1024px) {'),
        
        # 12. Utility & Animation - NEW
        ('@include clearfix();', '&::after { content: ""; display: table; clear: both; }'),
        ('@include animation("fade-in 1s");', 'animation: fade-in 1s;'),
        ('@include filter(blur(5px));', 'filter: blur(5px);'),
        
        # 13. Functions - NEW
        ('font-size: em(22);', 'font-size: 1.375rem;'),
        ('width: get-mobile-size(300px);', 'width: 300px;'),
        
        # 14. Visually Hidden
        ('@include visually-hidden();', 'position: absolute !important;'),
        
        # SCSS Variables
        ('color: $primary;', 'color: var(--primary);'),
        ('background: $white;', 'background: var(--white);'),
        
        # Hex Colors
        ('color: #fff;', 'color: var(--white, #fff);'),
        ('background: #000;', 'background: var(--black, #000);'),
        
        # darken() Functions
        ('color: darken(#008000,10%);', 'color: #006600;'),
        ('background: darken($primary, 10%);', 'background: var(--primaryhover);'),
        
        # Image Paths
        ("background: url('../images/bg.jpg');", "background: url('/wp-content/themes/DealerInspireDealerTheme/images/bg.jpg');"),
        
        # Breakpoint Updates
        ('@media (min-width: 920px)', '@media (min-width: 1024px)'),
    ]
    
    print("🧪 Testing K8 SBM Guide Mixin Conversions")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    for i, (input_scss, expected_output) in enumerate(test_cases, 1):
        try:
            result = processor._process_legacy_content(input_scss)
            
            if expected_output in result:
                print(f"✅ Test {i:2d}: PASS")
                print(f"   Input:    {input_scss}")
                print(f"   Expected: {expected_output}")
                print(f"   Result:   {result.strip()}")
                passed += 1
            else:
                print(f"❌ Test {i:2d}: FAIL")
                print(f"   Input:    {input_scss}")
                print(f"   Expected: {expected_output}")
                print(f"   Result:   {result.strip()}")
                failed += 1
            print()
            
        except Exception as e:
            print(f"💥 Test {i:2d}: ERROR - {e}")
            print(f"   Input: {input_scss}")
            failed += 1
            print()
    
    print("=" * 50)
    print(f"📊 Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED! SBM Tool V2 is K8 SBM Guide compliant!")
        return True
    else:
        print(f"⚠️  {failed} tests failed. SBM Tool V2 needs fixes for full K8 compliance.")
        return False

if __name__ == "__main__":
    success = test_k8_mixin_conversions()
    sys.exit(0 if success else 1) 
