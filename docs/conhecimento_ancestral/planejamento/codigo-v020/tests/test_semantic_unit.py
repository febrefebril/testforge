from testforge.semantic.model import SemanticTarget,SemanticTestCase,SemanticAction
from testforge.semantic.candidate_generator import LocatorCandidateGenerator
def test_role():
    g=LocatorCandidateGenerator();c=g.generate(SemanticTarget(role="button",accessible_name="OK"))
    assert any(x.strategy=="role" for x in c)
def test_label():
    g=LocatorCandidateGenerator();c=g.generate(SemanticTarget(role="textbox",accessible_name="CPF",label="CPF",placeholder="Informe"))
    assert any(x.strategy=="label" for x in c)
def test_testid():
    g=LocatorCandidateGenerator();c=g.generate(SemanticTarget(role="button",accessible_name="X",test_id="tid"))
    assert any(x.strategy=="test_id" for x in c)
def test_yaml(tmp_path):
    s=SemanticTestCase(test_id="T1",name="T",application="a")
    s.steps.append(SemanticAction(action_id="s1",intent="i",action="click",target=SemanticTarget(role="button",accessible_name="OK")))
    p=tmp_path/"t.yaml";s.save_yaml(p);l=SemanticTestCase.load_yaml(p)
    assert l.test_id=="T1";assert len(l.steps)==1
