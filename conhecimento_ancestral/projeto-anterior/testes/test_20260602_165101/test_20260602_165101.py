import pytest
import json
from pathlib import Path
from playwright.sync_api import Page
from playwright.sync_api import expect

class Test20260602165101:
    DATA_PATH = Path(__file__).with_suffix('.data.json')

    @pytest.fixture(autouse=True)
    def setup(self, page: Page):
        self.page = page
        with open(self.DATA_PATH) as f:
            self.data = json.load(f)

    def test_run(self, page: Page):
        """ Passo 1: click"""
        ' Seletores: h1:has-text("Simulador Crédito imobiliário CAIXA, Programa Minha Casa, Minha Vida e Empréstimo com Garantia de Imóvel") | //h1[contains(text(), "Simulador Crédito imobiliário CAIXA, Programa Minha Casa, Minha Vida e Empréstimo com Garantia de Imóvel")] | //h1[@*]'
        page.goto('https://www8.caixa.gov.br/siopiinternet-web/simulaOperacaoInternet.do?method=inicializarCasoUso')
        ' Passo 2: click'
        ' Seletores: html:has-text("var CONTEXTO_APP =\t\'/siopiinternet-web\';\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\tfunction combo() {\n\t\tjQuery(\\"sel") | //html[contains(text(), "var CONTEXTO_APP =\t\'/siopiinternet-web\';\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\tfunction combo() {\n\t\tjQuery(\\"sel")] | //html[@*]'
        page.click('html:has-text("var CONTEXTO_APP =\t\'/siopiinternet-web\';\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\tfunction combo() {\n\t\tjQuery(\\"sel")')
        ' Passo 3: click'
        ' Seletores: html:has-text("var CONTEXTO_APP =\t\'/siopiinternet-web\';\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\tfunction combo() {\n\t\tjQuery(\\"sel") | //html[contains(text(), "var CONTEXTO_APP =\t\'/siopiinternet-web\';\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\tfunction combo() {\n\t\tjQuery(\\"sel")] | //html[@*]'
        page.click('html:has-text("var CONTEXTO_APP =\t\'/siopiinternet-web\';\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\tfunction combo() {\n\t\tjQuery(\\"sel")')