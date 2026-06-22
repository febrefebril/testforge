import pytest
import json
from pathlib import Path
from playwright.sync_api import Page
from playwright.sync_api import expect

class Test20260602175359:
    DATA_PATH = Path(__file__).with_suffix('.data.json')

    @pytest.fixture(autouse=True)
    def setup(self, page: Page):
        self.page = page
        with open(self.DATA_PATH) as f:
            self.data = json.load(f)

    def test_run(self, page: Page):
        """ Passo 1: click"""
        ' Seletores: p:has-text("Início › Produtos para você › Habitação ›") | //p[contains(text(), "Início › Produtos para você › Habitação ›")] | p.breadcrumb.noprint'
        page.goto('https://www8.caixa.gov.br/siopiinternet-web/simulaOperacaoInternet.do?method=inicializarCasoUso')
        ' Passo 2: click'
        ' Seletores: #pessoaF | input[name="pessoa"] | //input[@*]'
        page.click('#pessoaF')
        ' Passo 3: select'
        ' Seletores: #pessoaF | input[name="pessoa"] | input:has-text("checked")'
        page.select_option('#pessoaF', label='checked')
        ' Passo 4: fill'
        ' Seletores: #pessoaF | input[name="pessoa"] | //input[@*]'
        page.fill('#pessoaF', self.data['steps'][3]['value'])
        ' Passo 5: click'
        ' Seletores: button:has-text("Selecione a opção de Financiamento/Empréstimo") | button.button_combobox.ui-button.ui-widget.ui-state-default.ui-button-icon-only.ui-corner-right.ui-button-icon.ui-state-hover.ui-state-focus | //button[@*]'
        page.click('button:has-text("Selecione a opção de Financiamento/Empréstimo")')
        ' Passo 6: click'
        ' Seletores: label:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?") | label:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?") | //label[contains(text(), "Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?")]'
        page.click('label:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?")')
        ' Passo 7: click'
        ' Seletores: li:has-text("Esta é uma simulação para aquisição de imóvel residencial (novo ou usado) ou par") | li:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?\n\t\t\t\t\t\t\t\n\t\t\t\t\t\t\t\t\n\nInforme o tipo de financi") | //li[contains(text(), "Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?\n\t\t\t\t\t\t\t\n\t\t\t\t\t\t\t\t\n\nInforme o tipo de financi")]'
        page.click('li:has-text("Esta é uma simulação para aquisição de imóvel residencial (novo ou usado) ou par")')