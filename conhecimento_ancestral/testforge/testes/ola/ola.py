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
        ' Seletores: #grupoTipoFinanciamento_input | input:has-text("Selecione a opção de Financiamento/Empréstimo") | input.ui-autocomplete-input.ui-widget.ui-widget-content.ui-corner-left.combobox'
        page.goto('https://www8.caixa.gov.br/siopiinternet-web/simulaOperacaoInternet.do?method=inicializarCasoUso')
        ' Passo 2: click'
        ' Seletores: #grupoTipoFinanciamento_input | input:has-text("Selecione a opção de Financiamento/Empréstimo") | input.ui-autocomplete-input.ui-widget.ui-widget-content.ui-corner-left.combobox'
        page.click('#grupoTipoFinanciamento_input')
        ' Passo 3: click'
        ' Seletores: #tipoImovel_input | input:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?") | input.ui-autocomplete-input.ui-widget.ui-widget-content.ui-corner-left.combobox'
        page.click('#tipoImovel_input')
        ' Passo 4: click'
        ' Seletores: #pessoaF | input[name="pessoa"] | //input[@*]'
        page.click('#pessoaF')
        ' Passo 5: select'
        ' Seletores: #pessoaF | input[name="pessoa"] | input:has-text("checked")'
        page.select_option('#pessoaF', label='checked')
        ' Passo 6: fill'
        ' Seletores: #pessoaF | input[name="pessoa"] | //input[@*]'
        page.fill('#pessoaF', self.data['steps'][5]['value'])
        ' Passo 7: click'
        ' Seletores: #tipoImovel_input | input:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?") | input.ui-autocomplete-input.ui-widget.ui-widget-content.ui-corner-left.combobox'
        page.click('#tipoImovel_input')
        ' Passo 8: click'
        ' Seletores: #tipoImovel_input | input:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?") | input.ui-autocomplete-input.ui-widget.ui-widget-content.ui-corner-left.combobox'
        page.click('#tipoImovel_input')