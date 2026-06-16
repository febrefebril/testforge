# Bug Lab

Sandbox for reproducing, debugging, and fixing TestForge bugs.

## Cycle: reproduce → verify → fix → validate

Every bug follows this 4-step cycle:

| Phase | Action | Command / File |
|-------|--------|---------------|
| **reproduce** | Create minimal HTML page + test that triggers the bug | `bug_lab/pages/<bug>/index.html` + `bug_lab/tests/<bug>_test.py` |
| **verify** | Run the test, confirm the bug exists and understand the root cause | `pytest bug_lab/tests/<bug>_test.py -v` |
| **fix** | Apply the fix in `src/testforge/` | Commit with `fix: BUG-XXX — description` |
| **validate** | Re-run the bug lab test + full suite, confirm no regressions | `pytest bug_lab/ tests/ -v` |

After validation, promote the test to `tests/` for permanent coverage.

## Quick Start

```bash
# 1. Copy the template
cp -r bug_lab/pages/template bug_lab/pages/BUG-001
cp bug_lab/tests/template_test.py bug_lab/tests/BUG-001_test.py

# 2. Reproduce — edit the HTML and test to trigger the bug
# 3. Verify — run the test
pytest bug_lab/tests/BUG-001_test.py -v

# 4. Fix — edit src/testforge/ to resolve
# 5. Validate — re-run and confirm green
pytest bug_lab/tests/BUG-001_test.py tests/ -v
```

## Structure

```
bug_lab/
├── pages/                # HTML pages to reproduce bugs
│   └── template/         # Minimal counter template to copy
├── tests/                # Pytest files that trigger the bug
│   └── template_test.py  # Example test demonstrating the cycle
├── fixtures/             # Test data (recordings, JSON, configs)
├── conftest.py           # Shared fixtures (test_server, browser, page)
└── README.md             # This file
```

## Bug Template

```markdown
# BUG-XXX: Short Description

## Symptoms
What failed? Error message, stack trace, unexpected behavior.

## Reproduction
1. Page: `bug_lab/pages/BUG-XXX/index.html`
2. Test: `pytest bug_lab/tests/BUG-XXX_test.py -v`
3. Observe: ...

## Root Cause
Which file/function is broken and why.

## Fix
Commit hash and summary of the fix.

## Validation
```bash
pytest bug_lab/tests/BUG-XXX_test.py tests/ -v
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
| `src/testforge/` | Source code (fixes applied here) | Tracked |
