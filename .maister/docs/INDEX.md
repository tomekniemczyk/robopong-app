# Documentation Index

**IMPORTANT**: Read this file at the beginning of any development task to understand available documentation and standards.

## Quick Reference

### Project Documentation
Project-level documentation covering vision, goals, architecture, and technology choices for AcePad (Donic Robopong 3050XL controller).

### Technical Standards
Coding standards, conventions, and best practices organized by domain (global, frontend, backend, testing, workflow, protocol).

---

## Project Documentation

Located in `.maister/docs/project/`

#### Vision (`project/vision.md`)
AcePad project purpose, current state (~18 weeks, 243 commits, production-deployed), feature overview (BLE+USB robot control, structured training system, multi-user sessions, player profiles, video recording, PWA), 6-12 month goals, evolution from reverse engineering to training platform.

#### Roadmap (`project/roadmap.md`)
Development priorities: connectivity stability, training UX polish, bug fixes (high); drill library expansion, player statistics, recording improvements (medium); frontend modularization, API docs, linting setup (tech debt). Future considerations: multi-robot support, cloud sync, AI-assisted training. Effort scale: S/M/L.

#### Tech Stack (`project/tech-stack.md`)
Full technology inventory: Python 3.11 (FastAPI, Bleak, pyserial), JavaScript ES6+ (Vue 3 CDN, no build step), SQLite + file-based JSON storage, pytest (196 tests), Raspberry Pi deployment, GitHub Actions CI, motion camera + ffmpeg recording, key dependency versions.

#### Architecture (`project/architecture.md`)
Layered monolithic architecture: transport layer (BLE/USB/Simulation ABC), robot orchestration (connection lifecycle, handshake, health monitor), API layer (40+ REST endpoints, WebSocket, session management), training engine (state machine), storage layer (SQLite 11 tables + JSON hybrid), recording system (ffmpeg). Data flow diagrams, external integrations, deployment architecture.

---

## Technical Standards

### Global Standards

Located in `.maister/docs/standards/global/`

These standards apply across the entire codebase, regardless of frontend/backend context.

#### Error Handling (`standards/global/error-handling.md`)
Clear user messages, fail-fast validation, typed exceptions, centralized handling at boundaries, graceful degradation, retry with backoff, resource cleanup in finally blocks. Minimal pattern: bare `except Exception: pass` for non-critical ops, `raise HTTPException(status_code)` for API errors.

#### Validation (`standards/global/validation.md`)
Server-side always, client-side for feedback, validate early, specific field-level errors, allowlists over blocklists, type/format checks, input sanitization, business rule validation, consistent enforcement across entry points.

#### Conventions (`standards/global/conventions.md`)
Predictable file/directory structure, conventional commits (feat:/fix:/refactor: prefix, 96.3% adherence), Unicode box-drawing section headers in all code files, flat module architecture (no nested packages), dot-prefix for user data files, minimal dependencies, build what's needed.

#### Coding Style (`standards/global/coding-style.md`)
Naming consistency, automatic formatting, descriptive names, focused single-responsibility functions, uniform indentation, no dead code, no backward compatibility shims, DRY principle, verbose logging by default, no feature flags.

#### Commenting (`standards/global/commenting.md`)
Let code speak through structure and naming, comment sparingly for non-obvious logic only, no change/changelog comments in code.

#### Minimal Implementation (`standards/global/minimal-implementation.md`)
Build only what's needed, every method must have callers or serve readability, delete exploration artifacts, no future stubs, no speculative abstractions, review before commit, remove dead code promptly.

---

### Frontend Standards

Located in `.maister/docs/standards/frontend/`

These standards apply to frontend code (UI components, client-side logic, styling).

