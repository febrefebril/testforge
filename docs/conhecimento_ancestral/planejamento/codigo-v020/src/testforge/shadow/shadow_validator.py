from ..taxonomy.taxonomy import FailureTaxonomy
from ..semantic.model import SemanticAction
from ..semantic.candidate_generator import LocatorCandidateGenerator
class ShadowValidator:
    def __init__(self,taxonomy):self.taxonomy=taxonomy;self.gen=LocatorCandidateGenerator()
    def suggest(self,action,taxonomy_code):
        if not self.taxonomy.allows_healing(taxonomy_code):return None
        cands=self.gen.generate(action.target)
        if not cands:return None
        b=cands[0]
        return {"action_id":action.action_id,"taxonomy_code":taxonomy_code,"original_locator":action.locator_candidates[0].playwright_expr if action.locator_candidates else "","suggested_locator":b.playwright_expr,"score":b.score,"mode":"shadow"}
