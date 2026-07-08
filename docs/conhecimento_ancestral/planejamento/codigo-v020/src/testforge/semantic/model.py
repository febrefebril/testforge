from dataclasses import dataclass,field
from typing import Any,Optional
from pathlib import Path
import json,yaml
@dataclass
class LocatorCandidate:
    strategy:str="";value:str="";playwright_expr:str="";score:float=0.0;reason:str=""
@dataclass
class SemanticTarget:
    role:Optional[str]=None;accessible_name:Optional[str]=None;label:Optional[str]=None
    placeholder:Optional[str]=None;test_id:Optional[str]=None;visible_text:Optional[str]=None
    tag:Optional[str]=None;attributes:dict=field(default_factory=dict)
@dataclass
class ActionContext:
    page_url_pattern:Optional[str]=None;page_title:Optional[str]=None;nearby_texts:list=field(default_factory=list)
@dataclass
class ExpectedAfterAction:
    type:str="";target:Optional[dict]=None;expected:Optional[str]=None
@dataclass
class SemanticAction:
    action_id:str="";source_event_id:Optional[str]=None;intent:str="";action:str=""
    input:Optional[dict]=None;target:SemanticTarget=field(default_factory=SemanticTarget)
    context:ActionContext=field(default_factory=ActionContext)
    locator_candidates:list=field(default_factory=list);expected_after_action:list=field(default_factory=list)
@dataclass
class SemanticTestCase:
    test_id:str="";name:str="";application:str="";source_recording_id:str=""
    created_at:str="";schema_version:str="0.2.0";preconditions:dict=field(default_factory=dict)
    steps:list=field(default_factory=list)
    healing_policy:dict=field(default_factory=lambda:{"deterministic_first":True,"auto_heal_threshold":0.90,"quarantine_threshold":0.75})
    def save_yaml(self,path):
        path.parent.mkdir(parents=True,exist_ok=True)
        from dataclasses import asdict
        path.write_text(yaml.dump(asdict(self),default_flow_style=False,allow_unicode=True,sort_keys=False),encoding="utf-8")
    @staticmethod
    def load_yaml(path):
        d=yaml.safe_load(path.read_text(encoding="utf-8"))
        stc=SemanticTestCase(**{k:v for k,v in d.items() if k!="steps"});stc.steps=[]
        for s in d.get("steps",[]):
            t=SemanticTarget(**s.pop("target",{}));c=ActionContext(**s.pop("context",{}))
            cands=[LocatorCandidate(**x) for x in s.pop("locator_candidates",[])]
            eaa=[ExpectedAfterAction(**x) for x in s.pop("expected_after_action",[])]
            stc.steps.append(SemanticAction(target=t,context=c,locator_candidates=cands,expected_after_action=eaa,**s))
        return stc
