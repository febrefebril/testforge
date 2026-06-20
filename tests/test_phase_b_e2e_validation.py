"""TestForge — Story 4.1: Batch E2E Validation.

Valida normalização em lote das gravações reais disponíveis em recordings/.
Testes offline: sem browser, sem Playwright — apenas normalização + análise.
"""
import os
import subprocess

import pytest

from testforge.semantic.model import SemanticTestCase
from testforge.semantic.recording_normalizer import RecordingNormalizer


def _encontrar_recordings_dir() -> str:
    """Encontra o diretório recordings/ a partir do repositório principal.

    Funciona tanto no checkout principal quanto em worktrees vinculados:
    usa git rev-parse --git-common-dir para obter o .git do repo principal,
    depois sobe um nível para chegar à raiz do projeto.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, check=True,
            cwd=os.path.dirname(__file__),
        )
        git_common = result.stdout.strip()
        # git-common-dir aponta para .git/ do repo principal
        repo_root = os.path.dirname(os.path.abspath(git_common))
        candidate = os.path.join(repo_root, "recordings")
        if os.path.isdir(candidate):
            return candidate
    except Exception:
        pass
    # Fallback: busca relativa ao arquivo de teste
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
def gravacoes_disponiveis():
    """Retorna lista de caminhos de gravações com raw_events.jsonl."""
    return _descobrir_gravacoes()


@pytest.fixture(scope="module")
def normalizer():
    return RecordingNormalizer()


class TestBatchNormalize:
    """CT-AUTO-4.1 — Normalização em lote das gravações reais."""

    def test_gravacoes_encontradas(self, gravacoes_disponiveis):
        """Pelo menos uma gravação com raw_events.jsonl deve existir."""
        assert len(gravacoes_disponiveis) > 0, (
            f"Nenhuma gravação com raw_events.jsonl encontrada "
            f"(recordings_dir={_RECORDINGS_DIR!r}). "
            "Execute o gravador para gerar dados reais."
        )

    def test_normalize_available_recordings(self, gravacoes_disponiveis, normalizer):
        """Normaliza todas as gravações disponíveis sem crashes.

        Para cada gravação com raw_events.jsonl:
        - normalize() não lança exceção
        - Retorna SemanticTestCase válido
        - Contém pelo menos 1 step
        """
        if not gravacoes_disponiveis:
            pytest.skip("Nenhuma gravação disponível para normalizar")

        resultados = {}
        erros = []

        for recording_dir in gravacoes_disponiveis:
            recording_id = os.path.basename(recording_dir)
            try:
                stc = normalizer.normalize(
                    recording_dir=recording_dir,
                    test_id=f"ST-{recording_id}",
                )
                assert isinstance(stc, SemanticTestCase), (
                    f"{recording_id}: normalize() deve retornar SemanticTestCase, "
                    f"obteve {type(stc).__name__}"
                )
                assert len(stc.steps) >= 1, (
                    f"{recording_id}: SemanticTestCase sem steps "
                    f"(raw_events.jsonl vazio?)"
                )
                resultados[recording_id] = {
                    "steps": len(stc.steps),
                    "steps_ativos": sum(1 for s in stc.steps if not s.skip_reason),
                    "field_values": len(stc.field_values or {}),
                    "blind_spots": len(stc.blind_spots or []),
                }
            except Exception as exc:
                erros.append(f"{recording_id}: {type(exc).__name__}: {exc}")

        # Reportar resumo para diagnóstico
        print("\n--- Resumo de normalização ---")
        for rid, r in resultados.items():
            print(
                f"  {rid}: {r['steps']} steps "
                f"({r['steps_ativos']} ativos, "
                f"{r['field_values']} campos, "
                f"{r['blind_spots']} blind spots)"
            )
        if erros:
            print("\n--- Erros ---")
            for e in erros:
                print(f"  {e}")

        assert not erros, (
            f"{len(erros)} gravação(ões) falharam na normalização:\n"
            + "\n".join(erros)
        )

    def test_field_values_coverage_by_recording(self, gravacoes_disponiveis, normalizer):
        """Verifica cobertura de field_values por gravação.

        Para cada gravação: field_values não deve ser completamente vazio se
        houver eventos de fill ativos no resultado normalizado.
        Reporta coverage dict por recording_id.
        """
        if not gravacoes_disponiveis:
            pytest.skip("Nenhuma gravação disponível")

        coverage = {}
        gravacoes_com_fills = []

        for recording_dir in gravacoes_disponiveis:
            recording_id = os.path.basename(recording_dir)
            stc = normalizer.normalize(
                recording_dir=recording_dir,
                test_id=f"ST-{recording_id}",
            )
            fv = stc.field_values or {}
            total = len(fv)
            com_valor = sum(1 for v in fv.values() if v.value)
            sem_valor = total - com_valor

            fills_ativos = sum(
                1 for s in stc.steps
                if s.action == "fill" and not s.skip_reason
            )

            coverage[recording_id] = {
                "total_campos": total,
                "com_valor": com_valor,
                "sem_valor": sem_valor,
                "fills_ativos": fills_ativos,
                "cobertura_pct": round(100 * com_valor / total, 1) if total > 0 else 0,
            }

            if fills_ativos > 0:
                gravacoes_com_fills.append(recording_id)

        print("\n--- Cobertura de field_values por gravação ---")
        for rid, c in coverage.items():
            pct = c["cobertura_pct"]
            print(
                f"  {rid}: {c['com_valor']}/{c['total_campos']} campos com valor "
                f"({pct}%), {c['fills_ativos']} fills ativos"
            )

        # Gravações com fills ativos devem ter ao menos algum campo mapeado
        for recording_id in gravacoes_com_fills:
            c = coverage[recording_id]
            assert c["total_campos"] > 0, (
                f"{recording_id}: tem {c['fills_ativos']} fill(s) ativo(s) "
                "mas field_values está vazio — normalização falhou em mapear campos"
            )

    def test_blind_spots_density(self, gravacoes_disponiveis, normalizer):
        """Verifica que blind_spots não dominam os steps ativos.

        Threshold: blind_spots < 50% dos steps ativos.
        Threshold relaxado para dados reais (podem ter mais gaps).
        Gravações com < 3 steps ativos são ignoradas (amostra pequena).
        """
        if not gravacoes_disponiveis:
            pytest.skip("Nenhuma gravação disponível")

        threshold = 0.50
        violacoes = []

        for recording_dir in gravacoes_disponiveis:
            recording_id = os.path.basename(recording_dir)
            stc = normalizer.normalize(
                recording_dir=recording_dir,
                test_id=f"ST-{recording_id}",
            )
            steps_ativos = [s for s in stc.steps if not s.skip_reason]
            blind_spots = stc.blind_spots or []

            total_ativos = len(steps_ativos)
            total_blind = len(blind_spots)

            if total_ativos < 3:
                continue

            densidade = total_blind / total_ativos
            if densidade >= threshold:
                violacoes.append(
                    f"{recording_id}: {total_blind}/{total_ativos} steps = "
                    f"{densidade:.0%} blind spots (limite: {threshold:.0%})"
                )

        if violacoes:
            print("\n--- Gravações com alta densidade de blind spots ---")
            for v in violacoes:
                print(f"  {v}")

        assert not violacoes, (
            f"{len(violacoes)} gravação(ões) excedem {threshold:.0%} de blind spots:\n"
            + "\n".join(violacoes)
        )
