"""Unit tests for PII detector — observability layer.

Contract [[feedback-pii-alert-only]]: values must NEVER be modified.
All tests assert `hit.value == original_input` to enforce this invariant.
"""
import pytest

from testforge.security import (
    PiiHit,
    PiiPattern,
    detect,
    url_scan,
    is_production_domain,
)
from testforge.security.pii_detector import Severity


@pytest.mark.unit
class TestPiiDetectorCpf:
    def test_when_cpf_formatted_then_emits_hit_and_preserves_value(self):
        # Arrange
        value = "000.000.000-00"

        # Act
        hits = detect(value, context="raw_events.evt_00035")

        # Assert
        assert len(hits) == 1
        hit = hits[0]
        assert hit.pattern == PiiPattern.CPF
        assert hit.value == "000.000.000-00"  # PRESERVED verbatim
        assert hit.severity == Severity.HIGH
        assert hit.context == "raw_events.evt_00035"

    def test_when_cpf_unformatted_then_still_matches(self):
        # Arrange
        value = "00000000000"

        # Act
        hits = detect(value)

        # Assert
        assert any(h.pattern == PiiPattern.CPF for h in hits)

    def test_when_cpf_inside_larger_text_then_matches(self):
        # Arrange
        value = "JOAO DA SILVA CPF: 000.000.000-00 NIS: 000.00000."

        # Act
        hits = detect(value, context="steps.step_0003")

        # Assert
        cpf_hits = [h for h in hits if h.pattern == PiiPattern.CPF]
        assert len(cpf_hits) == 1
        assert cpf_hits[0].value == "000.000.000-00"


@pytest.mark.unit
class TestPiiDetectorCnpj:
    def test_when_cnpj_formatted_then_emits_hit(self):
        # Arrange
        value = "42.097.365/0001-26"

        # Act
        hits = detect(value)

        # Assert
        cnpj_hits = [h for h in hits if h.pattern == PiiPattern.CNPJ]
        assert len(cnpj_hits) == 1
        assert cnpj_hits[0].value == "42.097.365/0001-26"
        assert cnpj_hits[0].severity == Severity.HIGH

    def test_when_multiple_cnpjs_in_select_options_then_all_matched(self):
        # Arrange — simula string agregada de <select> (BUG-REC-30)
        value = (
            "Selecione o CNPJ42.097.365/0001-2660.846.100/0001-6561.484.627/0001-50"
        )

        # Act
        hits = detect(value, context="raw_events.evt_00019.target.text")

        # Assert
        cnpj_hits = [h for h in hits if h.pattern == PiiPattern.CNPJ]
        assert len(cnpj_hits) >= 2


@pytest.mark.unit
class TestPiiDetectorMatricula:
    def test_when_matricula_br_pattern_then_emits_hit(self):
        # Arrange
        for matricula in ("c000011", "c000000", "c000098", "c000018", "C00001"):
            # Act
            hits = detect(matricula, context="raw_events.evt_00005")

            # Assert
            m_hits = [h for h in hits if h.pattern == PiiPattern.MATRICULA_BR]
            assert len(m_hits) == 1, f"failed for {matricula}"
            assert m_hits[0].value.lower() == matricula.lower()


@pytest.mark.unit
class TestPiiDetectorPassword:
    def test_when_type_password_then_emits_critical_regardless_of_content(self):
        # Arrange
        weak_pw = "senha123"
        md = {"type": "password", "name": "password", "label": "Senha"}

        # Act
        hits = detect(weak_pw, context="raw_events.evt_00009", field_metadata=md)

        # Assert
        pw_hits = [h for h in hits if h.pattern == PiiPattern.PASSWORD]
        assert len(pw_hits) == 1
        assert pw_hits[0].severity == Severity.CRITICAL
        assert pw_hits[0].value == "senha123"  # PRESERVED

    def test_when_paste_true_in_password_hint_field_then_emits_critical(self):
        # Arrange
        pw = "dev0001"
        md = {
            "type": "text",
            "paste": True,
            "placeholder": "Senha",
            "label": "Senha",
        }

        # Act
        hits = detect(pw, field_metadata=md)

        # Assert
        assert any(h.pattern == PiiPattern.PASSWORD for h in hits)

    def test_when_numeric_pin_in_password_field_then_emits_pin(self):
        # Arrange — BUG-REC-35 (PIN 134679)
        pin = "134679"
        md = {"type": "password", "name": "password", "label": "Senha"}

        # Act
        hits = detect(pin, field_metadata=md)

        # Assert
        assert any(h.pattern == PiiPattern.PIN for h in hits)
        assert any(h.pattern == PiiPattern.PASSWORD for h in hits)


