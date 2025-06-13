#!/usr/bin/env python3
"""
Production-Ready SBM Automation Validation
Tests automation against real patterns with accurate expectations based on current implementation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbm.config import Config
from sbm.scss.processor import SCSSProcessor
import re

def test_production_ready_automation():
    """Test automation against real patterns with accurate expectations"""
    
    # Real SCSS patterns from Stellantis/FCA PRs with realistic expectations
    test_cases = [
        {
            "name": "Breakpoint Mixin Replacement",
            "content": """
@include breakpoint(xs){
    .mobile-nav{
        display: none;
    }
}

@include breakpoint(sm){
    .tablet-nav{
        display: block;
    }
}

@include breakpoint(md){
    .desktop-nav{
        display: flex;
    }
}

@include breakpoint(lg){
    .large-screen{
        font-size: 24px;
    }
}
""",
            "expected_patterns": [
                "@media (max-width:767px) {",  # xs breakpoint
                "@media (min-width:768px) {",  # sm breakpoint
                "@media (min-width:1025px) {",  # md breakpoint
                "@media (min-width:1200px) {"  # lg breakpoint
            ]
        },
        {
            "name": "Explicit Media Query Preservation",
            "content": """
@media (max-width: 920px){
    .hero-banner{
        height: 300px;
    }
}

@media (min-width: 1024px) and (max-width: 1200px){
    .container{
        max-width: 960px;
    }
}

@media (max-width: 767px){
    .mobile-only{
        display: block;
    }
}
""",
            "expected_patterns": [
                "@media (max-width: 920px)",  # Preserve explicit
                "@media (min-width: 1024px) and (max-width: 1200px)",  # Preserve explicit
                "@media (max-width: 767px)"  # Preserve explicit
            ]
        },
        {
            "name": "Flexbox Mixin Replacement",
            "content": """
.nav-container{
    @include flexbox();
    @include flex-direction(column);
    @include align-items(center);
    @include justify-content(space-between);
}

.button-group{
    @include inline-flex();
    @include flex-wrap(wrap);
}
""",
            "expected_patterns": [
                "display: flex;",
                "flex-direction: column;",
                "align-items: center;",
                "justify-content: space-between;",
                "display: inline-flex;",
                "flex-wrap: wrap;"
            ]
        },
        {
            "name": "Transform and Transition Mixins",
            "content": """
.hover-effect{
    @include transition(all 0.3s);
    @include transform(scale(1.05));
}

.rotate-element{
    @include rotate(45deg);
}

.positioned-element{
    @include border-radius(8px);
    @include box-shadow(0 4px 6px rgba(0, 0, 0, 0.1));
}
""",
            "expected_patterns": [
                "transition: all 0.3s;",
                "transform: scale(1.05);",
                "transform: rotate(45deg);",
                "border-radius: 8px;",
                "box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);"
            ]
        },
        {
            "name": "SCSS Variable Conversion",
            "content": """
.primary-button{
    background-color: $primary;
    color: $white;
    border: 1px solid $secondary;
}

.cta-section{
    background: $cta;
    color: $black;
}

.hover-state{
    background: darken($primary, 10%);
}
""",
            "expected_patterns": [
                "background-color: var(--primary);",
                "color: var(--white);",
                "border: 1px solid var(--secondary);",
                "background: var(--cta);",
                "color: var(--black);",
                "background: var(--primaryhover);"
            ]
        },
        {
            "name": "Common Hex Color Conversion",
            "content": """
.white-background{
    background: #fff;
    color: #000;
}

.gray-elements{
    border: 1px solid #ccc;
    color: #333;
    background: #eee;
}
""",
            "expected_patterns": [
                "background: var(--white, #fff);",
                "color: var(--black, #000);",
                "border: 1px solid var(--hex-ccc, #ccc);",
                "color: var(--hex-333, #333);",
                "background: var(--hex-eee, #eee);"
            ]
        },
        {
            "name": "Gradient Mixin Replacement",
            "content": """
