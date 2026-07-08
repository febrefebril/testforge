"""NB-05: auto-fire cluster detector marks clicks with regular intervals as noise."""
import pytest
from datetime import datetime, timezone, timedelta


@pytest.mark.unit
class TestAutoFireDetectorWhenRegularGapsThenMarkedNoise:
    def _make_click(self, i, seconds_offset, eid, css=""):
        base = datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc)
        ts = (base + timedelta(seconds=seconds_offset)).isoformat().replace("+00:00", "Z")
        return {"type": "click", "timestamp": ts, "target": {"element_id": eid, "css_path": css}}

    def test_5_clicks_8s_apart_marked_as_noise(self):
        from testforge.semantic.recording_normalizer import _detect_auto_fire_clusters
        events = [self._make_click(i, i*8, "next", "#next") for i in range(5)]
        noise = _detect_auto_fire_clusters(events)
        assert noise == {0, 1, 2, 3, 4}

    def test_3_clicks_1s_apart_not_marked(self):
        from testforge.semantic.recording_normalizer import _detect_auto_fire_clusters
        events = [self._make_click(i, i*1, "btn", "#btn") for i in range(3)]
        noise = _detect_auto_fire_clusters(events)
        assert not noise, "Human clicks should not be marked noise."