#### CSS (`standards/frontend/css.md`)
Consistent methodology (framework-first), design tokens via CSS custom properties (dark theme on :root), minimize custom CSS, production optimization with purging, mobile-first 680px max-width, safe-area insets, PWA standalone dark theme (#0f1117).

#### Components (`standards/frontend/components.md`)
Single-file Vue 3 CDN SPA (~5000 lines, no build step, no router), Composition API with setup(), v-show for tab navigation (preserves state), t() as global property (NOT from setup()), i18n always 5 languages (PL/EN/DE/FR/ZH), UI icon consistency (timer/recording/pause/stop/play conventions), 100+ reactive refs, key data readable from 3m (~28px+).

#### Accessibility (`standards/frontend/accessibility.md`)
Semantic HTML elements, keyboard navigation with visible focus, 4.5:1 color contrast, alt text and form labels, screen reader testing, ARIA when needed, proper heading structure, focus management in dynamic content.

#### Responsive Design (`standards/frontend/responsive.md`)
Mobile-first approach, standard breakpoints, fluid percentage-based layouts, relative units (rem/em), cross-device testing, touch-friendly 44x44px targets, mobile performance optimization, readable typography, content priority on small screens, hybrid WebSocket + REST communication.

---

### Backend Standards

Located in `.maister/docs/standards/backend/`

These standards apply to backend code (APIs, services, data layer).

#### API Design (`standards/backend/api.md`)
RESTful resource-based URLs under /api/ prefix, plural nouns with kebab-case multi-word resources, limited URL nesting (2-3 levels), query parameters for filtering/sorting/pagination, proper HTTP status codes (201 for POST create, 204 for DELETE, explicit status_code on decorators), HTTPException pattern (bare 404, message for 400/403/409).

#### Models (`standards/backend/models.md`)
Pydantic V2 BaseModel with Field constraints (ge=, le=, default=) for all API inputs, clear naming (singular models, plural tables), timestamps, database constraints (NOT NULL, UNIQUE, FK), indexed foreign keys, multi-layer validation, Transport Layer ABC (RobotTransport with BLE/USB/Simulation implementations).

#### Queries (`standards/backend/queries.md`)
Parameterized queries always, avoid N+1 with eager loading/joins, select only needed columns, index strategic columns, transactions for related ops, hybrid storage (SQLite 11 tables + file-based JSON + separate presets.db), session role management (CONTROLLER/OBSERVER/PENDING with force takeover).

#### Migrations (`standards/backend/migrations.md`)
Reversible with rollback methods, small and focused single-change migrations, zero-downtime awareness, separate schema and data migrations, careful indexing on large tables, descriptive names, version-controlled and immutable after deployment.

---

### Protocol Standards

Located in `.maister/docs/standards/protocol/`

These standards document the Donic Robopong 3050XL communication protocol, hardware constants, and connection sequences derived from reverse engineering and live testing.

#### Robot Constants (`standards/protocol/robot-constants.md`)
Head center position (150, not 128) for oscillation/rotation/height, parameter ranges (osc 127-173, height 75-210, rotation 90-210), motor speed PWM formula (`raw * 4.016`), LED spin indicator calculation (`|top-bot|/360`, values 0-8).

#### Communication (`standards/protocol/communication.md`)
Transport terminators (BLE `\r` vs USB `\r\n`), USB initialization (raw `0x5A` byte x2 at 9600 baud, not string), BLE 20-byte payload limit with split/200ms delay, firmware-dependent command selection (B vs A/wTA for FW >= 701).

#### Connection Sequences (`standards/protocol/connection-sequences.md`)
Connection handshake (Z x3, H, F, I, J02), health monitor ping every 10s, calibration throw sequence with timing (set_ball, 300ms, T, 1500ms, H), per-device calibration persistence (keyed by address in SQLite `calibration` table with addr='' fallback, must resend after every connect), default calibration values (top=160, bot=0, osc=150, h=183, rot=150, wait=1000).

---

### Testing Standards

Located in `.maister/docs/standards/testing/`

These standards apply to all testing code (unit, integration, E2E).

#### Test Writing (`standards/testing/test-writing.md`)
Test behavior not implementation, clear descriptive names, pytest with monkeypatch + tmp_path isolation, test file naming (test_{module}.py unit, test_api_{domain}.py integration), module docstrings only (no per-test docstrings), section headers matching API endpoints, direct assert statements (no assertEqual), test execution via venv, risk-based testing priority, critical path focus.

---

### Workflow Standards

Located in `.maister/docs/standards/workflow/`

These standards define version control workflow, task management, and collaboration practices.

#### Git Workflow (`standards/workflow/git-workflow.md`)
Trunk-based development (commit directly to main, no branches/PRs), mandatory git worktree isolation for every task, rebase before push with --force-with-lease, logical conflict resolution (never blindly ours/theirs), parallel session safety (diff before/after rebase, visual verification of shared files like index.html).

#### Task Management (`standards/workflow/task-management.md`)
GitHub Issues for all tasks (backlog label, priority labels wysoki/sredni/niski), project map maintenance in CLAUDE.md (update on file add/remove, line count changes >20%), mandatory documentation of protocol/UX/hardware findings in memory and CLAUDE.md (live tests override RE docs).

---

## How to Use This Documentation

1. **Start Here**: Always read this INDEX.md first to understand what documentation exists
2. **Project Context**: Read relevant project documentation before starting work
3. **Standards**: Reference appropriate standards when writing code
   - Global standards apply to all code
   - Domain-specific standards (frontend/backend/testing) apply to relevant code
   - Protocol standards apply to robot communication code
   - Workflow standards apply to git and task management
4. **Keep Updated**: Update documentation when making significant changes
5. **Customize**: Adapt all documentation to your project's specific needs

## Updating Documentation

- **Project docs**: When project goals, tech stack, or architecture changes
- **Standards**: When team conventions evolve or new patterns are adopted
- **INDEX.md**: When adding, removing, or significantly changing documentation

---

**Last Generated**: 2026-04-10 (regenerated with all 25 documentation files)
**Maintained by**: Documentation Manager skill
