import json,time
from pathlib import Path
from ..recorder.sensitive_data_detector import scan_for_sensitive_data
class EvidenceCollector:
    def __init__(self,page,root_dir="evidence"):
        self.page=page;self.root=Path(root_dir);self.step_dir=None;self.network=[];self._att=False
    async def start_step(self,run_id,action_id):
        self.step_dir=self.root/run_id/f"{action_id}_{int(time.time()*1000)}"
        self.step_dir.mkdir(parents=True,exist_ok=True);self._attach();await self._snap("before");return self.step_dir
    async def finish_step(self,*,score_breakdown=None,oracle_results=None,promotion_decision=None):
        await self._snap("after");self._w("network_log.json",self.network)
        self._w("score_breakdown.json",score_breakdown or{});self._w("oracle_results.json",oracle_results or[])
        self._w("promotion_decision.json",promotion_decision or{})
        alert=scan_for_sensitive_data([json.dumps(self.network)])
        self._w("sensitive_data_alert.json",alert)
        m={"step_dir":str(self.step_dir),"sensitive_data_alert":alert};self._w("manifest.json",m);return m
    async def _snap(self,label):
        if not self.step_dir:return
        try:await self.page.screenshot(path=str(self.step_dir/f"screenshot_{label}.png"),full_page=True)
        except:pass
        try:(self.step_dir/f"dom_{label}.html").write_text(await self.page.content(),encoding="utf-8")
        except:pass
    def _attach(self):
        if self._att:return
        self.page.on("request",lambda r:self.network.append({"event":"request","url":r.url,"method":r.method}))
        self.page.on("response",lambda r:self.network.append({"event":"response","url":r.url,"status":r.status}))
        self._att=True
    def _w(self,name,data):
        if self.step_dir:(self.step_dir/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
