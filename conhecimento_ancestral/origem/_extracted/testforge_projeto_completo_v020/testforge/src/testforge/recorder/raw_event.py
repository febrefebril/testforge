from dataclasses import dataclass,field
from typing import Any,Optional
import json
@dataclass
class RawRecordedEvent:
    schema_version:str="0.2.0"; event_id:str=""; sequence:int=0; timestamp:str=""
    type:str=""; url:str=""; page_title:str=""
    target:Optional[dict]=None; input:Optional[dict]=None
    context:Optional[dict]=None; artifacts:dict=field(default_factory=dict)
    def to_json_line(self)->str: return json.dumps({"schema_version":self.schema_version,"event_id":self.event_id,"sequence":self.sequence,"timestamp":self.timestamp,"type":self.type,"url":self.url,"page_title":self.page_title,"target":self.target,"input":self.input,"context":self.context,"artifacts":self.artifacts},ensure_ascii=False)
