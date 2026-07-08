"""TestForge — execution_report.json e healing_report.md."""
import json
from pathlib import Path
from testforge.runner.incremental_runner import IncrementalRunner
from testforge.runner.step_result import IncrementalStepResult, HealingAttempt


def test_execution_report_contains_summary(tmp_path):
    script = tmp_path / "t.py"
    script.write_text("")
    runner = IncrementalRunner(script_path=str(script), output_root=str(tmp_path / "runs"))
    runner.step_results = [
        IncrementalStepResult(step_num=1, action="click", status="passed"),
        IncrementalStepResult(step_num=2, action="click", status="healing_rejected",
                              healing=HealingAttempt(attempted=True, rejection_reason=["x"])),
    ]
    runner.recording_id = "REC-x"
    totals = runner._compute_totals()
    report = runner._finalize_report(totals)
    assert report["summary"]["passed"] == 1
    assert report["summary"]["healing_rejected"] == 1
    out_dir = Path(tmp_path / "runs" / "REC-x")
    files = list(out_dir.rglob("execution_report.json"))
    assert len(files) >= 1
    data = json.loads(files[0].read_text())
    assert data["summary"]["total"] == 2