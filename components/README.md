# Opus Formosa Web Components

Reusable web components for consistent UI across the website.

## Header Component (`opus-header`)

A responsive navigation header with language support and active page highlighting.

### Usage

```html
<!-- Basic usage -->
<opus-header language="zh" current-page="home"></opus-header>

<!-- English version -->
<opus-header language="en" current-page="events"></opus-header>
```

### Attributes

- `language`: `"zh"` (Chinese) or `"en"` (English) - defaults to `"zh"`
- `current-page`: `"home"`, `"events"`, `"team"`, `"donors"`, `"partners"`, `"friends"` - defaults to `"home"`

### Files Required

- `components/header.js` - The web component definition
- Include this script in your HTML: `<script src="components/header.js"></script>`

### Example Integration

```html
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <!-- ... head content ... -->
    <script src="components/header.js"></script>
</head>
<body>
    <opus-header language="zh" current-page="home"></opus-header>
    <!-- rest of page content -->
</body>
</html>
```

### Features

- ✅ Responsive design
- ✅ Language switching (Chinese/English)
- ✅ Active page highlighting
- ✅ Consistent styling
- ✅ Shadow DOM isolation
- ✅ Support dropdown (commented out by default)
- ✅ Logo and branding
- ✅ Hover effects and transitions

### Current Support Dropdown Status

The support dropdown is currently commented out in the component. To enable it:

1. Uncomment the dropdown HTML in `components/header.js`
2. Update the page links as needed for each language
3. The dropdown will automatically show on hover

### Browser Support

Works in all modern browsers that support Web Components and Shadow DOM.