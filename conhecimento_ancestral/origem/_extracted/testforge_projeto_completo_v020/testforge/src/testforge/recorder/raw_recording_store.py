import json
from pathlib import Path
from .recording_session import RecordingSession
from .raw_event import RawRecordedEvent
class RawRecordingStore:
    def __init__(self,root_dir): self.root_dir=Path(root_dir)
    def session_dir(self,rid): return self.root_dir/rid
    def create_session_dir(self,session):
        d=self.session_dir(session.recording_id); d.mkdir(parents=True,exist_ok=True)
        for s in ("screenshots","dom_snapshots","ax_snapshots"): (d/s).mkdir(exist_ok=True)
        (d/"raw_events.jsonl").write_text("",encoding="utf-8"); self.write_metadata(session); return d
    def write_metadata(self,session):
        d=self.session_dir(session.recording_id)
        meta={"schema_version":"0.2.0","kind":"RawRecordedSession","recording_id":session.recording_id,"application":session.application,"base_url":session.base_url,"started_at":session.started_at,"finished_at":session.finished_at,"status":session.status,"event_count":session.event_count}
        (d/"recording_metadata.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    def append_event(self,rid,event):
        with open(self.session_dir(rid)/"raw_events.jsonl","a",encoding="utf-8") as f: f.write(event.to_json_line()+"\n")
    def write_json(self,rid,filename,data): (self.session_dir(rid)/filename).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    def read_events(self,rid):
        lines=(self.session_dir(rid)/"raw_events.jsonl").read_text(encoding="utf-8").strip().splitlines()
        return [json.loads(l) for l in lines if l.strip()]
