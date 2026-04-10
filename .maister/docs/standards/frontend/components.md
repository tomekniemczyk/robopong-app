## Components

### Single Responsibility
Each component should do one thing well.

### Reusability
Design components to work across different contexts with configurable props.

### Composability
Build complex UIs by combining smaller components rather than creating monoliths.

### Clear Interface
Define explicit, documented props with sensible defaults.

### Encapsulation
Keep implementation details private; expose only what's necessary.

### Consistent Naming
Use descriptive names that indicate purpose and follow team conventions.

### Local State
Keep state as close to where it's used as possible; lift only when needed.

### Minimal Props
If a component needs many props, consider composition or splitting it.

### Documentation
Document usage, props, and examples to help team adoption.

### Single-File Vue 3 CDN SPA
Entire frontend in `frontend/index.html` (~5000 lines). Vue 3 via CDN, no build step, no router. Composition API with setup(). 100+ reactive refs.

### v-show for Tab Navigation
Tab navigation uses `v-show` (preserves state) with `page` ref. Use `v-if` only for conditional elements where state preservation is not needed (modals, empty states).

### t() Global Property -- NOT from setup()
`t()` registered as `app.config.globalProperties.t`. Do NOT return from `setup()` -- Vue 3 prod compiler shadows it with v-for variables.

### i18n -- Always 5 Languages
Every UI text must be translated into PL/EN/DE/FR/ZH from the start. `t(key)` for UI (i18n.js), `tc(type, key)` for content (content_i18n.js).

### UI Icon Consistency
Timer: U+23F1. Recording: camera emoji + red REC pulse. Pause/Stop/Play: pause/stop/play symbols. Notes: speech balloon. Mic: microphone. Key data in overlays must be readable from 3m (~28px+).
