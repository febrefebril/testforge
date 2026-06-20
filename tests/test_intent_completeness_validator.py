"""Testes do IntentCompletenessValidator — Story 1.2.

5 cenários obrigatórios:
  a. test_completeness_all_fields          — score 1.0, gate aprovado
  b. test_completeness_missing_fields      — score < 0.70, gate reprovado
  c. test_completeness_blind_spots         — blind_spots contam como missing
  d. test_completeness_threshold_boundary  — score exato de 0.70
  e. test_completeness_empty_stc           — SemanticTestCase sem steps
"""

import pytest

from testforge.semantic.model import (
    FieldValueMap,
    SemanticTestCase,
)
from testforge.validation.intent_completeness import IntentCompletenessValidator


# ── Fixture base ───────────────────────────────────────────────────────────────


@pytest.fixture
def validator():
    return IntentCompletenessValidator()


def _stc(field_values: dict | None = None, blind_spots: list | None = None) -> SemanticTestCase:
    """Cria SemanticTestCase mínimo para testes de completude."""
    return SemanticTestCase(
        test_id="tc-test",
        source_recording_id="rec-test",
        field_values=field_values or {},
        blind_spots=blind_spots or [],
    )


def _fvm(chave: str, valor: str, source: str = "fill_event") -> FieldValueMap:
    """Cria FieldValueMap com valores mínimos."""
    return FieldValueMap(
        field_key=chave,
        value=valor,
        source=source,
        identifiers={"name": chave, "label": chave.capitalize()},
    )


# ── (a) Score 1.0 — todos os campos preenchidos ───────────────────────────────


class TestCompletenessAllFields:
    """Cenário (a): todos os campos têm valores — score 1.0, gate aprovado."""

    def test_score_um_quando_todos_preenchidos(self, validator):
        """Score deve ser 1.0 quando todos os campos têm fonte confiável."""
        stc = _stc(
            field_values={
                "nome": _fvm("nome", "João Silva"),
                "email": _fvm("email", "joao@teste.com"),
                "cpf": _fvm("cpf", "000.000.000-00"),
            }
        )

        resultado = validator.validate(stc)

        assert resultado["completeness_score"] == 1.0

    def test_passes_gate_quando_score_um(self, validator):
        """passes_gate=True quando score é 1.0."""
        stc = _stc(
            field_values={
                "nome": _fvm("nome", "João Silva"),
                "email": _fvm("email", "joao@teste.com"),
            }
        )

        resultado = validator.validate(stc)

        assert resultado["passes_gate"] is True

    def test_missing_fields_vazio_quando_completo(self, validator):
        """missing_fields deve ser lista vazia quando todos preenchidos."""
        stc = _stc(
            field_values={
                "nome": _fvm("nome", "Ana Lima"),
                "renda": _fvm("renda", "5000", source="form_values"),
            }
        )

        resultado = validator.validate(stc)

        assert resultado["missing_fields"] == []

    def test_contrato_de_retorno_completo(self, validator):
        """Resultado contém todas as chaves do contrato."""
        stc = _stc(field_values={"valor": _fvm("valor", "1000")})

        resultado = validator.validate(stc)

        assert set(resultado.keys()) == {
            "completeness_score",
            "missing_fields",
            "blind_spots_count",
            "passes_gate",
            "reason",
        }


# ── (b) Score < 0.70 — campos ausentes reprovam gate ─────────────────────────


