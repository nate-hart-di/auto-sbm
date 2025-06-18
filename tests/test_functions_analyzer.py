"""
Unit tests for the FunctionsAnalyzer to understand sb-inside migration patterns.

These tests demonstrate what content would be migrated to sb-inside.scss based on
functions.php analysis and CommonTheme dependencies.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import os
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sbm.core.functions_analyzer import FunctionsAnalyzer
from sbm.config import Config


class TestFunctionsAnalyzer:
    """Test cases for the FunctionsAnalyzer class."""
    
    @pytest.fixture
    def mock_config(self, tmp_path):
        """Create a mock config with temporary directories."""
        config = Mock(spec=Config)
        config.common_theme_dir = tmp_path / "DealerInspireCommonTheme"
        config.common_theme_dir.mkdir(parents=True, exist_ok=True)
        return config
    
    @pytest.fixture
    def analyzer(self, mock_config):
        """Create a FunctionsAnalyzer instance."""
        return FunctionsAnalyzer(mock_config)
    
    @pytest.fixture
    def sample_theme_dir(self, tmp_path):
        """Create a sample dealer theme directory."""
        theme_dir = tmp_path / "dealer-theme"
        theme_dir.mkdir()
        return theme_dir

    def test_analyze_map_shortcode_with_commontheme_reference(self, analyzer, sample_theme_dir):
        """Test analysis of functions.php with map shortcode referencing CommonTheme."""
        
        # Create sample functions.php with map shortcode
        functions_content = '''<?php
        
// Map shortcode that references CommonTheme
add_shortcode('dealer_map', function($atts) {
    extract(shortcode_atts(array(
        'location' => '',
        'zoom' => '15'
    ), $atts));
    
    ob_start();
    get_template_part('../../DealerInspireCommonTheme/partials/map/dealer-map');
    return ob_get_clean();
});

// Another map shortcode
add_shortcode('directions_widget', function($atts) {
    get_template_part('../../DealerInspireCommonTheme/partials/map/directions-box');
    return "Directions widget";
});

// Non-map shortcode (should be ignored)
add_shortcode('contact_form', function($atts) {
    get_template_part('partials/contact-form');
    return "Contact form";
});
'''
        
        functions_file = sample_theme_dir / "functions.php"
        functions_file.write_text(functions_content)
        
        # Run analysis
        result = analyzer.analyze_functions_file(sample_theme_dir)
        
        print("\n=== MAP SHORTCODE ANALYSIS ===")
        print(f"Functions file exists: {result['functions_file_exists']}")
        print(f"Migration required: {result['migration_required']}")
        print(f"Map shortcodes found: {len(result['map_shortcodes'])}")
        
        for shortcode in result['map_shortcodes']:
            print(f"\nShortcode: {shortcode['name']}")
            print(f"  Template path: {shortcode['template_path']}")
            print(f"  CommonTheme reference: {shortcode['is_commontheme_reference']}")
        
        print(f"\nPartials to migrate: {len(result['partials_to_migrate'])}")
        for partial in result['partials_to_migrate']:
            print(f"  {partial['source_path']} -> {partial['destination_path']}")
        
        print(f"\nStyles to migrate: {result['styles_to_migrate']}")
        print(f"Warnings: {result['warnings']}")
        print(f"Recommendations: {result['recommendations']}")
        
        # Assertions
        assert result['functions_file_exists'] is True
        assert result['migration_required'] is True
        assert len(result['map_shortcodes']) == 2
        assert len(result['partials_to_migrate']) == 2
        
        # Check specific shortcodes
        dealer_map = next((s for s in result['map_shortcodes'] if s['name'] == 'dealer_map'), None)
        assert dealer_map is not None
        assert dealer_map['is_commontheme_reference'] is True
        assert 'partials/map/dealer-map' in dealer_map['template_path']
    
    def test_sb_inside_style_migration_simulation(self, analyzer, sample_theme_dir, mock_config):
        """Test what would be migrated to sb-inside.scss."""
        
        # Create CommonTheme SCSS files that would be migrated
        css_dir = mock_config.common_theme_dir / "css"
        css_dir.mkdir(parents=True, exist_ok=True)
        
        # Create sample map-related SCSS
        map_scss_content = '''/* Map Container Styles */
.dealer-map-container {
    position: relative;
    width: 100%;
    height: 400px;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    
    @media (max-width: 768px) {
        height: 300px;
    }
    
    .map-loading {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 100%;
        background: var(--light-gray);
        color: var(--text-muted);
    }
    
    .map-error {
        padding: 20px;
        text-align: center;
        background: var(--error-bg);
        color: var(--error-text);
    }
}

/* Map Overlay Elements */
.map-overlay {
    position: absolute;
    top: 10px;
    right: 10px;
    background: white;
    padding: 8px 12px;
    border-radius: 4px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    z-index: 1000;
    
    &.directions-toggle {
        cursor: pointer;
        transition: background 0.2s ease;
        
        &:hover {
            background: var(--primary);
            color: white;
        }
    }
}'''

        directions_scss_content = '''/* Directions Box Styles */
.directions-container {
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
    overflow: hidden;
    margin-top: 20px;
    
    .directions-header {
        background: var(--primary);
        color: white;
        padding: 16px 20px;
        font-weight: 600;
        
        .close-btn {
            float: right;
            background: none;
            border: none;
            color: white;
            font-size: 18px;
            cursor: pointer;
            
            &:hover {
                opacity: 0.8;
            }
        }
    }
    
    .directions-content {
        padding: 20px;
        max-height: 400px;
        overflow-y: auto;
        
        .step {
            display: flex;
            margin-bottom: 16px;
            
            .step-number {
                flex-shrink: 0;
                width: 24px;
                height: 24px;
                background: var(--secondary);
                color: white;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 12px;
                font-weight: bold;
                margin-right: 12px;
            }
            
            .step-text {
                flex: 1;
                line-height: 1.5;
                
                .distance {
                    color: var(--text-muted);
                    font-size: 14px;
                    margin-left: 8px;
                }
            }
        }
    }
    
    @media (max-width: 768px) {
        margin-top: 16px;
        
        .directions-content {
            padding: 16px;
            
            .step {
                margin-bottom: 12px;
                
                .step-number {
                    width: 20px;
                    height: 20px;
                    font-size: 11px;
                }
            }
        }
    }
}'''

        # Write the SCSS files
        (css_dir / "_dealer-map.scss").write_text(map_scss_content)
        (css_dir / "_directions-box.scss").write_text(directions_scss_content)
        
        # Create functions.php that would trigger these migrations
        functions_content = '''<?php
add_shortcode('dealer_map', function($atts) {
    get_template_part('../../DealerInspireCommonTheme/partials/map/dealer-map');
    return ob_get_clean();
});

add_shortcode('directions_box', function($atts) {
    get_template_part('../../DealerInspireCommonTheme/partials/map/directions-box'); 
    return ob_get_clean();
});
'''
        
        functions_file = sample_theme_dir / "functions.php"
        functions_file.write_text(functions_content)
        
        # Create initial sb-inside.scss
        sb_inside_initial = '''/* Site Builder Inside Page Styles */

.page-header {
    background: var(--primary);
    color: white;
    padding: 40px 0;
    text-align: center;
}

.content-wrapper {
    max-width: 1200px;
    margin: 0 auto;
    padding: 40px 20px;
}
'''
        
        sb_inside_file = sample_theme_dir / "sb-inside.scss"
        sb_inside_file.write_text(sb_inside_initial)
        
        # Run analysis and migration
        analysis = analyzer.analyze_functions_file(sample_theme_dir)
        migration_result = analyzer.migrate_map_dependencies(sample_theme_dir, analysis)
        
        print("\n=== SB-INSIDE MIGRATION SIMULATION ===")
        print(f"Migration successful: {migration_result['success']}")
        print(f"Styles migrated: {migration_result['styles_migrated']}")
        
        # Read the final sb-inside.scss content
        final_sb_inside = sb_inside_file.read_text()
        
        print("\n=== FINAL SB-INSIDE.SCSS CONTENT ===")
        print(final_sb_inside)
        
        # Check what was migrated
        assert migration_result['success'] is True
        assert len(migration_result['styles_migrated']) > 0
        assert 'MIGRATED FROM' in final_sb_inside
        assert '.dealer-map-container' in final_sb_inside
        assert '.directions-container' in final_sb_inside
        assert 'var(--primary)' in final_sb_inside
        assert '@media (max-width: 768px)' in final_sb_inside
        
        print("\n✅ Successfully migrated map styles to sb-inside.scss")
        print(f"✅ Added {len(migration_result['styles_migrated'])} SCSS modules")
        print("✅ Styles use proper CSS variables (var(--primary), var(--secondary))")
        print("✅ Responsive breakpoints included")
    
    def test_complex_stellantis_map_scenario(self, analyzer, sample_theme_dir, mock_config):
        """Test complex Stellantis-specific map functionality that would be migrated."""
        
        # Create Stellantis-specific CommonTheme partials and styles
        partials_dir = mock_config.common_theme_dir / "partials" / "stellantis"
        partials_dir.mkdir(parents=True, exist_ok=True)
        
        css_dir = mock_config.common_theme_dir / "css" / "stellantis"
        css_dir.mkdir(parents=True, exist_ok=True)
        
        # Stellantis map widget SCSS
        stellantis_map_scss = '''/* Stellantis Brand Map Widget */
.stellantis-map-widget {
    background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
    border-radius: 12px;
    padding: 24px;
    color: white;
    position: relative;
    overflow: hidden;
    
    &::before {
        content: "";
        position: absolute;
        top: -50%;
        right: -50%;
        width: 200%;
        height: 200%;
        background: url('/themes/DealerInspireCommonTheme/images/stellantis-pattern.svg');
        opacity: 0.1;
        z-index: 1;
    }
    
    .widget-content {
        position: relative;
        z-index: 2;
    }
    
    .map-container {
        background: white;
        border-radius: 8px;
        height: 350px;
        margin: 16px 0;
        position: relative;
        
        .map-iframe {
            width: 100%;
            height: 100%;
            border: none;
            border-radius: 8px;
        }
        
        .map-loading-overlay {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(255, 255, 255, 0.9);
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 8px;
            
            .loading-spinner {
                width: 40px;
                height: 40px;
                border: 3px solid var(--light-gray);
                border-top: 3px solid var(--primary);
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }
        }
    }
    
    .dealer-info {
        display: grid;
        grid-template-columns: 1fr auto;
        gap: 20px;
        margin-top: 20px;
        
        .info-section {
            .dealer-name {
                font-size: 20px;
                font-weight: bold;
                margin-bottom: 8px;
            }
            
            .dealer-address {
                line-height: 1.4;
                opacity: 0.9;
                
                .address-line {
                    display: block;
                }
            }
            
            .dealer-phone {
                margin-top: 12px;
                font-size: 18px;
                font-weight: 600;
                
                a {
                    color: white;
                    text-decoration: none;
                    
                    &:hover {
                        text-decoration: underline;
                    }
                }
            }
        }
        
        .actions-section {
            display: flex;
            flex-direction: column;
            gap: 12px;
            
            .action-btn {
                background: rgba(255, 255, 255, 0.15);
                color: white;
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 6px;
                padding: 12px 20px;
                text-align: center;
                text-decoration: none;
                font-weight: 600;
                transition: all 0.3s ease;
                
                &:hover {
                    background: rgba(255, 255, 255, 0.25);
                    border-color: rgba(255, 255, 255, 0.5);
                    transform: translateY(-2px);
                }
                
                &.primary-action {
                    background: white;
                    color: var(--primary);
                    border-color: white;
                    
                    &:hover {
                        background: rgba(255, 255, 255, 0.9);
                    }
                }
            }
        }
    }
    
    @media (max-width: 1024px) {
        padding: 20px;
        
        .dealer-info {
            grid-template-columns: 1fr;
            
            .actions-section {
                flex-direction: row;
                justify-content: space-between;
            }
        }
    }
    
    @media (max-width: 768px) {
        padding: 16px;
        
        .map-container {
            height: 250px;
            margin: 12px 0;
        }
        
        .dealer-info {
            .info-section {
                .dealer-name {
                    font-size: 18px;
                }
            }
            
            .actions-section {
                flex-direction: column;
                
                .action-btn {
                    padding: 10px 16px;
                }
            }
        }
    }
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

/* FCA Direction Integration */
.fca-directions-integration {
    .directions-panel {
        background: white;
        border-radius: 8px;
        margin-top: 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        
        .panel-header {
            background: var(--stellantis-red, #E31837);
            color: white;
            padding: 16px 20px;
            border-radius: 8px 8px 0 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
            
            .header-title {
                font-weight: 600;
                font-size: 16px;
            }
            
            .toggle-btn {
                background: none;
                border: none;
                color: white;
                font-size: 14px;
                cursor: pointer;
                
                &:hover {
                    opacity: 0.8;
                }
            }
        }
        
        .panel-content {
            padding: 20px;
            
            .route-summary {
                display: flex;
                justify-content: space-between;
                margin-bottom: 20px;
                padding-bottom: 16px;
                border-bottom: 1px solid var(--border-light);
                
                .summary-item {
                    text-align: center;
                    
                    .value {
                        font-size: 18px;
                        font-weight: bold;
                        color: var(--primary);
                    }
                    
                    .label {
                        font-size: 12px;
                        text-transform: uppercase;
                        color: var(--text-muted);
                        margin-top: 4px;
                    }
                }
            }
        }
    }
}
'''
        
        (css_dir / "_stellantis-map-widget.scss").write_text(stellantis_map_scss)
        
        # Complex functions.php with multiple Stellantis map features
        stellantis_functions = '''<?php

// Stellantis Map Widget
add_shortcode('stellantis_map_widget', function($atts) {
    extract(shortcode_atts(array(
        'location_id' => '',
        'brand' => 'stellantis',
        'show_directions' => 'true',
        'height' => '350'
    ), $atts));
    
    ob_start();
    get_template_part('../../DealerInspireCommonTheme/partials/stellantis/map-widget');
    return ob_get_clean();
});

// FCA Directions Integration
add_shortcode('fca_directions', function($atts) {
    get_template_part('../../DealerInspireCommonTheme/partials/stellantis/fca-directions');
    return ob_get_clean();
});

// Interactive dealer locator
add_shortcode('dealer_locator_map', function($atts) {
    get_template_part('../../DealerInspireCommonTheme/partials/map/dealer-locator');
    return ob_get_clean();
});
'''
        
        functions_file = sample_theme_dir / "functions.php"
        functions_file.write_text(stellantis_functions)
        
        # Create base sb-inside.scss
        sb_inside_content = '''/* Site Builder Inside Page Styles */

.page-content {
    background: var(--page-bg, #f8f9fa);
    min-height: 100vh;
    padding: 40px 0;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 20px;
}
'''
        
        sb_inside_file = sample_theme_dir / "sb-inside.scss"
        sb_inside_file.write_text(sb_inside_content)
        
        # Run the analysis
        analysis = analyzer.analyze_functions_file(sample_theme_dir)
        migration_result = analyzer.migrate_map_dependencies(sample_theme_dir, analysis)
        
        print("\n=== STELLANTIS MAP MIGRATION TEST ===")
        print(f"Map shortcodes found: {len(analysis['map_shortcodes'])}")
        
        for shortcode in analysis['map_shortcodes']:
            print(f"  • {shortcode['name']} -> {shortcode['template_path']}")
        
        print(f"Migration required: {analysis['migration_required']}")
        print(f"Styles migrated: {migration_result['styles_migrated']}")
        
        # Check final content
        final_content = sb_inside_file.read_text()
        
        print("\n=== MIGRATED CONTENT ANALYSIS ===")
        print(f"Content length: {len(final_content)} characters")
        print(f"Contains Stellantis styles: {'.stellantis-map-widget' in final_content}")
        print(f"Contains FCA directions: {'.fca-directions-integration' in final_content}")
        print(f"Contains CSS variables: {'var(--primary)' in final_content}")
        print(f"Contains responsive design: {'@media (max-width: 768px)' in final_content}")
        print(f"Contains animations: {'@keyframes' in final_content}")
        
        # Detailed content preview
        if '.stellantis-map-widget' in final_content:
            print("\n✅ STELLANTIS MAP WIDGET STYLES MIGRATED")
            print("   - Gradient backgrounds with brand colors")
            print("   - Interactive map container with loading states") 
            print("   - Responsive dealer info grid")
            print("   - Action buttons with hover effects")
            print("   - Mobile-optimized layouts")
        
        if '.fca-directions-integration' in final_content:
            print("\n✅ FCA DIRECTIONS INTEGRATION MIGRATED")
            print("   - Branded header with Stellantis red")
            print("   - Route summary display")
            print("   - Collapsible panel interface")
        
        # Assertions
        assert migration_result['success'] is True
        assert '.stellantis-map-widget' in final_content
        assert 'var(--primary)' in final_content
        assert '@media (max-width: 768px)' in final_content
        
        print(f"\n🎯 Successfully demonstrated complex Stellantis map migration")
        print(f"🎯 Would migrate {len(migration_result['styles_migrated'])} SCSS modules to sb-inside.scss")


if __name__ == "__main__":
    """Run the tests directly for development."""
    import tempfile
    
    print("🧪 Running Functions Analyzer Unit Tests")
    print("=" * 50)
    
    # Create temporary directories
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # Mock config
        config = Mock(spec=Config)
        config.common_theme_dir = tmp_path / "DealerInspireCommonTheme"
        config.common_theme_dir.mkdir(parents=True, exist_ok=True)
        
        # Create analyzer
        analyzer = FunctionsAnalyzer(config)
        
        # Create sample theme
        theme_dir = tmp_path / "dealer-theme"
        theme_dir.mkdir()
        
        # Create test instance
        test_instance = TestFunctionsAnalyzer()
        
        # Run tests
        print("\n1. Testing basic map shortcode analysis...")
        test_instance.test_analyze_map_shortcode_with_commontheme_reference(analyzer, theme_dir)
        
        print("\n2. Testing sb-inside style migration...")
        test_instance.test_sb_inside_style_migration_simulation(analyzer, theme_dir, config)
        
        print("\n3. Testing complex Stellantis scenario...")
        test_instance.test_complex_stellantis_map_scenario(analyzer, theme_dir, config)
        
        print("\n" + "=" * 50)
        print("✅ All tests completed successfully!")
        print("\nKey findings:")
        print("• Map shortcodes are properly detected and analyzed")
        print("• CommonTheme dependencies are identified correctly")
        print("• SCSS content is migrated to sb-inside.scss with proper headers")
        print("• Stellantis-specific styling is preserved during migration")
        print("• CSS variables and responsive design patterns are maintained") 
