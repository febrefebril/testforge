# Recording fingerprints audit — 2026-06-27

Cross-references every existing recording against the capture-affecting
hotfix timeline. Inputs: file mtimes (proxy for `started_at`) plus
`git log --format="%H %ci %s" --since="2026-06-23" -- src/testforge/recorder/`.

This is a one-shot inferred audit. New recordings carry a real
fingerprint block (see `src/testforge/recorder/capture_fingerprint.py`)
so this style of inference is no longer required going forward.

## Capture-affecting commits (timeline)

The recorder writes were changed by these commits. Sorted ascending.
Recordings produced before each row miss the listed capability or
field shape.

| Date (UTC) | Commit | Change |
|---|---|---|
| 2026-06-24 17:46 | `62587bf` | Bug3: step counter increment restored |
| 2026-06-24 17:47 | `2796c80` | Bug9: fill dedup — DOM-indexed fallback key |
| 2026-06-24 17:48 | `d027eef` | Bug1: guard `page.title()` / `page.url` |
| 2026-06-24 18:17 | `1c49cae` | Bug8: expose `_OVERLAY_JS` as class attribute |
| 2026-06-24 19:06 | `359fedc` | perf: batch JS queue reads (no schema change) |
| 2026-06-24 19:12 | `b406295` | i18n + light-mode DOM capture skip |
| 2026-06-24 20:07 | `2b151d5` | bugs 11-16: SELECT recording + playback |
| 2026-06-25 17:14 | `2fe5f8f` | Sprint 0: RecorderController hook + diagnostic CLI |
| 2026-06-25 17:59 | `6bf85cb` | hotfix 1: heuristic candidates + detection cache |
| 2026-06-25 18:01 | `ce1966e` | hotfix 2: graceful stop + editor fallback chain |
| 2026-06-25 18:50 | `15bbde2` | hotfix 7: XHR/fetch POST → pseudo-submit |
| 2026-06-26 02:24 | `b90b4f9` | hotfix 10: browser close = graceful stop |
| 2026-06-26 02:57 | `552e05c` | hotfix 12: persist + audit SPA postbacks |
| 2026-06-26 15:47 | `2d057a9` | hotfix 14: Shift+S closes browser + clear UX |
| **2026-06-27 22:50** | **(this entry)** | **capture fingerprint v1 introduced** |

After hotfix 14, no commits in this session touched `overlay_inject.js`
or `_persist_raw_event`. H17 changed diagnostic timing only (replay-check
batched), H22a/H22b changed normalizer only.

## Recordings — inferred status

Buckets:

- 🟥 **incompatible** — predates a write-format-changing hotfix that
  the normalizer cannot recover from. Trust nothing.
- 🟧 **partial** — predates pseudo-submit (hotfix 7/12) or other
  metadata-adding changes. Action-level data OK; submit detection
  questionable.
- 🟨 **stable** — produced by recorder ≥ 2026-06-25 18:50 and ≤
  2026-06-26 15:47. Full capture, no fingerprint block.
- 🟩 **stable + fingerprintable** — produced ≥ fingerprint introduction
  (future recordings after the commit that lands this audit).

| Recording | Date | Bucket | Notes |
|---|---|---|---|
| `gravacao_para_bug` | 2026-06-24 17:12 | 🟥 | Pre-Bug3/Bug9. Step counter + fill dedup broken. |
| `REC-FULL-001`, `REC-ASSERT-001` | 2026-06-24 18:02-18:03 | 🟥 | Pre-SELECT fix (20:07). |
| `REC-*_2` | 2026-06-24 18:14 | 🟥 | Same window. |
| `REC-*_3` … `REC-*_11` | 2026-06-24 20:11-22:26 | 🟧 | Post-SELECT, pre-pseudo-submit. SELECT OK; SPA postbacks missing. |
| `grava_o_para_an_lise`, `grava_o_para_an_lise_2` | 2026-06-25 11:56-15:09 | 🟧 | Same window. |
| `grava_o_p_s_sprint0` | 2026-06-25 17:40-17:46 | 🟧 | Sprint 0 just shipped (17:14); pre-hotfix-7. |
| `test-pos-hotfix` | 2026-06-25 19:32 | 🟨 | Post-hotfix-7 (18:50). First stable bucket. |
| `REC-*_12`, `REC-*_13` | 2026-06-25 21:10-21:44 | 🟨 | Stable. |
| `test-pos-hotfix3..6` | 2026-06-26 16:56-18:49 | 🟨 | Post-hotfix-14 (15:47). Most stable. |
| `REC-*_14`, `test-pos-hotfix` (dup), `test-pos-hotfix7`, `test-pos-hotfix8` | 2026-06-27 19:48-20:01 | 🟨 | Today, pre-fingerprint commit. |

## Implications

1. **Spike 2 / EVIDENCE-ANALYSIS findings**: the 11 production recordings
   in `evidencias/recordings.zip` (analysed earlier this session) span
   the 2026-06-24 → 06-25 window. Roughly half sit in 🟥/🟧 — claims of
   "SELECT didn't capture" or "submit not recorded" against those
   recordings may reflect known recorder gaps, not present-day bugs.
   The `--complete` typing-not-captured findings still hold because that
   bug class lives in the **normalizer**, not in pre/post-hotfix-7
   recorder differences.

2. **H22c readiness**: `setter_hook_uncontested` (from H22b telemetry)
   should be measured **only** on 🟨 or 🟩 recordings. 🟥/🟧 recordings
   will report misleading numbers.

3. **Backfill policy**: **none**. We do not mutate existing
   recording_metadata.json files. The normalizer's
   `verify_fingerprint` already treats missing fingerprint as legacy
   v0 and logs a warning. This audit is the human-readable companion.

## Going forward

Every new recording carries a `fingerprint` block in
`recording_metadata.json`. The normalizer reads it, compares against
the recorder it is running with, and surfaces mismatches as warnings.

Bump policy for `CAPTURE_SCHEMA_VERSION`: only when the *write* format
of a recording artefact changes. Do **not** bump for:

- timing tweaks (e.g., H17 batched replay-check)
- retry / fallback changes
- normalizer-only fixes (e.g., hotfix 22, H22a, H22b)
- UI / overlay shortcut changes

Do bump for:

- new fields in `raw_events.jsonl` / `value_mutations.jsonl` /
  `field_snapshots.jsonl` / `final_state_snapshot.json` / `steps.jsonl`
- renames or shape changes of existing fields
- changes to the overlay JS that alter what fires `_persist_raw_event`
