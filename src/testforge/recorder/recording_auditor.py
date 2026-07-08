"""TestForge — Recording Auditor.

Generates quality reports for recordings. Analyzes raw events, captures
compilation outcomes, and surfaces potential issues (event flood,
missing submissions, dedup ratios, etc.).
"""
import json
import logging
import os
import time
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class RecordingAuditor:
    """Analyzes a recording directory and produces an audit report."""

    REPORT_FILENAME = "audit_report.json"

    def audit(self, recording_dir: str) -> dict:
        """Generate audit report for a recording directory.

        Reads raw_events.jsonl, steps.jsonl, network_log.json,
        evidence artifacts, and compilation output. Returns dict
        with quality metrics and issue flags.
        """
        start = time.time()
        recording_id = os.path.basename(recording_dir)
        report = {
            "recording_id": recording_id,
            "recording_dir": recording_dir,
            "audit_timestamp": datetime.utcnow().isoformat() + "Z",
            "duration_ms": 0,
            "events": {
                "total": 0,
                "by_type": {},
                "first_timestamp": None,
                "last_timestamp": None,
                "time_span_seconds": 0,
                "events_per_second": 0.0,
            },
            "steps": {
                "total": 0,
                "assert_types": {},
            },
            "evidence": {
                "screenshots": 0,
                "dom_snapshots": 0,
                "ax_snapshots": 0,
                "field_snapshots": 0,
                "value_mutations": 0,
            },
            "network": {
                "total_requests": 0,
                "api_requests": 0,
                "errors_4xx": 0,
                "errors_5xx": 0,
                "postbacks_detected": 0,
            },
            "compilation": {
                "last_compile_time": None,
                "last_status": None,
                "compiled_scripts": [],
            },
            "capture_runs": {
                "total": 0,
                "with_compilation": 0,
            },
            "issues": [],
            "quality_score": 0.0,
        }

        # --- Events analysis ---
        events_path = os.path.join(recording_dir, "raw_events.jsonl")
        if os.path.exists(events_path):
            timestamps = []
            type_counts = {}
            fill_count = 0
            with open(events_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        evt = json.loads(line)
                        et = evt.get("type", "unknown")
                        type_counts[et] = type_counts.get(et, 0) + 1
                        if et == "fill":
                            fill_count += 1
                        ts = evt.get("timestamp", "")
                        if ts:
                            timestamps.append(ts)
                    except json.JSONDecodeError:
                        continue

            report["events"]["total"] = sum(type_counts.values())
            report["events"]["by_type"] = type_counts

            if timestamps:
                report["events"]["first_timestamp"] = timestamps[0]
                report["events"]["last_timestamp"] = timestamps[-1]
                try:
                    t0 = datetime.fromisoformat(timestamps[0].replace("Z", "+00:00"))
                    t1 = datetime.fromisoformat(timestamps[-1].replace("Z", "+00:00"))
                    span = (t1 - t0).total_seconds()
                    report["events"]["time_span_seconds"] = round(span, 1)
                    if span > 0 and report["events"]["total"] > 0:
                        eps = report["events"]["total"] / span
                        report["events"]["events_per_second"] = round(eps, 2)
                except (ValueError, TypeError):
                    pass

            # Issue: excessive fill events (likely polling duplication)
            total = report["events"]["total"]
            eps = report["events"]["events_per_second"]
            if total > 100 and fill_count > total * 0.5:
                dedup_ratio = round(1 - (total / max(total * 1.5, 1)), 2)
                report["issues"].append({
                    "severity": "high",
                    "code": "EXCESSIVE_FILL_EVENTS",
                    "detail": f"{fill_count} fill events out of {total} total ({total}s in {report['events']['time_span_seconds']}s, {eps}/s). May indicate polling duplication.",
                    "suggestion": "Check __tfLastFillValue dedup in overlay. Angular currency mask can suppress native input events.",
                })
            if eps > 5:
                report["issues"].append({
                    "severity": "medium",
                    "code": "HIGH_EVENT_FREQUENCY",
                    "detail": f"{eps} events/second. May overload normalizer.",
                    "suggestion": "Reduce polling interval or improve dedup.",
                })

            # Issue: missing submit event for forms
            if type_counts.get("click", 0) > 3 and "submit" not in type_counts:
                report["issues"].append({
                    "severity": "warning",
                    "code": "MISSING_SUBMIT_EVENT",
                    "detail": f"{type_counts.get('click', 0)} clicks but no submit events. Form submission may not be detected.",
                    "suggestion": "Check __doPostBack detection for legacy ASP.NET or Angular form submit.",
                })

        # --- Steps (asserts) analysis ---
        steps_path = os.path.join(recording_dir, "steps.jsonl")
        if os.path.exists(steps_path):
            steps_count = 0
            assert_types = {}
            with open(steps_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        step = json.loads(line)
                        steps_count += 1
                        at = step.get("assert_type", "unknown")
                        assert_types[at] = assert_types.get(at, 0) + 1
                    except json.JSONDecodeError:
                        continue
            report["steps"]["total"] = steps_count
            report["steps"]["assert_types"] = assert_types

            if steps_count == 0:
                report["issues"].append({
                    "severity": "warning",
                    "code": "NO_ASSERTS",
                    "detail": "No assert steps found (Shift+A not used during recording).",
                    "suggestion": "Use Shift+A to add assertions for validation.",
                })

        # --- Evidence ---
        screenshots_dir = os.path.join(recording_dir, "screenshots")
        if os.path.isdir(screenshots_dir):
            files = [f for f in os.listdir(screenshots_dir) if f.endswith((".png", ".jpg", ".jpeg"))]
            report["evidence"]["screenshots"] = len(files)

        dom_dir = os.path.join(recording_dir, "dom_snapshots")
        if os.path.isdir(dom_dir):
            files = [f for f in os.listdir(dom_dir) if f.endswith(".html")]
            report["evidence"]["dom_snapshots"] = len(files)

        ax_dir = os.path.join(recording_dir, "ax_snapshots")
        if os.path.isdir(ax_dir):
            files = [f for f in os.listdir(ax_dir) if f.endswith(".json")]
            report["evidence"]["ax_snapshots"] = len(files)

        fsnap_path = os.path.join(recording_dir, "field_snapshots.jsonl")
        if os.path.exists(fsnap_path):
            try:
                with open(fsnap_path) as f:
                    report["evidence"]["field_snapshots"] = sum(1 for _ in f if _.strip())
            except Exception:
                pass

        vmut_path = os.path.join(recording_dir, "value_mutations.jsonl")
        if os.path.exists(vmut_path):
            try:
                with open(vmut_path) as f:
                    report["evidence"]["value_mutations"] = sum(1 for _ in f if _.strip())
            except Exception:
                pass

        # --- Network ---
        network_path = os.path.join(recording_dir, "network_log.json")
        if os.path.exists(network_path):
            try:
                with open(network_path) as f:
                    net = json.load(f)
                entries = net if isinstance(net, list) else net.get("entries", [])
                report["network"]["total_requests"] = len(entries)
                api_count = 0
                errors_4xx = 0
                errors_5xx = 0
                postbacks = 0
                for entry in entries:
                    url = entry.get("url", "") if isinstance(entry, dict) else ""
                    status = entry.get("status", 0) if isinstance(entry, dict) else 0
                    if isinstance(entry, dict):
                        if status >= 400 and status < 500:
                            errors_4xx += 1
                        elif status >= 500:
                            errors_5xx += 1
                        if "__dopostback" in url.lower() or "webform" in url.lower():
                            postbacks += 1
                        # Hotfix 12: SPA pseudo-submit (XHR/fetch POST tagged
                        # by RecorderController._mark_pseudo_submit).
                        elif entry.get("is_pseudo_submit"):
                            postbacks += 1
                        if any(ext in url for ext in [".json", "/api/", "/rest/", "/graphql"]):
                            api_count += 1
                report["network"]["api_requests"] = api_count
                report["network"]["errors_4xx"] = errors_4xx
                report["network"]["errors_5xx"] = errors_5xx
                report["network"]["postbacks_detected"] = postbacks
            except (json.JSONDecodeError, Exception) as exc:
                logger.warning("Failed to parse network_log.json: %s", exc)

        # --- Compilation ---
        meta_path = os.path.join(recording_dir, "recording_metadata.json")
        if os.path.exists(meta_path):
            try:
                with open(meta_path) as f:
                    meta = json.load(f)
                status_history = meta.get("status_history", [])
                compile_entries = [e for e in status_history if "compile" in e.get("reason", "")]
                if compile_entries:
                    last_compile = compile_entries[-1]
                    report["compilation"]["last_compile_time"] = last_compile.get("timestamp")
                    report["compilation"]["last_status"] = meta.get("recording_status") or meta.get("status")

                # Count captures runs
                capture_dir = os.path.join(recording_dir, "capture_runs")
                if os.path.isdir(capture_dir):
                    runs = sorted(os.listdir(capture_dir))
                    report["capture_runs"]["total"] = len(runs)
                    for run in runs:
                        run_dir = os.path.join(capture_dir, run)
                        if os.path.isdir(run_dir):
                            output_dir = os.path.join(run_dir, "output")
                            if os.path.isdir(output_dir):
                                py_files = [f for f in os.listdir(output_dir) if f.endswith(".py")]
                                if py_files:
                                    report["capture_runs"]["with_compilation"] += 1
                                    report["compilation"]["compiled_scripts"].extend(
                                        [os.path.join(run, "output", f) for f in py_files]
                                    )
            except Exception as exc:
                logger.warning("Failed to parse metadata for compilation status: %s", exc)

        # Check for compilation output in semantic_tests
        if not report["compilation"]["compiled_scripts"]:
            semantic_dir = os.path.join(recording_dir, "..", "..", "semantic_tests")
            if os.path.isdir(semantic_dir):
                st_dirs = [d for d in os.listdir(semantic_dir) if recording_id in d]
                for sd in st_dirs:
                    sd_path = os.path.join(semantic_dir, sd)
                    if os.path.isdir(sd_path):
                        py_files = [f for f in os.listdir(sd_path) if f.endswith(".py")]
                        report["compilation"]["compiled_scripts"].extend(
                            [os.path.join("semantic_tests", sd, f) for f in py_files]
                        )
            if not report["compilation"]["compiled_scripts"]:
                report["issues"].append({
                    "severity": "high",
                    "code": "NO_COMPILATION_OUTPUT",
                    "detail": "No compiled .py scripts found. Normalizer or compiler may have failed.",
                    "suggestion": "Run `testforge compile --check <id>` to debug. Check logs for normalizer errors.",
                })

        # --- Quality score ---
        score = 100.0
        for issue in report["issues"]:
            sev = issue.get("severity", "low")
            if sev == "high":
                score -= 25
            elif sev == "warning":
                score -= 10
            elif sev == "medium":
                score -= 15
        report["quality_score"] = max(0, score)

        report["duration_ms"] = round((time.time() - start) * 1000, 1)

        # Persist report
        report_path = os.path.join(recording_dir, self.REPORT_FILENAME)
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, default=str)
            logger.info("Audit report saved to %s (score=%.0f, duration=%sms)",
                         report_path, report["quality_score"], report["duration_ms"])
        except Exception as exc:
            logger.warning("Failed to save audit report: %s", exc)

        return report

    def print_report(self, report: dict) -> None:
        """Print a human-readable summary of the audit report."""
        rid = report.get("recording_id", "?")
        score = report.get("quality_score", 0)
        events = report.get("events", {})
        steps = report.get("steps", {})
        issues = report.get("issues", [])

        status = "OK" if score >= 80 else ("WARN" if score >= 50 else "FAIL")
        print(f"[TestForge] Audit {rid}: score={score:.0f}% status={status}")
        print(f"  Events: {events.get('total', 0)} total, {events.get('events_per_second', 0)}/s")
        print(f"  Types: {events.get('by_type', {})}")
        print(f"  Time span: {events.get('time_span_seconds', 0)}s")
        print(f"  Steps (asserts): {steps.get('total', 0)}")
        print(f"  Network requests: {report.get('network', {}).get('total_requests', 0)}")
        print(f"  Compilation: {report.get('compilation', {}).get('last_status', 'never')}")
        print(f"  Scripts: {report.get('compilation', {}).get('compiled_scripts', [])}")
        if issues:
            print(f"  Issues ({len(issues)}):")
            for iss in issues:
                print(f"    [{iss['severity'].upper()}] {iss['code']}: {iss['detail'][:120]}")
        print(f"  Audit duration: {report.get('duration_ms', 0)}ms")


def audit_recording(recording_dir: str) -> dict:
    """Convenience function to audit a recording."""
    auditor = RecordingAuditor()
    return auditor.audit(recording_dir)
