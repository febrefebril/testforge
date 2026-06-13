from ..semantic.model import LocatorCandidate
class FallbackResult:
    def __init__(self,candidate,success,oracle_passed,error=None):
        self.candidate=candidate;self.success=success;self.oracle_passed=oracle_passed;self.error=error
async def run_fallback(page,candidates,action_type,input_value=None,oracle_fn=None,min_score=0.60):
    for c in sorted([x for x in candidates if x.score>=min_score],key=lambda x:x.score,reverse=True):
        try:
            loc=_resolve(page,c)
            if await loc.count()!=1:continue
            if action_type in("fill","input"):await loc.fill(input_value or"")
            elif action_type=="click":await loc.click()
            ok=True
            if oracle_fn:ok=await oracle_fn()
            return FallbackResult(c,True,ok)
        except:continue
    return FallbackResult(None,False,False,"All candidates failed")
def _resolve(page,c):
    if c.strategy=="role":
        p=c.value.split("[name=");r=p[0];n=p[1].rstrip("]").strip("'\"") if len(p)>1 else ""
        return page.get_by_role(r,name=n)
    if c.strategy=="label":return page.get_by_label(c.value)
    if c.strategy=="test_id":return page.get_by_test_id(c.value)
    if c.strategy=="text":return page.get_by_text(c.value)
    if c.strategy=="placeholder":return page.get_by_placeholder(c.value)
    return page.locator(c.value)
