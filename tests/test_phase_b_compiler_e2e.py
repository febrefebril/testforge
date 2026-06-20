"""TestForge — Story 4.2: Compiler Integration E2E.

Valida o pipeline completo: gravação real → normalize → compile → Python válido.
Testes offline: sem browser, sem execução de Playwright — apenas sintaxe.
"""
import os
import py_compile
import subprocess
import tempfile

import pytest

from testforge.semantic.compiler import PlaywrightCompiler
from testforge.semantic.model import SemanticTestCase
from testforge.semantic.recording_normalizer import RecordingNormalizer


def _encontrar_recordings_dir() -> str:
    """Encontra o diretório recordings/ no repositório principal.

    Funciona tanto no checkout principal quanto em worktrees vinculados.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, check=True,
            cwd=os.path.dirname(__file__),
        )
        git_common = result.stdout.strip()
        repo_root = os.path.dirname(os.path.abspath(git_common))
        candidate = os.path.join(repo_root, "recordings")
        if os.path.isdir(candidate):
            return candidate
    except Exception:
        pass
    aqui = os.path.dirname(os.path.abspath(__file__))
    for _ in range(4):
        candidate = os.path.join(aqui, "recordings")
        if os.path.isdir(candidate):
            return candidate
        aqui = os.path.dirname(aqui)
    return ""


_RECORDINGS_DIR = _encontrar_recordings_dir()


def _descobrir_gravacoes() -> list:
    """Descobre gravações em recordings/ que possuem raw_events.jsonl."""
    gravacoes = []
    if not _RECORDINGS_DIR or not os.path.isdir(_RECORDINGS_DIR):
        return gravacoes
    for nome in sorted(os.listdir(_RECORDINGS_DIR)):
        caminho = os.path.join(_RECORDINGS_DIR, nome)
        if os.path.isdir(caminho) and os.path.exists(
            os.path.join(caminho, "raw_events.jsonl")
        ):
            gravacoes.append(caminho)
    return gravacoes


@pytest.fixture(scope="module")
def normalizer():
    return RecordingNormalizer()


@pytest.fixture(scope="module")
def compiler():
    return PlaywrightCompiler()


@pytest.fixture(scope="module")
def gravacoes_disponiveis():
    return _descobrir_gravacoes()


@pytest.fixture(scope="module")
def primeira_gravacao(gravacoes_disponiveis):
    """Retorna a primeira gravação disponível ou pula se não houver nenhuma."""
    if not gravacoes_disponiveis:
        pytest.skip("Nenhuma gravação disponível em recordings/")
    return gravacoes_disponiveis[0]


@pytest.fixture(scope="module")
def stc_normalizado(primeira_gravacao, normalizer):
    """SemanticTestCase normalizado da primeira gravação disponível."""
    recording_id = os.path.basename(primeira_gravacao)
    return normalizer.normalize(
        recording_dir=primeira_gravacao,
        test_id=f"ST-{recording_id}",
    )


class TestCompilerE2E:
    """CT-AUTO-4.2 — Pipeline normaliza → compila → Python válido."""

    def test_compile_with_field_values(self, stc_normalizado, compiler, tmp_path):
        """Pipeline completo com field_values.

        Normaliza uma gravação real → compila com field_values injetados →
        verifica que o arquivo .py gerado existe.
        """
        stc = stc_normalizado
        assert isinstance(stc, SemanticTestCase)
        assert len(stc.steps) >= 1, "Gravação normalizada sem steps"

        output_dir = str(tmp_path / "compilado")
        caminho = compiler.compile(
            test_case=stc,
            output_dir=output_dir,
            field_values=stc.field_values or {},
        )

        assert os.path.isfile(caminho), (
            f"compile() deve retornar caminho de arquivo existente, "
            f"obteve: {caminho!r}"
        )
        assert caminho.endswith(".py"), (
            f"Arquivo gerado deve ter extensão .py, obteve: {caminho!r}"
        )

        tamanho = os.path.getsize(caminho)
        assert tamanho > 0, f"Arquivo gerado está vazio: {caminho}"

        print(f"\nArquivo gerado: {caminho} ({tamanho} bytes)")

    def test_compile_generates_valid_python(self, stc_normalizado, compiler, tmp_path):
        """Arquivo gerado passa em py_compile (sintaxe válida).

        Não requer execução de browser — verifica apenas que o código
        gerado é Python sintaticamente correto.
        """
        stc = stc_normalizado
        output_dir = str(tmp_path / "validacao_sintaxe")

        caminho = compiler.compile(
            test_case=stc,
            output_dir=output_dir,
            field_values=stc.field_values or {},
        )

        # Verifica sintaxe sem executar
        try:
            py_compile.compile(caminho, doraise=True)
        except py_compile.PyCompileError as exc:
            with open(caminho) as f:
                codigo = f.read()
            pytest.fail(
                f"Sintaxe inválida no script gerado ({caminho}):\n"
                f"{exc}\n\n"
                f"--- Primeiras 30 linhas do código gerado ---\n"
                + "\n".join(codigo.splitlines()[:30])
            )

        print(f"\nSintaxe OK: {caminho}")

    def test_compile_contém_função_de_teste(self, stc_normalizado, compiler, tmp_path):
        """Script gerado contém pelo menos uma função test_*.

        Playwright Test Runner requer que funções de teste comecem com test_.
        """
        stc = stc_normalizado
        output_dir = str(tmp_path / "func_check")

        caminho = compiler.compile(
            test_case=stc,
            output_dir=output_dir,
        )

        with open(caminho) as f:
            codigo = f.read()

        funcoes_teste = [
            linha.strip()
            for linha in codigo.splitlines()
            if linha.strip().startswith("def test_")
        ]
        assert len(funcoes_teste) >= 1, (
            f"Script gerado não contém nenhuma função test_*:\n"
            f"--- Código gerado (primeiras 40 linhas) ---\n"
            + "\n".join(codigo.splitlines()[:40])
        )
        print(f"\nFunções de teste encontradas: {funcoes_teste}")

    def test_compile_todas_gravacoes(self, gravacoes_disponiveis, normalizer, compiler, tmp_path):
        """Compila todas as gravações disponíveis sem erros de sintaxe.

        Pipeline lote: normalize + compile em cada gravação.
        """
        if not gravacoes_disponiveis:
            pytest.skip("Nenhuma gravação disponível")

        erros_normalizacao = []
        erros_compilacao = []
        erros_sintaxe = []
        sucessos = []

        for recording_dir in gravacoes_disponiveis:
            recording_id = os.path.basename(recording_dir)
            output_dir = str(tmp_path / f"lote_{recording_id}")

            try:
                stc = normalizer.normalize(
                    recording_dir=recording_dir,
                    test_id=f"ST-{recording_id}",
                )
            except Exception as exc:
                erros_normalizacao.append(f"{recording_id}: {exc}")
                continue

            try:
                caminho = compiler.compile(
                    test_case=stc,
                    output_dir=output_dir,
                    field_values=stc.field_values or {},
                )
            except Exception as exc:
                erros_compilacao.append(f"{recording_id}: {exc}")
                continue

            try:
                py_compile.compile(caminho, doraise=True)
            except py_compile.PyCompileError as exc:
                erros_sintaxe.append(f"{recording_id}: {exc}")
                continue

            sucessos.append(recording_id)

        print(f"\n--- Resultado do lote ({len(gravacoes_disponiveis)} gravações) ---")
        print(f"  Sucesso: {len(sucessos)} — {', '.join(sucessos)}")
        if erros_normalizacao:
            print(f"  Erros normalização: {erros_normalizacao}")
        if erros_compilacao:
            print(f"  Erros compilação: {erros_compilacao}")
        if erros_sintaxe:
            print(f"  Erros sintaxe: {erros_sintaxe}")

        todos_erros = erros_normalizacao + erros_compilacao + erros_sintaxe
        assert not todos_erros, (
            f"{len(todos_erros)} erro(s) no pipeline lote:\n"
            + "\n".join(todos_erros)
        )
