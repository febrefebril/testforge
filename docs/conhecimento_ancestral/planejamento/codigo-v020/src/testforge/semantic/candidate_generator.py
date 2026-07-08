from .model import SemanticTarget,LocatorCandidate
class LocatorCandidateGenerator:
    def generate(self,target):
        c=[]
        if target.role and target.accessible_name:
            c.append(LocatorCandidate(strategy="role",value=f"{target.role}[name={target.accessible_name!r}]",playwright_expr=f"page.get_by_role({target.role!r},name={target.accessible_name!r})",score=0.95,reason="Role+accessible name"))
        if target.label:
            c.append(LocatorCandidate(strategy="label",value=target.label,playwright_expr=f"page.get_by_label({target.label!r})",score=0.94,reason="Label"))
        if target.placeholder:
            c.append(LocatorCandidate(strategy="placeholder",value=target.placeholder,playwright_expr=f"page.get_by_placeholder({target.placeholder!r})",score=0.80,reason="Placeholder"))
        if target.test_id:
            c.append(LocatorCandidate(strategy="test_id",value=target.test_id,playwright_expr=f"page.get_by_test_id({target.test_id!r})",score=0.92,reason="Test id"))
        if target.visible_text:
            c.append(LocatorCandidate(strategy="text",value=target.visible_text,playwright_expr=f"page.get_by_text({target.visible_text!r})",score=0.72,reason="Texto visível"))
        return sorted(c,key=lambda x:x.score,reverse=True)
