from testforge.promotion.promotion_gate import PromotionGate
def test_blocks_no_evidence():
    d=PromotionGate().decide(evidence_complete=False,oracle_passed=True)
    assert not d.allowed
def test_blocks_no_oracle():
    d=PromotionGate().decide(evidence_complete=True,oracle_passed=False)
    assert not d.allowed
def test_blocks_few_reviews():
    d=PromotionGate().decide(evidence_complete=True,oracle_passed=True,reviewed_count=5,false_heal_rate=0.0)
    assert not d.allowed
def test_allows_all_ok():
    d=PromotionGate().decide(evidence_complete=True,oracle_passed=True,reviewed_count=50,false_heal_rate=0.0)
    assert d.allowed
