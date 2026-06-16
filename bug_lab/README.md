# Bug Lab

Sandbox for reproducing, debugging, and fixing TestForge bugs.

## Structure

```
bug_lab/
├── pages/       # HTML pages to reproduce bugs
├── tests/       # Pytest files that trigger the bug
├── fixtures/    # Test data (recordings, JSON, configs)
└── README.md    # This file
```

## Workflow: Report → Reproduce → Fix → Verify

### 1. Create bug directory
```bash
mkdir -p bug_lab/tests/bugs/BUG-XXX
```

### 2. Add reproduction artifacts
- `pages/` — minimal HTML page that triggers the bug
- `tests/` — pytest file that exercises the failing path
- `fixtures/` — recordings, test data, or config that caused the bug

### 3. Fix the code in `src/testforge/`

### 4. Verify fix
```bash
pytest bug_lab/tests/bugs/BUG-XXX/ -v
```

### 5. Promote to permanent test
Move the test to `tests/` and the fixture to `tests/test_pages/`.

## Bug Template

```markdown
# BUG-XXX: Short Description

## Symptoms
What failed? Error message, stack trace, unexpected behavior.

## Reproduction Steps
1. Load page: `bug_lab/pages/BUG-XXX/index.html`
2. Run: `pytest bug_lab/tests/bugs/BUG-XXX/test_bug.py`
3. Observe: ...

## Expected Behavior
What should happen instead.

## Root Cause
Which file/function is broken and why.

## Fix
Commit hash and summary of the fix.

## Verification
```bash
pytest bug_lab/tests/bugs/BUG-XXX/ tests/ -v -k "relevant_test"
```
```

## Related Directories

| Directory | Purpose | Git |
|-----------|---------|-----|
| `bug_lab/` | Bug reproduction sandbox | Tracked |
| `recordings/` | Raw Playwright recordings (runtime artifacts) | Ignored |
| `semantic_tests/` | Compiled semantic test runs (runtime artifacts) | Ignored |
| `tests/` | Permanent test suite | Tracked |
| `synthetic_lab/` | Fake apps for testing | Tracked |
