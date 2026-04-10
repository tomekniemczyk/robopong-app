## Git Workflow

Standards for version control workflow in the AcePad project. Trunk-based development with worktree isolation and safe parallel collaboration.

### Trunk-Based Development

Commit directly to main -- no feature branches, no pull requests. Push to main with `--force-with-lease`.

### Mandatory Git Worktree

ALWAYS work in a git worktree (`git worktree add /tmp/robopong-work HEAD`). NEVER edit files directly in the main working directory. Create a new worktree from current main for each task; never reuse old worktrees.

### Rebase Before Push

ALWAYS rebase on main before pushing: `git pull --rebase origin main`. Push with `--force-with-lease` to protect against overwriting others' commits.

Full sequence:

```bash
# After completing work in worktree
git commit -m "description"
git checkout main
git pull --rebase origin main
# resolve any conflicts
git push --force-with-lease origin main
git worktree remove /tmp/robopong-work
```

### Logical Conflict Resolution

When resolving rebase conflicts, ALWAYS read both sides, understand the intent of each change, and merge preserving both functionalities. NEVER blindly choose "ours" or "theirs".

### Parallel Session Safety

The project is developed in parallel Claude sessions. Multiple sessions may modify the same files simultaneously (especially `frontend/index.html`).

Before rebase:
- Run `git diff HEAD origin/main` to see what other sessions changed.

After rebase:
- Run `git diff HEAD~N HEAD` and review the full diff.
- Verify your own changes are present and others' changes are not overwritten.
- Even without conflicts, visually verify files touched by both sides.
