## Test Writing

### Test Behavior
Focus on what code does, not how it does it, to allow safe refactoring.

### Clear Names
Use descriptive names explaining what's tested and expected (`shouldReturnErrorWhenUserNotFound`).

### Mock External Dependencies
Isolate tests by mocking databases, APIs, and external services.

### Fast Execution
Keep unit tests fast (milliseconds) so developers run them frequently.

### Risk-Based Testing
Prioritize testing based on business criticality and likelihood of bugs.

### Balance Coverage and Velocity
Adjust test coverage based on project needs and team workflow.

### Critical Path Focus
Ensure core user workflows and critical business logic are well-tested.

### Appropriate Depth
Match edge case testing to the risk profile of the code.

### Pytest with monkeypatch + tmp_path Isolation
All tests isolate storage via monkeypatch + tmp_path. Integration tests use `client` fixture with TestClient. Robot mocked with MagicMock.

### Test File and Function Naming
Files: `test_{module}.py` (unit), `test_api_{domain}.py` (integration), `test_{feature}_enhanced.py` (extended). Functions: `test_{verb}_{noun}` with descriptive suffixes (_empty, _404, _persists).

### Module Docstrings Only -- No Per-Test Docstrings
Every test file has a module-level docstring describing scope. Individual test functions rely on descriptive names, no docstrings.

### Section Headers Match API Endpoints
Integration tests use box-drawing section headers matching endpoints: `# -- GET /api/drills/tree ------...`

### Direct Assert Statements
Use plain `assert` with direct comparisons. No assertEqual/assertIn. Use `pytest.raises` for expected exceptions.

### Test Execution via venv
Run tests via virtual environment: `cd backend && venv/bin/pytest`. Test deps in `requirements-test.txt`.
