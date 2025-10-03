# Typography System Guide

This guide documents the comprehensive typography system implemented for the Vue 3 + Vuetify 3 admin dashboard, using Inter and JetBrains Mono fonts.

## Overview

The typography system provides a consistent, accessible, and performant font hierarchy across the entire admin dashboard. It integrates seamlessly with Vuetify 3's theming system while providing custom utility classes for specialized use cases.

## Font Stack

### Primary Fonts
- **Inter**: Used for display/UI text (headings, body, interface elements)
- **JetBrains Mono**: Used for code/monospace text (query logs, technical data, code blocks)

### Fallback Stack
- **Inter fallback**: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif`
- **JetBrains Mono fallback**: `'SF Mono', Monaco, Inconsolata, 'Roboto Mono', 'Source Code Pro', Consolas, 'Courier New', monospace`

## Implementation Details

### 1. Font Loading (index.html)
```html
<!-- Font Preconnect for Performance -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>

<!-- Typography Fonts -->
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@300;400;500;600;700&display=swap" rel="stylesheet">
```

### 2. CSS Custom Properties (typography.css)
```css
:root {
  /* Font Families */
  --font-family-display: 'Inter', /* fallbacks */;
  --font-family-body: 'Inter', /* fallbacks */;
  --font-family-mono: 'JetBrains Mono', /* fallbacks */;

  /* Font Weights */
  --font-weight-light: 300;
  --font-weight-regular: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;
  --font-weight-bold: 700;
  --font-weight-extrabold: 800;

  /* Font Sizes (rem for accessibility) */
  --font-size-xs: 0.75rem;   /* 12px */
  --font-size-sm: 0.875rem;  /* 14px */
  --font-size-base: 1rem;    /* 16px */
  --font-size-lg: 1.125rem;  /* 18px */
  --font-size-xl: 1.25rem;   /* 20px */
  --font-size-2xl: 1.5rem;   /* 24px */
  --font-size-3xl: 1.875rem; /* 30px */
  --font-size-4xl: 2.25rem;  /* 36px */
  --font-size-5xl: 3rem;     /* 48px */
}
```

### 3. Vuetify Integration (vuetify.js)
```javascript
const typography = {
  fontFamily: 'Inter, /* fallbacks */',
  h1: {
    fontFamily: 'Inter, /* fallbacks */',
    fontSize: '1.875rem',
    fontWeight: 700,
    lineHeight: '1.25',
    letterSpacing: '-0.025em'
  },
  // ... additional typography configuration
}

export default createVuetify({
  typography,
  // ... other configuration
})
```

## Usage Examples

### Display Typography
```vue
<template>
  <div class="typography-display-1">Large Display Text</div>
  <div class="typography-display-2">Medium Display Text</div>
  <div class="typography-display-3">Small Display Text</div>
</template>
```

### Headings
```vue
<template>
  <h1 class="typography-h1">Main Heading</h1>
  <h2 class="typography-h2">Section Heading</h2>
  <h3 class="typography-h3">Subsection Heading</h3>
</template>
```

### Body Text
```vue
<template>
  <p class="typography-body-1">Regular body text with comfortable line height.</p>
  <p class="typography-body-2">Smaller body text for secondary content.</p>
  <span class="typography-caption">Caption text for labels and metadata.</span>
</template>
```

### Code & Technical Content
```vue
<template>
  <!-- Inline code -->
  <p>Use <code class="typography-code-inline">const variable = "value"</code> for constants.</p>
  
  <!-- Code blocks -->
  <pre class="typography-code-block">
function example() {
  return "Hello World";
}
  </pre>
  
  <!-- Technical text -->
  <span class="typography-technical">API endpoint: /api/v1/queries</span>
</template>
```

### Admin Dashboard Specific Classes
```vue
<template>
  <!-- Dashboard titles -->
  <h1 class="dashboard-title">Dashboard Overview</h1>
  <h2 class="dashboard-section-title">Recent Activity</h2>
  
  <!-- Metric displays -->
  <div class="metric-value">1,247</div>
  <div class="metric-label">Total Queries</div>
  
  <!-- Query content -->
  <div class="query-text">What is Nick's experience with Vue.js?</div>
  <div class="response-text">Based on the knowledge base...</div>
