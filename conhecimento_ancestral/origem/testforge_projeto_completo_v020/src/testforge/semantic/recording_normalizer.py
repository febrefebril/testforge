from pathlib import Path
from datetime import datetime,timezone
import json,uuid
from .model import SemanticTestCase,SemanticAction,SemanticTarget,ActionContext
from .candidate_generator import LocatorCandidateGenerator
class RecordingNormalizer:
    def __init__(self): self.gen=LocatorCandidateGenerator()
    def normalize(self,recording_dir,output_dir):
        events=[json.loads(l) for l in (recording_dir/"raw_events.jsonl").read_text(encoding="utf-8").strip().splitlines() if l.strip()]
        meta=json.loads((recording_dir/"recording_metadata.json").read_text(encoding="utf-8"))
        tid=f"TEST-{uuid.uuid4().hex[:8]}"
        stc=SemanticTestCase(test_id=tid,name=f"Test from {meta.get('recording_id','')}",application=meta.get("application",""),source_recording_id=meta.get("recording_id",""),created_at=datetime.now(timezone.utc).astimezone().isoformat(),preconditions={"initial_url":meta.get("base_url","")})
        n=0
        for e in events:
            if e["type"]=="navigation": continue
            n+=1; t=e.get("target") or {}
            target=SemanticTarget(role=t.get("role"),accessible_name=t.get("accessible_name"),label=t.get("label"),placeholder=t.get("placeholder"),test_id=t.get("test_id"),visible_text=t.get("text"),tag=t.get("tag"),attributes=t.get("attributes",{}))
            ctx_r=e.get("context") or {}
            ctx=ActionContext(page_url_pattern=e.get("url"),page_title=ctx_r.get("page_title") or e.get("page_title"),nearby_texts=ctx_r.get("nearby_texts",[]))
            nm=t.get("accessible_name") or t.get("text") or t.get("label") or "elemento"
            intent=f"Preencher {nm}" if e["type"] in ("fill","input") else f"Clicar em {nm}"
            cands=self.gen.generate(target)
            stc.steps.append(SemanticAction(action_id=f"step_{n:03d}",source_event_id=e.get("event_id"),intent=intent,action=e["type"],input=e.get("input"),target=target,context=ctx,locator_candidates=cands))
        out=output_dir/tid/"semantic_test_case.yaml"; stc.save_yaml(out); return out
