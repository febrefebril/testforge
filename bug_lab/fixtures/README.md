# Bug Lab — Fixtures

Test data that triggers or reproduces bugs.

## Convention

```
bug_lab/fixtures/BUG-XXX/
├── recording.jsonl        # Raw Playwright recording
├── test_data.json          # Input data used by the test
├── semantic_steps.jsonl    # Compiled semantic steps
└── expected_output.json    # What the correct output should be
```

## Fixture Types

| File | Purpose |
|------|---------|
| `recording.jsonl` | Raw events captured by `Recorder` that cause the bug |
| `test_data.json` | Input parameters or test data fed to the buggy function |
| `semantic_steps.jsonl` | Compiled semantic steps from `SemanticCompiler` |
| `expected_output.json` | Golden file — correct behavior after fix |
| `config.yaml` | TestForge config that exposes the bug |

## Template: test_data.json

```json
{
  "bug_id": "BUG-XXX",
  "description": "Short description",
  "input": {
    "url": "https://example.com",
    "steps": [
      {"action": "click", "selector": "#btn"},
      {"action": "type", "selector": "#input", "value": "test"}
    ]
  },
  "expected": {
    "result": "success"
  },
  "actual_buggy": {
    "error": "TimeoutError: waiting for selector '#btn'"
  }
}
```

## Rules

- Keep fixtures minimal — only data needed to reproduce the bug.
- Do NOT commit API keys, secrets, or real user data.
- Use `expected_output.json` as golden file for fix verification.
- Fixtures may reference recordings from `recordings/` directory if needed.
