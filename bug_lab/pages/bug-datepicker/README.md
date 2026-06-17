# BUG: Datepicker — Time-Mismatch Validation Bug

## Symptom
Selecting today's date in the datepicker and clicking "Validate" shows error
"Date must not be in the past." — even though today should be accepted.

**Error message displayed on page:**
```
Date must not be in the past.
```

## Cause
JavaScript validation compares `new Date(inputValue)` (midnight UTC) against
`new Date()` (wall-clock time including hours:minutes:seconds:millis).

`new Date("2026-06-17T00:00:00")` = midnight.  
`new Date()` at 14:30 = 14:30:00.000.

`midnight < 14:30` → `true` → today's date rejected as "past".

Root cause chain:
1. `new Date()` includes current time component
2. `new Date("YYYY-MM-DD")` or `new Date(value + 'T00:00:00')` is midnight
3. Comparison `midnight < wallclock` always true (unless it's exactly midnight)
4. Today's date fails the "not in the past" check

**Rules:**
- Date must not be empty
- Date must not be in the past (today IS allowed)
- Date must be within next 90 days

## Reproduction
```bash
# 1. Reproduction test (shows today's date rejected)
pytest bug_lab/tests/test_bug_datepicker.py::test_today_date_rejected_bug -v

# 2. Future date works fine
pytest bug_lab/tests/test_bug_datepicker.py::test_future_date_accepted -v

# 3. Run all datepicker tests
pytest bug_lab/tests/test_bug_datepicker.py -v
```

**Manual reproduction:**
1. Load `bug_lab/pages/bug-datepicker/index.html`
2. Open browser DevTools console
3. Type today's date in the input (any time except exactly midnight)
4. Click "Validate" → **FAILS**: "Date must not be in the past."
5. Try a date 30 days from now → **SUCCEEDS** (no time-mismatch because it's definitively greater)

## Fix
Normalize both dates to midnight before comparison:

```javascript
// Before (BUGGY):
const selected = new Date(value + 'T00:00:00');
const now = new Date();
if (selected.getTime() < now.getTime()) { ... }  // today rejected!

// After (FIXED):
const selected = new Date(value + 'T00:00:00');
const today = new Date();
today.setHours(0, 0, 0, 0);
if (selected.getTime() < today.getTime()) { ... }  // today accepted
```

## Validation
```bash
# Bug lab tests (3 tests)
pytest bug_lab/tests/test_bug_datepicker.py -v

# Run all bug lab tests
pytest bug_lab/tests/ -v
```

## Test Coverage

| Test | What It Validates |
|------|-------------------|
| `test_today_date_rejected_bug` | Today's date incorrectly rejected as "past" |
| `test_future_date_accepted` | Date 30 days ahead passes validation |
| `test_empty_date_rejected` | Empty input shows "Please select a date." |
