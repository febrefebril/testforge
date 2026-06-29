"""H22b — diagnosticos de deduplicacao no RecordingNormalizer.

Contexto: veja .planning/spikes/SPIKE-keyboard-type-mask.md (secao H22)
e a entrada H22a de 2026-06-27 em DECISIONS-LOG.md.

H22a reordenou a tabela de prioridade de fonte para que `final_state`
supere `setter_hook`. H22b adiciona telemetria por chamada que conta
quantas vezes cada fonte realmente vence outra. O sinal alimenta a
decisao H22c: se `setter_hook` for dominado por `final_state` em toda
gracao, o hook do prototipo (e seu pipeline companheiro
value_mutations.jsonl) pode ser deletado.

Este arquivo fixa:
1. A estrutura de estatisticas existe em cada instancia.
2. As estatisticas resetam entre chamadas `normalize()`.
3. O contador `setter_hook_dominated_by_final_state` incrementa quando
   ambas as fontes disparam para o mesmo campo e final_state vence.
4. O contador `setter_hook_uncontested` incrementa quando setter_hook
   produz um valor sem outra fonte para aquela chave — esta e a
   justificativa restante para manter o hook.
"""
from __future__ import annotations

from testforge.semantic.recording_normalizer import RecordingNormalizer


def _make_entry(key: str, value: str, source: str) -> dict:
    return {
        "field_key": key,
        "value": value,
        "intention": f"fill {key} ({source})",
        "identifiers": {"id": key},
        "source": source,
        "step_index": 0,
        "fingerprint": f"input#{key}[name=]",
    }


class TestStatsShape:
    def test_fresh_stats_has_expected_keys(self):
        n = RecordingNormalizer()
        assert set(n.ir_dedupe_stats.keys()) == {
            "loser_counts",
            "winner_counts",
            "setter_hook_dominated_by_final_state",
            "final_state_uncontested",
            "setter_hook_uncontested",
        }

    def test_stats_are_per_instance(self):
        """Dois normalizers nao devem compartilhar estatisticas de dedup — H22b usa
        estado de instancia precisamente para evitar o bug de estado mutavel em
        nivel de classe que nos afetou em regressoes P2/P3 anteriores."""
        a = RecordingNormalizer()
        b = RecordingNormalizer()
        a.ir_dedupe_stats["loser_counts"]["setter_hook"] = 99
        assert b.ir_dedupe_stats["loser_counts"].get("setter_hook", 0) == 0


class TestDedupeAccountsWinsAndLosses:
    def test_final_state_beats_setter_hook_increments_counter(self):
        n = RecordingNormalizer()
        entries = [
            _make_entry("valor", "1,00", "setter_hook"),
            _make_entry("valor", "10.000,00", "final_state"),
        ]
        out = n._ir_dedupe_entries(entries)
        assert len(out) == 1
        assert out[0]["source"] == "final_state"
        assert n.ir_dedupe_stats["setter_hook_dominated_by_final_state"] == 1
        assert n.ir_dedupe_stats["loser_counts"].get("setter_hook") == 1
        assert n.ir_dedupe_stats["winner_counts"].get("final_state") == 1

    def test_setter_hook_uncontested_when_no_competing_source(self):
        """Se setter_hook e a unica fonte que produziu um valor para uma
        chave, o hook ainda e essencial. Este contador rastreia com que
        frequencia isso acontece para que H22c (deletar _hookValue) possa
        ser baseado em evidencias."""
        n = RecordingNormalizer()
        entries = [
            _make_entry("only_setter_field", "1,00", "setter_hook"),
        ]
        n._ir_dedupe_entries(entries)
        assert n.ir_dedupe_stats["setter_hook_uncontested"] == 1
        assert n.ir_dedupe_stats["final_state_uncontested"] == 0

    def test_final_state_uncontested_when_no_competing_source(self):
        n = RecordingNormalizer()
        entries = [
            _make_entry("only_final_field", "10,00", "final_state"),
        ]
        n._ir_dedupe_entries(entries)
        assert n.ir_dedupe_stats["final_state_uncontested"] == 1
        assert n.ir_dedupe_stats["setter_hook_uncontested"] == 0

    def test_setter_hook_beats_lower_source(self):
        """A nova ordenacao ainda deve permitir que setter_hook vença
        network_payload / polling / snapshot_diff. Fixa para que a
        promocao de H22a nao inverta acidentalmente esses tambem."""
        n = RecordingNormalizer()
        entries = [
            _make_entry("field", "polling_val", "polling"),
            _make_entry("field", "setter_val", "setter_hook"),
        ]
        out = n._ir_dedupe_entries(entries)
        assert len(out) == 1
        assert out[0]["source"] == "setter_hook"
        assert n.ir_dedupe_stats["loser_counts"].get("polling") == 1


class TestStatsResetPerNormalize:
    def test_stats_reset_on_normalize_call(self, tmp_path):
        """Uma segunda invocacao normalize() nao deve carregar estatisticas da
        primeira. Isso espelha o ciclo de vida de invocacoes CLI onde a
        instancia do normalizer pode ser reutilizada entre gravacoes."""
        n = RecordingNormalizer()
        # Polui estatisticas manualmente como se uma chamada anterior tivesse rodado.
        n.ir_dedupe_stats["setter_hook_dominated_by_final_state"] = 5
        n.ir_dedupe_stats["loser_counts"]["setter_hook"] = 10
        # Executa normalize em um diretorio de gravacao vazio.
        # Um diretorio vazio produz um STC vazio mas ainda deve resetar
        # as estatisticas — esse e o contrato H22b.
        try:
            n.normalize(str(tmp_path))
        except Exception:
            # Diretorios vazios podem falhar por falta de raw_events.jsonl; isso
            # e aceitavel para este teste — o reset de estatisticas acontece antes
            # de qualquer E/S de arquivo.
            pass
        assert n.ir_dedupe_stats["setter_hook_dominated_by_final_state"] == 0
        assert n.ir_dedupe_stats["loser_counts"] == {}
