## CSS

### Consistent Methodology
Stick to the project's chosen approach (Tailwind, BEM, CSS modules, etc.) across the entire codebase.

### Work With the Framework
Use framework patterns as intended rather than fighting them with excessive overrides.

### Design Tokens
Establish and document consistent values for colors, spacing, and typography.

### Minimize Custom CSS
Prefer framework utilities to reduce custom styling maintenance.

### Production Optimization
Use CSS purging or tree-shaking to remove unused styles.

### Dark Theme via CSS Custom Properties
Dark theme with CSS custom properties on :root: --bg, --surface, --card, --border, --accent, --danger, --success, --warning, --text, --muted. No light theme.

### Mobile-First 680px Max-Width
Mobile-first design, max-width 680px, safe-area insets. PWA standalone mode with dark theme (#0f1117).
