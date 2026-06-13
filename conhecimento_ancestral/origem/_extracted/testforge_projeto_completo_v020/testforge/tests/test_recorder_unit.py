import json
from testforge.recorder.recorder_controller import RecorderController
from testforge.recorder.raw_event import RawRecordedEvent
from testforge.recorder.sensitive_data_detector import scan_for_sensitive_data

def test_session_start_stop(tmp_path):
    c=RecorderController(root_dir=tmp_path);s=c.start("app","http://x")
    assert s.recording_id.startswith("REC-")
    assert (tmp_path/s.recording_id).exists()
    c.stop(s.recording_id)
    m=json.loads((tmp_path/s.recording_id/"recording_metadata.json").read_text())
    assert m["status"]=="finished"

def test_rejects_after_stop(tmp_path):
    c=RecorderController(root_dir=tmp_path);s=c.start("app","http://x");c.stop(s.recording_id)
    try: c.add_event(s.recording_id,RawRecordedEvent(type="click")); assert False
    except RuntimeError: pass

def test_add_event_writes_jsonl(tmp_path):
    c=RecorderController(root_dir=tmp_path);s=c.start("app","http://x")
    c.add_event(s.recording_id,RawRecordedEvent(type="click",url="http://x"))
    c.add_event(s.recording_id,RawRecordedEvent(type="fill",url="http://x",input={"value":"12345678900","value_kind":"literal"}))
    c.stop(s.recording_id)
    lines=(tmp_path/s.recording_id/"raw_events.jsonl").read_text().strip().splitlines()
    assert len(lines)==2

def test_sensitive_cpf():
    a=scan_for_sensitive_data(["12345678900"])
    assert a["possible_sensitive_data_detected"];assert not a["masking_applied"]

def test_sensitive_clean():
    a=scan_for_sensitive_data(["hello"])
    assert not a["possible_sensitive_data_detected"]

def test_preserved_in_events(tmp_path):
    c=RecorderController(root_dir=tmp_path);s=c.start("app","http://x")
    c.add_event(s.recording_id,RawRecordedEvent(type="fill",url="http://x",input={"value":"12345678900","value_kind":"literal"}))
    c.stop(s.recording_id)
    assert "12345678900" in (tmp_path/s.recording_id/"raw_events.jsonl").read_text()
    a=json.loads((tmp_path/s.recording_id/"sensitive_data_alert.json").read_text())
    assert not a["masking_applied"]
