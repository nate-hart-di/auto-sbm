#!/usr/bin/env python3
"""
Comprehensive torture test for SCSS variable conversion logic.
Tests complex SCSS features to ensure intelligent conversion works correctly.
"""

import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sbm.scss.processor import SCSSProcessor

class TestSCSSConversionTorture(unittest.TestCase):
    
    def setUp(self):
        self.processor = SCSSProcessor('test')
    
    def test_mixin_parameters_preserved(self):
        """Test that mixin parameters are not converted to CSS variables"""
        input_scss = """
@mixin button($bg-color, $text-color, $padding: 10px) {
  background-color: $bg-color;
  color: $text-color;
  padding: $padding;
  @if $text-color == white {
    border: 1px solid $bg-color;
  }
}
"""
        result = self.processor._convert_scss_variables_intelligently(input_scss)
        
        # Mixin parameters should NOT be converted
        self.assertIn('$bg-color', result)
        self.assertIn('$text-color', result)
        self.assertIn('$padding', result)
        
        # CSS properties should be converted
        self.assertIn('background-color: var(--bg-color)', result)
        self.assertIn('color: var(--text-color)', result)
        self.assertIn('padding: var(--padding)', result)
    
    def test_scss_maps_preserved(self):
        """Test that SCSS maps are completely preserved"""
        input_scss = """
$breakpoints: (
  small: 480px,
  medium: 768px,
  large: 1024px,
  xlarge: 1200px
);

$font-weights: (
  light: 300,
  regular: 400,
  bold: 700,
  black: 900
);
"""
        result = self.processor._convert_scss_variables_intelligently(input_scss)
        
        # Map definitions should be preserved
        self.assertIn('$breakpoints: (', result)
        self.assertIn('$font-weights: (', result)
        self.assertIn('small: 480px', result)
        self.assertIn('regular: 400', result)
        
        # Should NOT be converted to CSS variables
        self.assertNotIn('var(--breakpoints)', result)
        self.assertNotIn('var(--font-weights)', result)
    
    def test_control_flow_preserved(self):
        """Test that @each, @for, @if statements are preserved"""
        input_scss = """
$colors: (primary, secondary, accent);

@each $color in $colors {
  .bg-#{$color} {
    background-color: $color;
  }
}

@for $i from 1 through 5 {
  .col-#{$i} {
    width: percentage($i / 5);
  }
}

@if $theme == dark {
  body {
    background: $dark-bg;
  }
} @else {
  body {
    background: $light-bg;
  }
}
"""
        result = self.processor._convert_scss_variables_intelligently(input_scss)
        
        # Control flow should be preserved
        self.assertIn('@each $color in $colors', result)
        self.assertIn('@for $i from 1 through 5', result)
        self.assertIn('@if $theme == dark', result)
        
        # CSS properties should be converted
        self.assertIn('background-color: var(--color)', result)
        self.assertIn('background: var(--dark-bg)', result)
        self.assertIn('background: var(--light-bg)', result)
    
    def test_scss_functions_preserved(self):
        """Test that SCSS function calls are preserved"""
        input_scss = """
$colors: (primary: #3498db, secondary: #2ecc71);

.button {
  color: map-get($colors, primary);
  background: darken(map-get($colors, secondary), 10%);
  width: percentage(1/3);
  margin: unitless(16px);
}

$keys: map-keys($colors);
$values: map-values($colors);
"""
        result = self.processor._convert_scss_variables_intelligently(input_scss)
        
        # Function calls should be preserved
        self.assertIn('map-get($colors, primary)', result)
        self.assertIn('map-get($colors, secondary)', result)
        self.assertIn('map-keys($colors)', result)
        self.assertIn('map-values($colors)', result)
        
        # CSS properties should be converted where appropriate
        self.assertIn('color: var(--colors)', result)
        self.assertIn('background: var(--colors)', result)
    
    def test_complex_nested_structures(self):
        """Test complex nested SCSS structures"""
        input_scss = """
@mixin media-query($breakpoint) {
  @if map-has-key($breakpoints, $breakpoint) {
    @media (min-width: map-get($breakpoints, $breakpoint)) {
      @content;
    }
  }
}

$grid-columns: 12;
$grid-gutter: 20px;

@for $i from 1 through $grid-columns {
  .col-#{$i} {
    width: percentage($i / $grid-columns);
    padding: $grid-gutter / 2;
    
    @include media-query(tablet) {
      padding: $grid-gutter;
    }
  }
}
"""
        result = self.processor._convert_scss_variables_intelligently(input_scss)
        
        # Mixin parameters preserved
        self.assertIn('$breakpoint', result)
        
        # Function calls preserved
        self.assertIn('map-has-key($breakpoints, $breakpoint)', result)
        self.assertIn('map-get($breakpoints, $breakpoint)', result)
        
        # Loop variables preserved
        self.assertIn('@for $i from 1 through $grid-columns', result)
        self.assertIn('percentage($i / $grid-columns)', result)
        
        # CSS properties converted
        self.assertIn('width: var(--i)', result)
        self.assertIn('padding: var(--grid-gutter)', result)
    
    def test_placeholder_selectors(self):
        """Test that placeholder selectors with interpolation work"""
        input_scss = """
$button-types: (primary, secondary, danger);

@each $type in $button-types {
  %button-#{$type} {
    background-color: $type;
    color: $text-color;
    @include transition(all 0.3s ease);
  }
}

.btn-primary {
  @extend %button-primary;
  border-color: $primary-border;
}
"""
        result = self.processor._convert_scss_variables_intelligently(input_scss)
        
        # Loop and interpolation preserved
        self.assertIn('@each $type in $button-types', result)
        self.assertIn('%button-#{$type}', result)
        
        # CSS properties converted
        self.assertIn('background-color: var(--type)', result)
        self.assertIn('color: var(--text-color)', result)
        self.assertIn('border-color: var(--primary-border)', result)
    
    def test_variable_assignments_preserved(self):
        """Test that variable assignments are preserved"""
        input_scss = """
$primary: #3498db;
$secondary: lighten($primary, 20%);
$tertiary: darken($primary, 15%);
$font-size: 16px;
$line-height: $font-size * 1.5;

.text {
  font-size: $font-size;
  line-height: $line-height;
  color: $primary;
}
"""
        result = self.processor._convert_scss_variables_intelligently(input_scss)
        
        # Variable assignments preserved
        self.assertIn('$primary: #3498db', result)
        self.assertIn('$secondary: lighten($primary, 20%)', result)
        self.assertIn('$line-height: $font-size * 1.5', result)
        
        # CSS properties converted
        self.assertIn('font-size: var(--font-size)', result)
        self.assertIn('line-height: var(--line-height)', result)
        self.assertIn('color: var(--primary)', result)
    
    def test_edge_cases_and_gotchas(self):
        """Test edge cases that might trip up the conversion"""
        input_scss = """
// Edge case: colon in string values
.content::before {
  content: "Value: $placeholder";
}

// Edge case: variables in calc()
.element {
  width: calc(100% - $sidebar-width);
  height: calc($base-height * 2);
}

// Edge case: variables in URL
.background {
  background-image: url($image-path + "/bg.jpg");
}

// Edge case: nested interpolation
@each $size in $sizes {
  .icon-#{$size} {
    background-image: url("#{$icon-path}/#{$size}.svg");
  }
}
"""
        result = self.processor._convert_scss_variables_intelligently(input_scss)
        
        # String content should be converted
        self.assertIn('content: "Value: var(--placeholder)"', result)
        
        # Calc expressions should be converted
        self.assertIn('width: calc(100% - var(--sidebar-width))', result)
        self.assertIn('height: calc(var(--base-height) * 2)', result)
        
        # URL expressions should be converted
        self.assertIn('background-image: url(var(--image-path) + "/bg.jpg")', result)
        
        # Loop variables preserved but interpolation converted
        self.assertIn('@each $size in $sizes', result)
        self.assertIn('background-image: url("#{var(--icon-path)}/#{var(--size)}.svg")', result)
    
    def test_full_complex_example(self):
        """Test the original complex example from the issue"""
        input_scss = """
@mixin declareFonts($family, $weight) {
  font-family: $family;
  @if $weight != null {
    font-weight: $weight;
  }
}

$font-types: (
  regular: (
    family: $maintextfont,
    weight: 400,
  ),
  light: (
    family: $maintextfont,
    weight: 300,
  ),
  bold: (
    family: $maintextfont,
    weight: 700,
  ),
  condensed: (
    family: $heading-font,
    weight: 300,
  ),
);

$types: map_keys($font-types);
@each $type in $types {
  %#{$type} {
    @include declareFonts((map-get($font-types, $type))...);
  }
}

@mixin transform($value) {
  transform: $value;
  -webkit-transform: $value;
  -moz-transform: $value;
  -o-transform: $value;
  -ms-transform: $value;
}

@mixin ease($property: all, $duration: 0.35s) {
  -webkit-transition: $property $duration ease-in-out;
  -moz-transition: $property $duration ease-in-out;
  -o-transition: $property $duration ease-in-out;
  transition: $property $duration ease-in-out;
}

@mixin bgSize($size: cover, $xAxis: 50%, $yAxis: 50%) {
  -webkit-background-size: $size;
  -moz-background-size: $size;
  background-size: $size;
  background-position: $xAxis $yAxis;
  background-repeat: no-repeat;
}

.button {
  color: $primary;
  background: $secondary;
  @include transform(translateX(10px));
  @include ease(color, 0.2s);
}
"""
        result = self.processor._convert_scss_variables_intelligently(input_scss)
        
        # All mixin parameters should be preserved
        self.assertIn('$family', result)
        self.assertIn('$weight', result)
        self.assertIn('$value', result)
        self.assertIn('$property', result)
        self.assertIn('$duration', result)
        self.assertIn('$size', result)
        self.assertIn('$xAxis', result)
        self.assertIn('$yAxis', result)
        
        # Map and variable definitions preserved
        self.assertIn('$font-types: (', result)
        self.assertIn('$types: map_keys($font-types)', result)
        
        # Control flow preserved
        self.assertIn('@each $type in $types', result)
        self.assertIn('@if $weight != null', result)
        
        # Function calls preserved
        self.assertIn('map-get($font-types, $type)', result)
        
        # CSS properties converted
        self.assertIn('color: var(--primary)', result)
        self.assertIn('background: var(--secondary)', result)
        self.assertIn('font-family: var(--family)', result)
        self.assertIn('font-weight: var(--weight)', result)
        
        # Mixin body properties converted
        self.assertIn('transform: var(--value)', result)
        self.assertIn('transition: var(--property) var(--duration)', result)
        self.assertIn('background-size: var(--size)', result)
        self.assertIn('background-position: var(--xAxis) var(--yAxis)', result)

if __name__ == '__main__':
    # Run all tests
    unittest.main(verbosity=2)