# Utility Classes Documentation

This document provides an overview of the utility classes available in the project.

## Typography
Various typography utility classes are available in `global.css` for font sizes, weights, styles, and alignment.

## Border Radius (Rounded Corners)

### Basic Rounding
- `.rounded-none` - No border radius (0)
- `.rounded-sm` - Small border radius (0.125rem)
- `.rounded` - Default border radius (0.25rem)
- `.rounded-md` - Medium border radius (0.375rem)
- `.rounded-lg` - Large border radius (0.5rem)
- `.rounded-xl` - Extra large border radius (0.75rem)
- `.rounded-2xl` - 2x extra large border radius (1rem)
- `.rounded-3xl` - 3x extra large border radius (1.5rem)
- `.rounded-full` - Full circular border radius (9999px)

### Individual Corner Rounding
- `.rounded-t` - Round top corners
- `.rounded-r` - Round right corners
- `.rounded-b` - Round bottom corners
- `.rounded-l` - Round left corners

## Shadows

### Basic Shadows
- `.shadow-none` - No shadow
- `.shadow-sm` - Small shadow
- `.shadow` - Default shadow
- `.shadow-md` - Medium shadow
- `.shadow-lg` - Large shadow
- `.shadow-xl` - Extra large shadow
- `.shadow-2xl` - 2x extra large shadow
- `.shadow-inner` - Inner shadow

### Colored Shadows
- `.shadow-primary` - Shadow with primary color (purple)
- `.shadow-dark` - Dark shadow
- `.shadow-light` - Light shadow

## Usage Examples

```html
<!-- Rounded corners and shadow on an image -->
<img src="example.jpg" class="rounded-lg shadow-md" alt="Example image">

<!-- Fully rounded button with shadow -->
<button class="rounded-full shadow">Click me</button>

<!-- Card with rounded top and shadow -->
<div class="rounded-t shadow-lg">
  <h2>Card Title</h2>
  <p>Card content</p>
</div>

<!-- Element with primary colored shadow -->
<div class="shadow-primary">
  Special content
</div>
```