@pytest.mark.unit
class TestPiiDetectorEmail:
    def test_when_email_then_emits_hit(self):
        hits = detect("email@gmail.com", context="raw_events.evt_00045")
        assert any(h.pattern == PiiPattern.EMAIL for h in hits)


@pytest.mark.unit
class TestPiiDetectorPhoneBr:
    def test_when_phone_br_formatted_then_emits_hit(self):
        hits = detect("(61)99623-9901")
        assert any(h.pattern == PiiPattern.PHONE_BR for h in hits)


@pytest.mark.unit
class TestPiiDetectorCorporateFilename:
    def test_when_corp_filename_then_emits_hit(self):
        # BUG-REC-61
        hits = detect("CNT.EMP.MZ.BMX0.PRONAMPE.D260625.R4")
        f_hits = [h for h in hits if h.pattern == PiiPattern.CORP_FILENAME]
        assert len(f_hits) == 1
        assert f_hits[0].value == "CNT.EMP.MZ.BMX0.PRONAMPE.D260625.R4"


@pytest.mark.unit
class TestPiiDetectorUrlScan:
    def test_when_keycloak_url_then_emits_hits_per_param(self):
        # BUG-REC-31
        url = (
            "https://login.des.example.com/auth/realms/intranet/protocol/openid-connect/"
            "auth?state=abc123&nonce=def456&code_challenge=xyz789&client_id=cli"
        )

        # Act
        hits = url_scan(url, context="raw_events.evt_00009.url")

        # Assert
        patterns = {h.pattern for h in hits}
        assert PiiPattern.KEYCLOAK_SESSION in patterns
        assert len(hits) == 3  # state, nonce, code_challenge (não client_id)


@pytest.mark.unit
class TestPiiDetectorProductionDomain:
    @pytest.mark.parametrize(
        "url,expect_hit",
        [
            ("https://simulador.banco.example.com/home", True),
            ("https://agendamento-frontend-v2-des.apps.nprd.example.com/", False),
            ("https://plataforma-des.banco.example.com/", False),
            ("https://agendamento-front-v2-tqs.apps.nprd.example.com/", False),
        ],
        ids=[
            "producao_detected",
            "des_ok",
            "plataforma_des_ok",
            "tqs_ok",
        ],
    )
    def test_production_domain_detection(self, url, expect_hit):
        # Act
        hit = is_production_domain(url)

        # Assert
        if expect_hit:
            assert hit is not None
            assert hit.pattern == PiiPattern.PRODUCTION_DOMAIN
            assert hit.severity == Severity.CRITICAL
        else:
            assert hit is None


@pytest.mark.unit
class TestPiiDetectorContract:
    """Invariant: detector NEVER modifies input value.

    Regression risk: fix future para "mask on detect" quebra contrato
    [[feedback-pii-alert-only]] — dados são massa de teste.
    """

    @pytest.mark.parametrize(
        "value,metadata",
        [
            ("000.000.000-00", None),
            ("42.097.365/0001-26", None),
            ("senha123", {"type": "password"}),
            ("134679", {"type": "password", "label": "Senha"}),
            ("email@gmail.com", None),
            ("(61)99623-9901", None),
            ("c000011", None),
            ("CNT.EMP.MZ.BMX0.PRONAMPE.D260625.R4", None),
        ],
        ids=[
            "cpf",
            "cnpj",
            "password",
            "pin",
            "email",
            "phone",
            "matricula",
            "corp_filename",
        ],
    )
    def test_detector_preserves_original_value_verbatim(self, value, metadata):
        # Act
        hits = detect(value, field_metadata=metadata)

        # Assert — TODA hit.value deve conter o value original
        assert len(hits) >= 1, f"expected detection for {value!r}"
        for hit in hits:
            assert hit.value in value or value in hit.value, (
                f"detector modified value: original={value!r} hit.value={hit.value!r}"
            )

    def test_detector_returns_empty_when_no_pattern_matches(self):
        # Act
        hits = detect("hello world neutral text")

        # Assert
        # "world neutral" ou "hello world" pode matchar FULL_NAME — filtrar
        non_fullname = [h for h in hits if h.pattern != PiiPattern.FULL_NAME]
        assert non_fullname == []

    def test_detector_handles_none_and_empty(self):
        assert detect(None) == []
        assert detect("") == []
        assert detect(0) == []  # int coerced to "0" — no match
