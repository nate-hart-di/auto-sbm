"""
Test mixin replacement functionality in SCSS processor.
"""

import pytest
from sbm.scss.processor import SCSSProcessor
from sbm.config import Config


class TestMixinReplacement:
    """Test comprehensive mixin replacement functionality."""
    
    @pytest.fixture
    def processor(self):
        """Create SCSS processor for testing."""
        config = Config()
        return SCSSProcessor(config)
    
    def test_flexbox_mixin_replacement(self, processor):
        """Test that flexbox mixins are properly replaced."""
        legacy_content = """
.container {
    @include flexbox();
    @include flex-direction(row);
    @include align-items(center);
    @include justify-content(space-between);
}
"""
        
        processed = processor._process_legacy_content(legacy_content)
        
        assert 'display: flex;' in processed
        assert 'flex-direction: row;' in processed
        assert 'align-items: center;' in processed
        assert 'justify-content: space-between;' in processed
        assert '@include' not in processed
    
    def test_positioning_mixin_replacement(self, processor):
        """Test that positioning mixins are properly replaced."""
        legacy_content = """
.item {
    @include absolute((top:0, left:0));
}
.center {
    @include centering(both);
}
"""
        
        processed = processor._process_legacy_content(legacy_content)
        
        assert 'position: absolute; top: 0; left: 0;' in processed
        assert 'position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);' in processed
    
    def test_transform_mixin_replacement(self, processor):
        """Test that transform mixins are properly replaced."""
        legacy_content = """
.spin {
    @include rotate(45deg);
}
.move {
    @include transform(translateX(10px));
}
.fade {
    @include transition(all 0.3s);
}
"""
        
        processed = processor._process_legacy_content(legacy_content)
        
        assert 'transform: rotate(45deg);' in processed
        assert 'transform: translateX(10px);' in processed
        assert 'transition: all 0.3s;' in processed
    
    def test_gradient_mixin_replacement(self, processor):
        """Test that gradient mixins are properly replaced."""
        legacy_content = """
.bg {
    @include gradient(#fff, #000);
}
.bg-lr {
    @include gradient-left-right(#fff, #000);
}
"""
        
        processed = processor._process_legacy_content(legacy_content)
        
        assert 'background: linear-gradient(to bottom, #fff, #000);' in processed
        assert 'background: linear-gradient(to right, #fff, #000);' in processed
    
    def test_typography_mixin_replacement(self, processor):
        """Test that typography mixins are properly replaced."""
        legacy_content = """
.text {
    @include font_size(18);
}
h2 {
    @include responsive-font(4vw, 30px, 100px);
}
"""
        
        processed = processor._process_legacy_content(legacy_content)
        
        assert 'font-size: 18px;' in processed
        assert 'font-size: clamp(30px, 4vw, 100px);' in processed
    
    def test_breakpoint_mixin_replacement(self, processor):
        """Test that breakpoint mixins are properly replaced."""
        legacy_content = """
@include breakpoint('md') {
    .element {
        font-size: 1.2rem;
    }
}
"""
        
        processed = processor._process_legacy_content(legacy_content)
        
        assert '@media (min-width: 768px) {' in processed
        assert '@include breakpoint' not in processed
    
    def test_utility_mixin_replacement(self, processor):
        """Test that utility mixins are properly replaced."""
        legacy_content = """
.clearfix {
    @include clearfix();
}
.sr-only {
    @include visually-hidden();
}
.select {
    @include appearance(none);
}
"""
        
        processed = processor._process_legacy_content(legacy_content)
        
        assert '&::after { content: ""; display: table; clear: both; }' in processed
        assert 'position: absolute !important;' in processed
        assert 'appearance: none; -webkit-appearance: none; -moz-appearance: none;' in processed
    
    def test_z_index_mixin_replacement(self, processor):
        """Test that z-index mixins are properly replaced."""
        legacy_content = """
.modal {
    @include z-index("modal");
}
.overlay {
    @include z-index("overlay");
}
"""
        
        processed = processor._process_legacy_content(legacy_content)
        
        assert 'z-index: 1000;' in processed
        assert 'z-index: 800;' in processed
    
    def test_box_model_mixin_replacement(self, processor):
        """Test that box model mixins are properly replaced."""
        legacy_content = """
.card {
    @include border-radius(8px);
    @include box-sizing(border-box);
}
"""
        
        processed = processor._process_legacy_content(legacy_content)
        
        assert 'border-radius: 8px;' in processed
        assert 'box-sizing: border-box;' in processed
    
    def test_image_path_replacement(self, processor):
        """Test that image paths are properly updated."""
        legacy_content = """
.bg {
    background-image: url('../images/bg.jpg');
}
"""
        
        processed = processor._process_legacy_content(legacy_content)
        
        assert "url('/wp-content/themes/DealerInspireDealerTheme/images/bg.jpg')" in processed
    
    def test_breakpoint_value_replacement(self, processor):
        """Test that non-standard breakpoints are updated."""
        legacy_content = """
@media (min-width: 920px) {
    .element {
        font-size: 1.2rem;
    }
}
"""
        
        processed = processor._process_legacy_content(legacy_content)
        
        assert '@media (min-width: 1024px)' in processed
        assert '920px' not in processed
    
    def test_complex_mixin_combination(self, processor):
        """Test processing of multiple mixins in one selector."""
        legacy_content = """
.complex {
    @include flexbox();
    @include flex-direction(column);
    @include align-items(center);
    @include border-radius(8px);
    @include transition(all 0.3s);
    @include absolute((top:10px, right:10px));
}
"""
        
        processed = processor._process_legacy_content(legacy_content)
        
        # Verify all mixins were replaced
        assert 'display: flex;' in processed
        assert 'flex-direction: column;' in processed
        assert 'align-items: center;' in processed
        assert 'border-radius: 8px;' in processed
        assert 'transition: all 0.3s;' in processed
        assert 'position: absolute; top: 10px; right: 10px;' in processed
        
        # Verify no mixins remain
        assert '@include' not in processed


class TestMixinReplacementEdgeCases:
    """Test edge cases in mixin replacement."""
    
    @pytest.fixture
    def processor(self):
        """Create SCSS processor for testing."""
        config = Config()
        return SCSSProcessor(config)
    
    def test_nested_mixin_replacement(self, processor):
        """Test mixin replacement in nested selectors."""
        legacy_content = """
.parent {
    @include flexbox();
    
    .child {
        @include align-items(center);
        
        &:hover {
            @include transition(all 0.2s);
        }
    }
}
"""
        
        processed = processor._process_legacy_content(legacy_content)
        
        assert 'display: flex;' in processed
        assert 'align-items: center;' in processed
        assert 'transition: all 0.2s;' in processed
    
    def test_mixin_with_variables(self, processor):
        """Test mixin replacement when variables are used."""
        legacy_content = """
.element {
    @include border-radius($border-radius);
    @include transition(all $transition-duration);
}
"""
        
        processed = processor._process_legacy_content(legacy_content)
        
        # Should preserve variable usage
        assert 'border-radius: $border-radius;' in processed
        assert 'transition: all $transition-duration;' in processed
    
    def test_commented_mixins_ignored(self, processor):
        """Test that commented mixins are not replaced."""
        legacy_content = """
.element {
    // @include flexbox();
    /* @include align-items(center); */
    @include border-radius(4px);
}
"""
        
        processed = processor._process_legacy_content(legacy_content)
        
        # Only uncommented mixin should be replaced
        assert 'border-radius: 4px;' in processed
        assert '// @include flexbox();' in processed
        assert '/* @include align-items(center); */' in processed 
