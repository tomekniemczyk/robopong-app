## Development Conventions

### Predictable Structure
Organize files and directories in a logical, navigable layout.

### Up-to-Date Documentation
Keep README files current with setup steps, architecture overview, and contribution guidelines.

### Clean Version Control
Write clear commit messages, use feature branches, and add meaningful descriptions to pull requests.

### Environment Variables
Store configuration in environment variables; never commit secrets or API keys.

### Minimal Dependencies
Keep dependencies lean and up-to-date; document why major ones are included.

### Consistent Reviews
Follow a defined code review process with clear expectations for reviewers and authors.

### Testing Standards
Define required test coverage (unit, integration, etc.) before merging.

### Feature Flags
Use flags for incomplete features instead of long-lived branches.

### Changelog Updates
Maintain a changelog or release notes for significant changes.

### Build What's Needed
Avoid speculative code and "just in case" additions (see minimal-implementation.md).

### Conventional Commits
Commit messages use conventional commit format: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`, `test:`, `ci:`, `style:`, `perf:` prefix. 96.3% of 243 commits follow this convention.

### Unicode Box-Drawing Section Headers
All code files (Python, CSS, JavaScript) use Unicode box-drawing characters (U+2500) for section headers:
- Python: `# -- Section Name ------...`
- CSS: `/* -- Section Name ------... */`
- JS: `// -- Section Name ------...`

### Flat Module Architecture
Backend uses flat .py modules -- no nested packages, no `__init__.py` in backend/. Each module imported directly by name: `import db`, `from models import Ball`.

### Dot-Prefix for User Data Files
User-generated/mutable data files use dot-prefix: `.drills_user.json` (user overrides) vs `drills_default.json` (factory, tracked in git).
