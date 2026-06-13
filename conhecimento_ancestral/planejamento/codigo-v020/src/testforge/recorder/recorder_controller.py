import json,time
from datetime import datetime,timezone
from pathlib import Path
from .recording_session import RecordingSession
from .raw_recording_store import RawRecordingStore
from .raw_event import RawRecordedEvent
from .sensitive_data_detector import scan_for_sensitive_data

class RecorderController:
    def __init__(self,root_dir="recordings"):
        self.store=RawRecordingStore(root_dir); self._sessions={}; self._seq={}
        self._net={}; self._vals={}
    def start(self,application,base_url):
        s=RecordingSession.create(application,base_url); self.store.create_session_dir(s)
        self._sessions[s.recording_id]=s; self._seq[s.recording_id]=0
        self._net[s.recording_id]=[]; self._vals[s.recording_id]=[]; return s
    def stop(self,rid):
        s=self._sessions[rid]; s.finish()
        self.store.write_json(rid,"network_log.json",self._net.get(rid,[]))
        alert=scan_for_sensitive_data(self._vals.get(rid,[]))
        self.store.write_json(rid,"sensitive_data_alert.json",alert)
        self.store.write_metadata(s); return s
    def add_event(self,rid,event):
        s=self._sessions[rid]
        if s.status!="recording": raise RuntimeError("Session already finished.")
        self._seq[rid]+=1; event.sequence=self._seq[rid]
        if not event.event_id: event.event_id=f"evt_{event.sequence:04d}"
        if not event.timestamp: event.timestamp=datetime.now(timezone.utc).astimezone().isoformat()
        if event.input and event.input.get("value"):
            v=str(event.input["value"]); self._vals.setdefault(rid,[]).append(v)
            event.input["sensitive_data_alert"]=scan_for_sensitive_data([v])
        self.store.append_event(rid,event); s.event_count+=1
    async def start_browser_recording(self,page,application,base_url):
        s=self.start(application,base_url); rid=s.recording_id; self._page=page
        async def _target(el):
            try:
                return await page.evaluate("""(el)=>{const r=el.getBoundingClientRect();const ls=el.labels?Array.from(el.labels).map(l=>l.textContent.trim()):[];const nb=[];const p=el.closest('form,section,main,div');if(p)p.querySelectorAll('label,h1,h2,h3,p,span,th').forEach(n=>{const t=n.textContent.trim();if(t&&t.length<100)nb.push(t)});return{tag:el.tagName.toLowerCase(),text:(el.textContent||'').trim().substring(0,200),role:el.getAttribute('role')||el.tagName.toLowerCase(),accessible_name:el.getAttribute('aria-label')||'',label:ls.length?ls[0]:null,placeholder:el.getAttribute('placeholder')||null,id:el.id||null,name:el.getAttribute('name')||null,test_id:el.getAttribute('data-testid')||null,attributes:Object.fromEntries(Array.from(el.attributes).map(a=>[a.name,a.value])),bounding_box:{x:r.x,y:r.y,width:r.width,height:r.height},nearby_texts:nb.slice(0,10)}}""",el)
            except: return {"tag":"unknown"}
        self._target=_target
        async def _snap(eid):
            a={}; sd=self.store.session_dir(rid)
            try: await page.screenshot(path=str(sd/f"screenshots/{eid}.png"),full_page=True); a["screenshot"]=f"screenshots/{eid}.png"
            except: pass
            try: (sd/f"dom_snapshots/{eid}.html").write_text(await page.content(),encoding="utf-8"); a["dom_snapshot"]=f"dom_snapshots/{eid}.html"
            except: pass
            try:
                ax=await page.accessibility.snapshot(interesting_only=False)
                (sd/f"ax_snapshots/{eid}.json").write_text(json.dumps(ax or {},ensure_ascii=False,indent=2),encoding="utf-8"); a["ax_snapshot"]=f"ax_snapshots/{eid}.json"
            except: pass
            return a
        self._snap=_snap; return s
    async def record_navigation(self,rid,url):
        eid=f"evt_{self._seq.get(rid,0)+1:04d}"; a=await self._snap(eid)
        self.add_event(rid,RawRecordedEvent(type="navigation",url=url,page_title=await self._page.title(),artifacts=a))
    async def record_action(self,rid,action_type,element,input_value=None):
        eid=f"evt_{self._seq.get(rid,0)+1:04d}"; t=await self._target(element); a=await self._snap(eid)
        inp={"value":input_value,"value_kind":"literal_observed"} if input_value else None
        ctx={"nearby_texts":t.pop("nearby_texts",[]),"page_title":await self._page.title()}
        self.add_event(rid,RawRecordedEvent(type=action_type,url=self._page.url,page_title=await self._page.title(),target=t,input=inp,context=ctx,artifacts=a))
