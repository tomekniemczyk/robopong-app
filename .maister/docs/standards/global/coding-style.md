## Coding Style

### Naming Consistency
Follow established naming patterns for variables, functions, classes, and files throughout the project.

### Automatic Formatting
Use automated tools to enforce consistent indentation, spacing, and line breaks.

### Descriptive Names
Choose names that clearly communicate intent; avoid cryptic abbreviations or single-letter identifiers outside tight loops.

### Focused Functions
Write functions that do one thing well; smaller functions are easier to read, test, and maintain.

### Uniform Indentation
Standardize on spaces or tabs and enforce with editor/linter settings.

### No Dead Code
Remove unused imports, commented-out blocks, and orphaned functions instead of leaving them behind.

### No Backward Compatibility Unless Required
Avoid extra code paths for backward compatibility unless explicitly needed.

### DRY (Don't Repeat Yourself)
Extract repeated logic into reusable functions or modules.

### Verbose Logging Default
VERBOSE logging enabled by default (toggle in main.py). Relevant operations should be logged via module-level logger.

### No Feature Flags or Backward Compat
No feature flags, backward-compatibility shims, or unnecessary error handling for impossible scenarios. Code should be clean and direct.
