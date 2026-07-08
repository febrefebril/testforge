"""REC-59 REC-86: detect and alert when recording in production domain."""
import pytest


@pytest.mark.unit
class TestProductionDetectorWhenProdDomainThenAlerts:
    def test_prod_domain_detected(self):
        from testforge.recorder.production_detector import is_production
        assert is_production("https://simulador.banco.example.com/home") is True

    def test_des_domain_not_prod(self):
        from testforge.recorder.production_detector import is_production
        assert is_production("https://plataforma-des.banco.example.com/inicio") is False

    def test_tqs_not_prod(self):
        from testforge.recorder.production_detector import is_production
        assert is_production("https://simulador-tqs.apps.nprd.example.com/") is False

    def test_localhost_not_prod(self):
        from testforge.recorder.production_detector import is_production
        assert is_production("http://localhost:8765/") is False

    def test_alert_prints_when_prod(self, capsys):
        from testforge.recorder.production_detector import alert_if_production
        alert_if_production("https://simulador.banco.example.com/")
        out = capsys.readouterr().out
        assert "PRODUCAO" in out

    def test_alert_silent_when_not_prod(self, capsys):
        from testforge.recorder.production_detector import alert_if_production
        alert_if_production("https://plataforma-des.banco.example.com/")
        out = capsys.readouterr().out
        assert out == ""
