"""Teste de regressão — Bug 4: git publish deve ocorrer APÓS validação de intent."""
from pathlib import Path


def test_app_py_publish_order_in_source():
    """_auto_publish_recording deve aparecer depois de _run_post_recording_completion
    e _run_post_recording_validation no fonte app.py."""
    src = (Path(__file__).parent.parent / "src/testforge/cli/app.py").read_text(encoding="utf-8")

    publish_pos = src.find("_auto_publish_recording(rid, rec_dir)")
    completion_pos = src.find("_run_post_recording_completion(")
    validation_pos = src.find("_run_post_recording_validation(")

    assert publish_pos != -1, "_auto_publish_recording não encontrado em app.py"
    assert completion_pos != -1, "_run_post_recording_completion não encontrado em app.py"
    assert publish_pos > completion_pos, \
        "_auto_publish_recording deve aparecer depois de _run_post_recording_completion"
    if validation_pos != -1:
        assert publish_pos > validation_pos, \
            "_auto_publish_recording deve aparecer depois de _run_post_recording_validation"
