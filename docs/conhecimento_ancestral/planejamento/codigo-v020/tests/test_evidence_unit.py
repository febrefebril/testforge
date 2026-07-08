from testforge.evidence.evidence_store import EvidenceStore
def test_insert_and_query(tmp_path):
    s=EvidenceStore(tmp_path/"t.sqlite")
    sid=s.insert_healing_suggestion(run_id="r",application="a",page_signature="p",action_id="a1",taxonomy_code="LOCATOR_NOT_FOUND",original_locator="x",suggested_locator="y",total_score=0.9)
    s.insert_evidence_package(sid,{"t":1})
    s.insert_oracle_observation(healing_suggestion_id=sid,oracle_type="v",expected="e",result="passed")
    assert len(s.list_pending_reviews())==1
    s.insert_review_decision(healing_suggestion_id=sid,label="TRUE_POSITIVE_HEAL")
    assert len(s.list_pending_reviews())==0
def test_metrics(tmp_path):
    s=EvidenceStore(tmp_path/"t.sqlite")
    sid=s.insert_healing_suggestion(run_id="r",application="a",page_signature="p",action_id="a1",taxonomy_code="X",original_locator="x",suggested_locator="y",total_score=0.9)
    s.insert_review_decision(healing_suggestion_id=sid,label="TRUE_POSITIVE_HEAL")
    m=s.get_metrics();assert m["precision"]==1.0