class TestCompletenessMissingFields:
    """Cenário (b): campos missing_fill fazem score < 0.70 — gate reprovado."""

    def test_gate_reprovado_com_maioria_ausente(self, validator):
        """Quando maioria dos campos é missing_fill → passes_gate=False."""
        stc = _stc(
            field_values={
                # 1 preenchido
                "nome": _fvm("nome", "Carlos"),
                # 3 ausentes
                "renda": _fvm("renda", "", source="missing_fill"),
                "cpf": _fvm("cpf", "", source="missing_fill"),
                "data_nascimento": _fvm("data_nascimento", "", source="missing_fill"),
            }
        )

        resultado = validator.validate(stc)

        # 1 de 4 = 25% — abaixo do gate de 70%
        assert resultado["passes_gate"] is False
        assert resultado["completeness_score"] < 0.70

    def test_missing_fields_lista_campos_ausentes(self, validator):
        """missing_fields lista as chaves dos campos ausentes."""
        stc = _stc(
            field_values={
                "nome": _fvm("nome", "Carlos"),
                "renda": _fvm("renda", "", source="missing_fill"),
                "cpf": _fvm("cpf", "", source="missing_fill"),
            }
        )

        resultado = validator.validate(stc)

        assert "renda" in resultado["missing_fields"]
        assert "cpf" in resultado["missing_fields"]
        assert "nome" not in resultado["missing_fields"]

    def test_campo_sem_valor_conta_como_ausente(self, validator):
        """Campo com source ok mas value vazio também conta como missing."""
        stc = _stc(
            field_values={
                "nome": _fvm("nome", ""),      # valor vazio — ausente
                "email": _fvm("email", "x@y"), # preenchido
            }
        )

        resultado = validator.validate(stc)

        assert "nome" in resultado["missing_fields"]
        assert resultado["completeness_score"] == 0.5  # 1 de 2

    def test_reason_menciona_gate_reprovado(self, validator):
        """reason menciona que o gate foi reprovado."""
        stc = _stc(
            field_values={
                "a": _fvm("a", "", source="missing_fill"),
                "b": _fvm("b", "", source="missing_fill"),
            }
        )

        resultado = validator.validate(stc)

        assert "reprovado" in resultado["reason"].lower() or "gate" in resultado["reason"].lower()


# ── (c) blind_spots contam como missing ──────────────────────────────────────


class TestCompletenessBlindSpots:
    """Cenário (c): blind_spots com typing_not_captured contam como missing."""

    def test_blind_spot_typing_rebaixa_campo(self, validator):
        """Campo em field_values mas com blind_spot typing_not_captured → missing."""
        stc = _stc(
            field_values={
                "valor": _fvm("valor", "500"),  # aparentemente preenchido
                "nome": _fvm("nome", "Ana"),    # sem blind_spot
            },
            blind_spots=[
                {
                    "step": 3,
                    "pattern": "typing_not_captured",
                    "element": "input",
                    "label": "Valor",  # corresponde a chave "valor" após canonicalização
                    "gap_seconds": 5.0,
                    "resolution": "data-file",
                }
            ],
        )

        resultado = validator.validate(stc)

        # "valor" deve ser rebaixado para missing pelo blind_spot
        assert "valor" in resultado["missing_fields"]

    def test_blind_spot_sem_label_gera_chave_generica(self, validator):
        """Blind spot sem label gera chave genérica e conta como missing."""
        stc = _stc(
            field_values={
                "nome": _fvm("nome", "Ana"),
            },
            blind_spots=[
                {
                    "step": 7,
                    "pattern": "typing_not_captured",
                    "element": "input",
                    "label": "",  # sem label identificável
                    "gap_seconds": 8.0,
                    "resolution": "data-file",
                }
            ],
        )

        resultado = validator.validate(stc)

        # Chave genérica para step 7
        assert "campo_blind_spot_step_7" in resultado["missing_fields"]

    def test_blind_spots_count_reflete_total_de_blind_spots(self, validator):
        """blind_spots_count reflete o total de blind_spots no STC, independente do padrão."""
        stc = _stc(
            field_values={"a": _fvm("a", "x")},
            blind_spots=[
                {"step": 1, "pattern": "typing_not_captured", "label": "A", "gap_seconds": 3},
                {"step": 2, "pattern": "long_gap", "gap_seconds": 15},
                {"step": 4, "pattern": "select_not_captured"},
            ],
        )

        resultado = validator.validate(stc)

        assert resultado["blind_spots_count"] == 3

    def test_long_gap_blind_spot_nao_conta_como_missing(self, validator):
        """Blind spot com padrão 'long_gap' não conta como campo ausente."""
        stc = _stc(
            field_values={"nome": _fvm("nome", "Carlos")},
            blind_spots=[
                {"step": 5, "pattern": "long_gap", "gap_seconds": 12},
            ],
        )

        resultado = validator.validate(stc)

        # long_gap não é missing — score permanece 1.0
        assert resultado["completeness_score"] == 1.0
        assert resultado["passes_gate"] is True

    def test_select_not_captured_conta_como_missing(self, validator):
        """Blind spot select_not_captured também conta como missing."""
        stc = _stc(
            field_values={"nome": _fvm("nome", "Maria")},
            blind_spots=[
                {
                    "step": 2,
                    "pattern": "select_not_captured",
                    "label": "Estado",
                    "resolution": "data-file",
                }
            ],
        )

        resultado = validator.validate(stc)

        assert "estado" in resultado["missing_fields"]
        assert resultado["passes_gate"] is False  # 1 de 2 = 50%


