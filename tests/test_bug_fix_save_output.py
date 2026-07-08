"""Teste de regressão — Funcionalidade 10: flag --save-output escreve run_output.txt."""
from pathlib import Path

SRC = (Path(__file__).parent.parent / "src/testforge/cli/app.py").read_text(encoding="utf-8")


def test_save_output_flag_in_argparse():
    """Subparser run deve declarar argumento --save-output."""
    assert "--save-output" in SRC, "--save-output argumento não declarado em app.py"


def test_save_output_writes_file():
    """Código save_output deve escrever run_output.txt."""
    assert "save_output" in SRC, "save_output não referenciado em app.py"
    assert "run_output.txt" in SRC, "run_output.txt não referenciado em app.py"
    # Código deve abrir arquivo para escrita
    assert 'run_output.txt", "w"' in SRC or '"run_output.txt"' in SRC, \
        "escrita de run_output.txt não encontrada em app.py"


def test_save_output_uses_script_dir():
    """Arquivo de saída deve ser colocado junto ao script, não em caminho fixo."""
    assert "os.path.dirname" in SRC and "run_output.txt" in SRC, \
        "save-output deve calcular caminho a partir do diretório do script"
