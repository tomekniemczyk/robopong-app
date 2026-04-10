# Development Roadmap

## Current State
- **Version**: Production (no semantic versioning)
- **Key Features**: Robot control (BLE+USB), drills, exercises, trainings, player profiles, video recording, multi-user sessions, calibration, i18n (5 languages)
- **Recent Focus**: Training flow improvements, drill modes (sync/async), calibration UX, force takeover

## Planned Enhancements (Next 3-6 Months)

### High Priority
- [ ] **Connectivity Stability** — Improve BLE reconnection logic and health monitoring `Effort: M`
- [ ] **Training UX Polish** — Refine training flow based on real-world usage feedback `Effort: M`
- [ ] **Bug Fixes** — Address edge cases in drill execution and session management `Effort: S`

### Medium Priority
- [ ] **Drill Library Expansion** — Add more training drills based on coaching methodology `Effort: M`
- [ ] **Player Statistics** — Enhanced analytics and progress tracking `Effort: M`
- [ ] **Recording Improvements** — Better video quality, annotation, comparison tools `Effort: L`

### Technical Debt
- [ ] **Frontend Modularization** — Consider splitting 5300-line index.html into components `Effort: L`
- [ ] **API Documentation** — Add OpenAPI/Swagger auto-generation from FastAPI `Effort: S`
- [ ] **Linting Setup** — Add flake8/black for Python, ESLint for JavaScript `Effort: S`

## Future Considerations
- **Multi-robot Support**: Control multiple robots simultaneously
- **Cloud Sync**: Sync player profiles and training history across devices
- **AI-assisted Training**: Adaptive drill selection based on player performance

---
**Effort Scale**: `S`: 2-3 days | `M`: 1 week | `L`: 2+ weeks
