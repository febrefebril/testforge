from dataclasses import dataclass,field
class PromotionDecision:
    def __init__(self,allowed,from_state,to_state,reasons=None):
        self.allowed=allowed;self.from_state=from_state;self.to_state=to_state;self.reasons=reasons or[]
class PromotionGate:
    def decide(self,*,evidence_complete,oracle_passed,oracle_conflict=False,false_heal_reviewed=False,reviewed_count=0,false_heal_rate=1.0,current_state="experimental",target_state="shadow_validated"):
        r=[]
        if not evidence_complete:r.append("Evidence package incompleto.")
        if not oracle_passed:r.append("Oracle não passou.")
        if oracle_conflict:r.append("Conflito entre oracles.")
        if false_heal_reviewed:r.append("Existe falso healing revisado.")
        if target_state=="shadow_validated":
            if reviewed_count<30:r.append(f"Apenas {reviewed_count} observações revisadas (mín 30).")
            if false_heal_rate>=0.02:r.append(f"False heal rate {false_heal_rate:.2%} >= 2%.")
        return PromotionDecision(allowed=len(r)==0,from_state=current_state,to_state=target_state,reasons=r)
