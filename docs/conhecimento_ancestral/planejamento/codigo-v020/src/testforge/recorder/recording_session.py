from dataclasses import dataclass
from datetime import datetime,timezone
import uuid
@dataclass
class RecordingSession:
    recording_id:str=""; application:str=""; base_url:str=""
    started_at:str=""; finished_at:str=None; status:str="recording"; event_count:int=0
    @staticmethod
    def create(application,base_url):
        now=datetime.now(timezone.utc).astimezone()
        return RecordingSession(recording_id=f"REC-{now.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}",application=application,base_url=base_url,started_at=now.isoformat(),status="recording")
    def finish(self):
        self.finished_at=datetime.now(timezone.utc).astimezone().isoformat(); self.status="finished"