# ── (d) Boundary exato de 0.70 ────────────────────────────────────────────────


class TestCompletenessThresholdBoundary:
    """Cenário (d): score exato de 0.70 deve aprovar o gate."""

    def test_score_exato_0_70_aprova_gate(self, validator):
        """Score exatamente 0.70 (7 de 10) → passes_gate=True."""
        field_values = {}
        # 7 campos preenchidos
        for i in range(7):
            field_values[f"campo_{i}"] = _fvm(f"campo_{i}", f"valor_{i}")
        # 3 campos ausentes
        for i in range(7, 10):
            field_values[f"campo_{i}"] = _fvm(f"campo_{i}", "", source="missing_fill")

        stc = _stc(field_values=field_values)

        resultado = validator.validate(stc)

        assert resultado["completeness_score"] == pytest.approx(0.70, abs=1e-4)
        assert resultado["passes_gate"] is True

    def test_score_abaixo_0_70_reprova_gate(self, validator):
        """Score abaixo de 0.70 (6 de 10) → passes_gate=False."""
        field_values = {}
        # 6 campos preenchidos
        for i in range(6):
            field_values[f"campo_{i}"] = _fvm(f"campo_{i}", f"valor_{i}")
        # 4 campos ausentes
        for i in range(6, 10):
            field_values[f"campo_{i}"] = _fvm(f"campo_{i}", "", source="missing_fill")

        stc = _stc(field_values=field_values)

        resultado = validator.validate(stc)

        assert resultado["completeness_score"] == pytest.approx(0.60, abs=1e-4)
        assert resultado["passes_gate"] is False

    def test_score_acima_0_70_aprova_gate(self, validator):
        """Score acima de 0.70 (8 de 10) → passes_gate=True."""
        field_values = {}
        for i in range(8):
            field_values[f"campo_{i}"] = _fvm(f"campo_{i}", f"valor_{i}")
        for i in range(8, 10):
            field_values[f"campo_{i}"] = _fvm(f"campo_{i}", "", source="missing_fill")

        stc = _stc(field_values=field_values)

        resultado = validator.validate(stc)

        assert resultado["passes_gate"] is True
        assert resultado["completeness_score"] >= 0.70


# ── (e) SemanticTestCase sem steps ────────────────────────────────────────────


class TestCompletenessEmptySTC:
    """Cenário (e): SemanticTestCase sem steps — score 1.0 por vacuidade."""

    def test_stc_vazio_score_um(self, validator):
        """STC sem steps e sem field_values → score 1.0 por vacuidade."""
        stc = SemanticTestCase(
            test_id="tc-vazio",
            source_recording_id="rec-vazio",
        )

        resultado = validator.validate(stc)

        assert resultado["completeness_score"] == 1.0

    def test_stc_vazio_passes_gate(self, validator):
        """STC sem campo esperado → passes_gate=True."""
        stc = SemanticTestCase(
            test_id="tc-vazio",
            source_recording_id="rec-vazio",
        )

        resultado = validator.validate(stc)

        assert resultado["passes_gate"] is True

    def test_stc_vazio_sem_missing_fields(self, validator):
        """STC vazio → missing_fields=[]."""
        stc = SemanticTestCase(
            test_id="tc-vazio",
            source_recording_id="rec-vazio",
        )

        resultado = validator.validate(stc)

        assert resultado["missing_fields"] == []

    def test_stc_vazio_blind_spots_count_zero(self, validator):
        """STC sem blind_spots → blind_spots_count=0."""
        stc = SemanticTestCase(
            test_id="tc-vazio",
            source_recording_id="rec-vazio",
        )

        resultado = validator.validate(stc)

        assert resultado["blind_spots_count"] == 0

    def test_stc_vazio_reason_menciona_vacuidade(self, validator):
        """reason para STC vazio menciona ausência de campos esperados."""
        stc = SemanticTestCase(
            test_id="tc-vazio",
            source_recording_id="rec-vazio",
        )

        resultado = validator.validate(stc)

        assert "vacuidade" in resultado["reason"].lower() or "nenhum" in resultado["reason"].lower()
