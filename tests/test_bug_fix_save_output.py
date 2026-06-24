"""Regression test — Feature 10: --save-output flag writes run_output.txt."""
from pathlib import Path

SRC = (Path(__file__).parent.parent / "src/testforge/cli/app.py").read_text(encoding="utf-8")


def test_save_output_flag_in_argparse():
    """run subparser must declare --save-output argument."""
    assert "--save-output" in SRC, "--save-output argument not declared in app.py"


def test_save_output_writes_file():
    """save_output code path must write run_output.txt."""
    assert "save_output" in SRC, "save_output not referenced in app.py"
    assert "run_output.txt" in SRC, "run_output.txt not referenced in app.py"
    # Code must open the file for writing
    assert 'run_output.txt", "w"' in SRC or '"run_output.txt"' in SRC, \
        "run_output.txt write not found in app.py"


def test_save_output_uses_script_dir():
    """Output file must be placed next to the script, not at a hardcoded path."""
    assert "os.path.dirname" in SRC and "run_output.txt" in SRC, \
        "save-output must compute path from script directory"