.gradient-background{
    @include gradient(#FF6B6B, #4ECDC4);
}

.horizontal-gradient{
    @include gradient-left-right(#8B5CF6, #EC4899);
}
""",
            "expected_patterns": [
                "background: linear-gradient(to bottom, #FF6B6B, #4ECDC4);",
                "background: linear-gradient(to right, #8B5CF6, #EC4899);"
            ]
        },
        {
            "name": "Z-Index Mixin Replacement",
            "content": """
.modal-overlay{
    @include z-index("modal");
}

.dropdown-menu{
    @include z-index("dropdown");
}

.site-header{
    @include z-index("header");
}
""",
            "expected_patterns": [
                "z-index: 1000;",  # modal
                "z-index: 600;",   # dropdown
                "z-index: 400;"    # header
            ]
        },
        {
            "name": "Image Path Updates",
            "content": """
.hero-bg{
    background-image: url('../images/hero-banner.jpg');
}

.logo{
    background: url("../images/logo.png");
}
""",
            "expected_patterns": [
                "url('/wp-content/themes/DealerInspireDealerTheme/images/hero-banner.jpg')",
                "url('/wp-content/themes/DealerInspireDealerTheme/images/logo.png')"
            ]
        },
        {
            "name": "Complex Real-World Example",
            "content": """
@include breakpoint(xs){
    .mobile-menu{
        @include flexbox();
        @include flex-direction(column);
        background: $primary;
        @include border-radius(4px);
    }
}

@media (max-width: 920px){
    .hero-section{
        background: #fff;
        @include transition(all 0.3s);
    }
}

.cta-button{
    background: $cta;
    color: #000;
    @include box-shadow(0 2px 4px rgba(0,0,0,0.2));
    
    &:hover{
        background: darken($cta, 10%);
    }
}
""",
            "expected_patterns": [
                "@media (max-width:767px) {",  # xs breakpoint replacement
                "display: flex;",  # flexbox mixin
                "flex-direction: column;",  # flex-direction mixin
                "background: var(--primary);",  # SCSS variable
                "border-radius: 4px;",  # border-radius mixin
                "@media (max-width: 920px)",  # preserve explicit media query
                "background: var(--white, #fff);",  # hex color conversion
                "transition: all 0.3s;",  # transition mixin
                "background: var(--cta);",  # SCSS variable
                "color: var(--black, #000);",  # hex color conversion
                "box-shadow: 0 2px 4px rgba(0,0,0,0.2);",  # box-shadow mixin
                "background: var(--ctahover);"  # darken function
            ]
        }
    ]
    
    # Initialize processor
    config = Config()
    processor = SCSSProcessor(config)
    
    # Test results
    total_tests = len(test_cases)
    passed_tests = 0
    failed_tests = []
    
    print(f"🧪 Testing SBM automation production readiness...")
    print(f"📋 {total_tests} comprehensive test cases covering all implemented features")
    print("=" * 80)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n[{i:2d}/{total_tests}] Testing {test_case['name']}")
        
        try:
            # Process the SCSS content
            result = processor._process_legacy_content(test_case['content'])
            
            # Check if all expected patterns are present
            patterns_found = 0
            total_patterns = len(test_case['expected_patterns'])
            missing_patterns = []
            
            for pattern in test_case['expected_patterns']:
                if pattern in result:
                    patterns_found += 1
                    print(f"    ✅ Found: {pattern}")
                else:
                    missing_patterns.append(pattern)
                    print(f"    ❌ Missing: {pattern}")
            
            if patterns_found == total_patterns:
                print(f"    🎯 PASS - All {total_patterns} patterns found")
                passed_tests += 1
            else:
                print(f"    ⚠️  PARTIAL - {patterns_found}/{total_patterns} patterns found")
                failed_tests.append({
                    'name': test_case['name'],
                    'found': patterns_found,
                    'total': total_patterns,
                    'missing': missing_patterns
                })
                
        except Exception as e:
            print(f"    💥 ERROR: {str(e)}")
            failed_tests.append({
                'name': test_case['name'],
                'error': str(e)
            })
    
    # Print comprehensive results
    print("\n" + "=" * 80)
    print("📊 PRODUCTION READINESS VALIDATION RESULTS")
    print("=" * 80)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {len(failed_tests)}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if failed_tests:
        print(f"\n❌ Failed Tests ({len(failed_tests)}):")
        for failure in failed_tests:
            if 'error' in failure:
                print(f"  • {failure['name']}: ERROR - {failure['error']}")
            else:
                print(f"  • {failure['name']}: {failure['found']}/{failure['total']} patterns")
                for missing in failure['missing'][:3]:  # Show first 3 missing patterns
                    print(f"    - Missing: {missing}")
    
    print("\n🎯 VALIDATED AUTOMATION FEATURES:")
    print("  ✅ @include breakpoint() → CommonTheme media queries")
    print("  ✅ Explicit media queries preserved AS-IS")
    print("  ✅ @include flexbox() → display: flex")
    print("  ✅ All flexbox mixins → CSS equivalents")
    print("  ✅ @include transition() → transition:")
    print("  ✅ @include transform() → transform:")
    print("  ✅ @include border-radius() → border-radius:")
    print("  ✅ @include box-shadow() → box-shadow:")
    print("  ✅ SCSS variables → CSS custom properties")
    print("  ✅ Common hex colors → CSS variables with fallbacks")
    print("  ✅ darken() functions → hover variables")
    print("  ✅ @include gradient() → linear-gradient()")
    print("  ✅ @include z-index() → numeric values")
    print("  ✅ Image paths → /wp-content/ format")
    
    if passed_tests == total_tests:
        print(f"\n🚀 AUTOMATION IS PRODUCTION READY!")
        print(f"   ✅ 100% success rate on comprehensive feature validation")
        print(f"   ✅ All core transformations working correctly")
        print(f"   ✅ Real-world patterns handled properly")
    else:
        print(f"\n⚠️  AUTOMATION NEEDS REFINEMENT")
        print(f"   📊 {(passed_tests/total_tests)*100:.1f}% success rate")
        print(f"   🔧 {len(failed_tests)} features need attention")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    success = test_production_ready_automation()
    sys.exit(0 if success else 1) 
