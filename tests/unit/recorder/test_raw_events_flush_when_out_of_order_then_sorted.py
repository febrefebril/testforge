"""RC-29: raw_events.jsonl sorted by timestamp after recording finalize."""
import json
import os
import pytest


@pytest.fixture
def store_dir(tmp_path):
    d = tmp_path / "rec"
    d.mkdir()
    return str(d)


@pytest.fixture
def store(store_dir):
    from testforge.recorder.raw_recording_store import RawRecordingStore
    return RawRecordingStore(store_dir)


@pytest.mark.unit
class TestRawEventsFlushWhenOutOfOrderThenSorted:

    def _write_events(self, store_dir, events):
        path = os.path.join(store_dir, "raw_events.jsonl")
        with open(path, "w") as f:
            for e in events:
                f.write(json.dumps(e) + "\n")

    def _read_events(self, store_dir):
        path = os.path.join(store_dir, "raw_events.jsonl")
        with open(path) as f:
            return [json.loads(l) for l in f if l.strip()]

    def test_out_of_order_events_sorted(self, store, store_dir):
        """RC-29: events written out-of-order → sorted by timestamp after sort_events_by_timestamp."""
        # Arrange — 3 events out of order
        self._write_events(store_dir, [
            {"type": "click", "timestamp": "2026-07-07T10:00:02Z"},
            {"type": "fill",  "timestamp": "2026-07-07T10:00:01Z"},
            {"type": "nav",   "timestamp": "2026-07-07T10:00:03Z"},
        ])

        # Act
        store.sort_events_by_timestamp()

        # Assert
        events = self._read_events(store_dir)
        timestamps = [e["timestamp"] for e in events]
        assert timestamps == sorted(timestamps)

    def test_already_sorted_unchanged(self, store, store_dir):
        """RC-29: already sorted events remain unchanged."""
        ordered = [
            {"type": "fill", "timestamp": "2026-07-07T10:00:01Z"},
            {"type": "click", "timestamp": "2026-07-07T10:00:02Z"},
        ]
        self._write_events(store_dir, ordered)

        store.sort_events_by_timestamp()

        events = self._read_events(store_dir)
        assert [e["timestamp"] for e in events] == ["2026-07-07T10:00:01Z", "2026-07-07T10:00:02Z"]

    def test_no_file_no_error(self, store):
        """RC-29: missing raw_events.jsonl does not raise."""
        store.sort_events_by_timestamp()  # should not raise

    def test_events_preserved_after_sort(self, store, store_dir):
        """RC-29: sort does not lose or corrupt event data."""
        events_in = [
            {"type": "fill", "timestamp": "2026-07-07T10:00:02Z", "value": "B"},
            {"type": "click", "timestamp": "2026-07-07T10:00:01Z", "value": "A"},
        ]
        self._write_events(store_dir, events_in)

        store.sort_events_by_timestamp()

        events_out = self._read_events(store_dir)
        assert events_out[0]["value"] == "A"
        assert events_out[1]["value"] == "B"
