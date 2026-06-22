import pytest
import json
from pathlib import Path
from playwright.sync_api import Page
from playwright.sync_api import expect

class Ola:
    DATA_PATH = Path(__file__).with_suffix('.data.json')

    @pytest.fixture(autouse=True)
    def setup(self, page: Page):
        self.page = page
        with open(self.DATA_PATH) as f:
            self.data = json.load(f)

    def test_run(self, page: Page):
        """ Passo 1: click"""
        ' Seletores: fieldset:has-text("Esta é uma simulação para aquisição de imóvel residencial (novo ou usado) ou par") | fieldset:has-text("1\n\t\t\t\t\t\t\n\t\t\t\t\t\t\tDados iniciais\n\t\t\t\t\t\t\tInforme qual é a sua opção de financiamento ou do empréstimo com garantia de imóve") | //fieldset[contains(text(), "1\n\t\t\t\t\t\t\n\t\t\t\t\t\t\tDados iniciais\n\t\t\t\t\t\t\tInforme qual é a sua opção de financiamento ou do empréstimo com garantia de imóve")]'
        page.goto('https://www8.caixa.gov.br/siopiinternet-web/simulaOperacaoInternet.do?method=inicializarCasoUso')