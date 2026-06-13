from pathlib import Path
from ..semantic.model import SemanticTestCase
class PlaywrightPythonCompiler:
    def compile(self,stc,output_dir):
        out=output_dir/stc.test_id; out.mkdir(parents=True,exist_ok=True)
        lines=["import pytest","from playwright.sync_api import Page,expect","",f"class Test{stc.test_id.replace('-','_')}:",f'    """Generated from {stc.source_recording_id}"""',"",f"    def test_{stc.application.replace('-','_')}(self,page:Page)->None:",f"        page.goto({stc.preconditions.get('initial_url','')!r})"]
        for s in stc.steps:
            b=s.locator_candidates[0] if s.locator_candidates else None
            if not b: lines.append(f"        # SKIP {s.action_id}"); continue
            if s.action in ("fill","input"):
                v=(s.input or {}).get("value",""); lines.append(f"        {b.playwright_expr}.fill({v!r})")
            elif s.action=="click": lines.append(f"        {b.playwright_expr}.click()")
        lines.append("")
        tf=out/f"test_{stc.application.replace('-','_')}.py"; tf.write_text("\n".join(lines),encoding="utf-8"); return tf
