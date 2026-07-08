"""Fase 2 (BUG-REC-01/16): submission_report exposes per-artifact counts.

Consumers of submission_report.json previously confused steps.jsonl.length
(assert-only) with test size. Now artifact_counts breaks it down.
"""
import json
from pathlib import Path

import pytest


@pytest.mark.unit
class TestSubmissionReportArtifactCounts:
    def test_report_exposes_raw_events_and_asserts_curated_separately(self, tmp_path):
        # Arrange — build minimal recording with distinct counts
        recordings_dir = tmp_path / "recordings"
        rec_id = "test_rec_counts"
        rec_dir = recordings_dir / rec_id
        rec_dir.mkdir(parents=True)

        # 5 raw events, 1 assert, 3 value_mutations
        (rec_dir / "raw_events.jsonl").write_text(
            "\n".join('{"event_id":"evt_%d","type":"click"}' % i for i in range(5)) + "\n"
        )
        (rec_dir / "steps.jsonl").write_text('{"step_id":"step_0001","action":"assert"}\n')
        (rec_dir / "value_mutations.jsonl").write_text(
            '{"value":"a"}\n{"value":"b"}\n{"value":"c"}\n'
        )
        (rec_dir / "recording_metadata.json").write_text(
            json.dumps({"system": "S", "suite": "T", "test_case": "TC"})
        )

        from testforge.publisher.git_publisher import GitPublisher

        pub = GitPublisher.__new__(GitPublisher)

        # Act
        report = pub._generate_submission_report(
            rec_id, json.loads((rec_dir / "recording_metadata.json").read_text()),
            str(recordings_dir),
        )

        # Assert
        counts = report["artifact_counts"]
        assert counts["raw_events"] == 5, (
            f"raw_events should count all events, got {counts['raw_events']}"
        )
        assert counts["asserts_curated"] == 1, (
            f"asserts_curated must reflect steps.jsonl entries (asserts only), "
            f"got {counts['asserts_curated']}"
        )
        assert counts["value_mutations"] == 3
        assert counts["field_snapshots"] == 0  # absent file → 0

    def test_report_missing_files_return_zero_not_error(self, tmp_path):
        # Arrange
        recordings_dir = tmp_path / "recordings"
        rec_id = "empty_rec"
        rec_dir = recordings_dir / rec_id
        rec_dir.mkdir(parents=True)
        (rec_dir / "recording_metadata.json").write_text("{}")

        from testforge.publisher.git_publisher import GitPublisher

        pub = GitPublisher.__new__(GitPublisher)

        # Act
        report = pub._generate_submission_report(rec_id, {}, str(recordings_dir))

        # Assert — no crash, zeros
        assert report["artifact_counts"] == {
            "raw_events": 0,
            "asserts_curated": 0,
            "value_mutations": 0,
            "field_snapshots": 0,
        }
