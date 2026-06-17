# BUG: Datepicker — Operator Validation Bug

## Symptom
Selecting today's date in the datepicker and clicking "Validate" shows error
"Date must not be in the past." — even though today should be accepted.

**Error message displayed on page:**
```
Date must not be in the past.
```

## Cause
JavaScript validation uses `<=` (less-than-or-equal) instead of `<` (less-than)
when comparing selected date against today's midnight.

`selected.getTime() <= today.getTime()` with both at midnight → `true` → today's date rejected.

Root cause chain:
1. Both dates normalized to midnight (time-mismatch already fixed)
2. Comparison `midnight <= midnight` is true (operator bug)
3. Today's date fails the "not in the past" check

**Rules:**
- Date must not be empty
- Date must not be in the past (today IS allowed)
- Date must be within next 90 days

## Reproduction
```bash
# 1. Fix validation test (today's date accepted after fix)
pytest bug_lab/tests/test_bug_datepicker.py::test_today_date_accepted -v

# 2. Future date works fine
pytest bug_lab/tests/test_bug_datepicker.py::test_future_date_accepted -v

# 3. Run all datepicker tests
pytest bug_lab/tests/test_bug_datepicker.py -v
```

**Manual reproduction:**
1. Load `bug_lab/pages/bug-datepicker/index.html`
2. Open browser DevTools console
3. Type today's date in the input
4. Click "Validate" → **FAILS**: "Date must not be in the past." (with `<=` bug)
5. Fix: change `<=` to `<` → today's date accepted

## Fix
Change `<=` to `<` in the comparison operator:

```javascript
// Before (BUGGY):
if (selected.getTime() <= today.getTime()) { ... }  // today rejected!

// After (FIXED):
if (selected.getTime() < today.getTime()) { ... }  // today accepted
```

## Validation
```bash
# Bug lab tests (all 7 tests)
pytest bug_lab/tests/test_bug_datepicker.py -v

# Run all bug lab tests
pytest bug_lab/tests/ -v
```

## Test Coverage

| Test | What It Validates |
|------|-------------------|
| `test_today_date_accepted` | Today's date accepted after operator fix |
| `test_future_date_accepted` | Date 30 days ahead passes validation |
| `test_empty_date_rejected` | Empty input shows "Please select a date." |
| `test_past_date_rejected` | Past date correctly rejected |
| `test_beyond_90_days_rejected` | Date beyond 90 days rejected |
| `test_submit_enabled_after_validation` | Submit button enables after validation |
| `test_submit_shows_confirmation` | Submit shows confirmation with date |