</template>
```

### Font Family Utilities
```vue
<template>
  <div class="font-display">Text using display font family (Inter)</div>
  <div class="font-body">Text using body font family (Inter)</div>
  <div class="font-mono">Text using monospace font family (JetBrains Mono)</div>
</template>
```

### Font Weight Utilities
```vue
<template>
  <span class="font-light">Light text</span>
  <span class="font-regular">Regular text</span>
  <span class="font-medium">Medium text</span>
  <span class="font-semibold">Semibold text</span>
  <span class="font-bold">Bold text</span>
  <span class="font-extrabold">Extra bold text</span>
</template>
```

### Letter Spacing Utilities
```vue
<template>
  <div class="tracking-tighter">Tighter letter spacing</div>
  <div class="tracking-normal">Normal letter spacing</div>
  <div class="tracking-wide">Wide letter spacing</div>
</template>
```

## Component Integration

### MetricCard Example
```vue
<template>
  <v-card>
    <v-card-text>
      <div class="metric-label">Total Queries</div>
      <div class="metric-value text-primary">1,247</div>
    </v-card-text>
  </v-card>
</template>
```

### QueryTable Example
```vue
<template>
  <div class="query-text bg-surface-variant pa-3 rounded">
    What is Nick's development philosophy?
  </div>
  <div class="response-text mt-2">
    Based on the knowledge base, Nick believes in...
  </div>
</template>
```

## Best Practices

### 1. Use Semantic Typography Classes
- Prefer semantic classes like `typography-h1` over utility classes
- Use utility classes for fine-tuning when needed

### 2. Maintain Consistency
- Use the predefined typography scale for font sizes
- Stick to the established font weight system
- Follow line height and letter spacing guidelines

### 3. Accessibility
- All font sizes use `rem` units for better accessibility
- Maintain sufficient contrast ratios
- Use proper semantic HTML elements with typography classes

### 4. Performance Considerations
- Fonts are loaded with `font-display: swap` for better performance
- Preconnect to Google Fonts for faster loading
- Font smoothing optimizations are applied

### 5. Responsive Typography
- Typography scales appropriately on mobile devices
- Use CSS custom properties for easy theme customization

## Theme Support

### Dark Theme
- Code blocks and inline code automatically adapt to dark theme
- Proper contrast ratios maintained across themes
- Text selection colors use theme-aware colors

### Customization
All typography can be customized through CSS custom properties:

```css
:root {
  --font-family-display: 'Your Custom Font', Inter, sans-serif;
  --font-size-base: 1.125rem; /* Larger base font size */
}
```

## Testing

### Typography Demo
Access the typography demonstration component in development:
```
/admin/typography-demo
```

This route showcases all typography classes and their proper usage.

### Integration Testing
The typography system has been integrated with:
- ✅ Vuetify components
- ✅ Admin dashboard views
- ✅ MetricCard component
- ✅ Query display components
- ✅ Monaco Editor integration

## File Structure

```
admin/frontend/
├── index.html                 # Font loading
├── src/
│   ├── styles/
│   │   ├── typography.css     # Typography system
│   │   └── main.css           # Global styles + typography integration
│   ├── plugins/
│   │   └── vuetify.js         # Vuetify typography configuration
│   ├── components/
│   │   └── TypographyDemo.vue # Demo component
│   └── main.js                # CSS imports
└── TYPOGRAPHY_GUIDE.md        # This guide
```

## Performance Metrics

- ✅ Fonts load with `display: swap` for better LCP
- ✅ Preconnect hints for faster DNS resolution  
- ✅ Font smoothing optimizations applied
- ✅ No CLS from font loading due to proper fallbacks
- ✅ Build size impact: Minimal, fonts loaded from CDN

## Browser Support

- ✅ Modern browsers (Chrome, Firefox, Safari, Edge)
- ✅ Graceful fallbacks for older browsers
- ✅ Font stack ensures compatibility across platforms
- ✅ CSS custom properties with fallbacks where needed

---

**Last Updated**: 2024-08-28  
**Version**: 1.0  
**Dependencies**: Vue 3.4+, Vuetify 3.6+, Inter & JetBrains Mono fonts