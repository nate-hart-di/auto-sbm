#!/usr/bin/env python3
"""
Demo to show exactly what content gets migrated to sb-inside.scss
"""

def demo_sb_inside_migration():
    """Show what content would be migrated to sb-inside.scss from CommonTheme dependencies"""
    
    print("🎯 SB-INSIDE MIGRATION CONTENT DEMO")
    print("=" * 70)
    print()
    print("This demo shows what types of content get migrated to sb-inside.scss")
    print("when the FunctionsAnalyzer detects map shortcodes that reference CommonTheme.")
    print()
    
    # Original sb-inside.scss (before migration)
    original_content = '''/* Site Builder Inside Page Styles */

.page-header {
    background: var(--primary);
    color: white;
    padding: 40px 0;
    text-align: center;
    
    h1 {
        font-size: 32px;
        font-weight: 700;
        margin: 0;
    }
}

.content-wrapper {
    max-width: 1200px;
    margin: 0 auto;
    padding: 40px 20px;
    
    .main-content {
        background: white;
        border-radius: 8px;
        padding: 30px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
    
    @media (max-width: 768px) {
        padding: 20px 16px;
        
        .main-content {
            padding: 20px;
        }
    }
}'''
    
    # Content that gets appended when CommonTheme map dependencies are found
    migrated_content = '''

/* MIGRATED FROM partials/map/_dealer-map.scss *****************************/

/* Dealer Map Container - Core map display functionality */
.dealer-map-container {
    position: relative;
    width: 100%;
    height: 400px;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    background: var(--white);
    
    /* Responsive height adjustments for different screen sizes */
    @media (max-width: 1024px) {
        height: 350px;
    }
    
    @media (max-width: 768px) {
        height: 300px;
        margin: 16px 0;
    }
    
    /* Loading state with animated spinner */
    .map-loading {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 100%;
        background: var(--light-gray);
        color: var(--text-muted);
        font-size: 16px;
        
        .loading-spinner {
            width: 32px;
            height: 32px;
            border: 3px solid var(--border-light);
            border-top: 3px solid var(--primary);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-right: 12px;
        }
    }
    
    /* Error state styling */
    .map-error {
        padding: 20px;
        text-align: center;
        background: var(--error-bg);
        color: var(--error-text);
        border-radius: 4px;
        margin: 10px;
    }
    
    /* Interactive overlay elements */
    .map-overlay {
        position: absolute;
        top: 10px;
        right: 10px;
        background: white;
        padding: 8px 12px;
        border-radius: 4px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        z-index: 1000;
        font-size: 14px;
        
        &.directions-toggle {
            cursor: pointer;
            transition: all 0.2s ease;
            
            &:hover {
                background: var(--primary);
                color: white;
                transform: translateY(-1px);
            }
        }
    }
}

/* Loading animation for map spinner */
@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}


/* MIGRATED FROM partials/map/_directions-box.scss **************************/

/* Directions Container - Interactive routing functionality */
.directions-container {
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
    overflow: hidden;
    margin-top: 20px;
    
    /* Header with close functionality */
    .directions-header {
        background: var(--primary);
        color: white;
        padding: 16px 20px;
        font-weight: 600;
        display: flex;
        justify-content: space-between;
        align-items: center;
        
        .header-title {
            font-size: 16px;
        }
        
        .close-btn {
            background: none;
            border: none;
            color: white;
            font-size: 18px;
            cursor: pointer;
            padding: 4px;
            
            &:hover {
                opacity: 0.8;
            }
        }
    }
    
    /* Scrollable content area with route information */
    .directions-content {
        padding: 20px;
        max-height: 400px;
        overflow-y: auto;
        
        /* Route summary with time and distance */
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
                    display: block;
                }
                
                .label {
                    font-size: 12px;
                    text-transform: uppercase;
                    color: var(--text-muted);
                    margin-top: 4px;
                }
            }
        }
        
        /* Individual step-by-step directions */
        .direction-step {
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
            
            .step-content {
                flex: 1;
                line-height: 1.5;
                
                .step-instruction {
                    color: var(--text-dark);
                    margin-bottom: 4px;
                }
                
                .step-distance {
                    color: var(--text-muted);
                    font-size: 14px;
                }
            }
        }
    }
    
    /* Mobile-responsive adjustments */
    @media (max-width: 768px) {
        margin-top: 16px;
        
        .directions-content {
            padding: 16px;
            
            .direction-step {
                margin-bottom: 12px;
                
                .step-number {
                    width: 20px;
                    height: 20px;
                    font-size: 11px;
                }
            }
        }
    }
}


/* MIGRATED FROM partials/stellantis/_map-row.scss **************************/

/* Stellantis-specific map integration for FCA brands */
#mapRow {
    background: var(--page-bg, #f8f9fa);
    padding: 60px 0;
    
    .container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 0 20px;
    }
    
    .map-section-header {
        text-align: center;
        margin-bottom: 40px;
        
        h2 {
            font-size: 32px;
            color: var(--text-dark);
            margin-bottom: 16px;
        }
        
        .section-description {
            font-size: 18px;
            color: var(--text-muted);
            max-width: 600px;
            margin: 0 auto;
            line-height: 1.6;
        }
    }
    
    .map-grid {
        display: grid;
        grid-template-columns: 2fr 1fr;
        gap: 40px;
        align-items: start;
        
        @media (max-width: 1024px) {
            grid-template-columns: 1fr;
            gap: 30px;
        }
    }
    
    .map-panel {
        .dealer-map-container {
            height: 500px;
            
            @media (max-width: 768px) {
                height: 400px;
            }
        }
    }
    
    .dealer-info-panel {
        background: white;
        border-radius: 12px;
        padding: 30px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        
        .dealer-header {
            border-bottom: 2px solid var(--primary);
            padding-bottom: 20px;
            margin-bottom: 24px;
            
            .dealer-name {
                font-size: 24px;
                font-weight: 700;
                color: var(--text-dark);
                margin-bottom: 8px;
            }
            
            .dealer-brand {
                font-size: 14px;
                text-transform: uppercase;
                color: var(--primary);
                font-weight: 600;
                letter-spacing: 1px;
            }
        }
        
        .contact-info {
            .info-group {
                margin-bottom: 20px;
                
                .label {
                    font-size: 12px;
                    text-transform: uppercase;
                    color: var(--text-muted);
                    font-weight: 600;
                    margin-bottom: 4px;
                }
                
                .value {
                    font-size: 16px;
                    color: var(--text-dark);
                    line-height: 1.4;
                }
                
                a {
                    color: var(--primary);
                    text-decoration: none;
                    
                    &:hover {
                        text-decoration: underline;
                    }
                }
            }
        }
        
        .action-buttons {
            display: flex;
            flex-direction: column;
            gap: 12px;
            margin-top: 30px;
            
            .btn {
                padding: 12px 20px;
                border-radius: 6px;
                text-align: center;
                text-decoration: none;
                font-weight: 600;
                transition: all 0.3s ease;
                
                &.btn-primary {
                    background: var(--primary);
                    color: white;
                    border: 2px solid var(--primary);
                    
                    &:hover {
                        background: var(--primary-dark);
                        transform: translateY(-2px);
                    }
                }
                
                &.btn-outline {
                    background: transparent;
                    color: var(--primary);
                    border: 2px solid var(--primary);
                    
                    &:hover {
                        background: var(--primary);
                        color: white;
                    }
                }
            }
        }
    }
}

/* Directions box integration */
#directionsBox {
    margin-top: 30px;
    
    @media (max-width: 1024px) {
        margin-top: 20px;
    }
}
'''
    
    final_content = original_content + migrated_content
    
    print("📋 ORIGINAL SB-INSIDE.SCSS (before migration):")
    print("=" * 50)
    print(original_content)
    
    print("\n\n📋 CONTENT MIGRATED TO SB-INSIDE.SCSS (from CommonTheme):")
    print("=" * 50)
    print(migrated_content)
    
    print("\n\n📊 MIGRATION ANALYSIS:")
    print("=" * 50)
    print(f"Original size: {len(original_content)} characters")
    print(f"Migrated content: {len(migrated_content)} characters") 
    print(f"Final size: {len(final_content)} characters")
    print(f"Size increase: {len(migrated_content)} characters ({((len(migrated_content) / len(original_content)) * 100):.1f}% increase)")
    
    print(f"\n📋 CONTENT FEATURES ADDED:")
    print("✅ Responsive map container with loading states")
    print("✅ Interactive directions box with step-by-step navigation") 
    print("✅ Stellantis #mapRow and #directionsBox components for FCA compliance")
    print("✅ CSS variable integration (var(--primary), var(--secondary))")
    print("✅ Mobile-responsive breakpoints (768px, 1024px)")
    print("✅ Loading animations and interactive hover effects")
    print("✅ Error state handling and accessibility features")
    print("✅ Site Builder-compliant styling patterns")
    
    print(f"\n🎯 MIGRATION TRIGGER CONDITIONS:")
    print("This content is added to sb-inside.scss when:")
    print("1. functions.php contains map-related shortcodes")
    print("2. Shortcodes reference CommonTheme partials (../../DealerInspireCommonTheme/)")
    print("3. Associated SCSS files exist in CommonTheme/css/")
    print("4. FunctionsAnalyzer.migrate_map_dependencies() is called")
    
    print(f"\n🔍 EXAMPLE TRIGGERING SHORTCODE:")
    print("""add_shortcode('dealer_map', function($atts) {
    get_template_part('../../DealerInspireCommonTheme/partials/map/dealer-map');
    return ob_get_clean();
});""")
    
    print(f"\n✅ RESULT: Enterprise-grade map functionality ready for Site Builder integration!")


if __name__ == "__main__":
    demo_sb_inside_migration() 
