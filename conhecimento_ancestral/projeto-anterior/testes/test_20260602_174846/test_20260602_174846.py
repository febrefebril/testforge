import pytest
import json
from pathlib import Path
from playwright.sync_api import Page
from playwright.sync_api import expect

class Test20260602174846:
    DATA_PATH = Path(__file__).with_suffix('.data.json')

    @pytest.fixture(autouse=True)
    def setup(self, page: Page):
        self.page = page
        with open(self.DATA_PATH) as f:
            self.data = json.load(f)

    def test_run(self, page: Page):
        """ Passo 1: click"""
        ' Seletores: #pessoaF | input[name="pessoa"] | //input[@*]'
        page.goto('https://www8.caixa.gov.br/siopiinternet-web/simulaOperacaoInternet.do?method=inicializarCasoUso')
        ' Passo 2: select'
        ' Seletores: #pessoaF | input[name="pessoa"] | input:has-text("checked")'
        page.select_option('#pessoaF', label='checked')
        ' Passo 3: fill'
        ' Seletores: #pessoaF | input[name="pessoa"] | //input[@*]'
        page.fill('#pessoaF', self.data['steps'][2]['value'])
        ' Passo 4: click'
        ' Seletores: label:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?") | label:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?") | //label[contains(text(), "Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?")]'
        page.click('label:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?")')
        ' Passo 5: click'
        ' Seletores: button:has-text("Selecione a opção de Financiamento/Empréstimo") | button.button_combobox.ui-button.ui-widget.ui-state-default.ui-button-icon-only.ui-corner-right.ui-button-icon.ui-state-hover.ui-state-focus | //button[@*]'
        page.click('button:has-text("Selecione a opção de Financiamento/Empréstimo")')
        ' Passo 6: click'
        ' Seletores: span.ui-button-icon-primary.ui-icon.ui-icon-triangle-1-s | //span[@*]'
        page.click('span.ui-button-icon-primary.ui-icon.ui-icon-triangle-1-s')
        ' Passo 7: click'
        ' Seletores: span.ui-button-icon-primary.ui-icon.ui-icon-triangle-1-s | //span[@*]'
        page.click('span.ui-button-icon-primary.ui-icon.ui-icon-triangle-1-s')
        ' Passo 8: click'
        ' Seletores: label:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?") | label:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?") | //label[contains(text(), "Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?")]'
        page.click('label:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?")')
        ' Passo 9: click'
        ' Seletores: #pessoaJ | input[name="pessoa"] | //input[@*]'
        page.click('#pessoaJ')
        ' Passo 10: select'
        ' Seletores: #pessoaJ | input[name="pessoa"] | input:has-text("checked")'
        page.select_option('#pessoaJ', label='checked')
        ' Passo 11: fill'
        ' Seletores: #pessoaJ | input[name="pessoa"] | //input[@*]'
        page.fill('#pessoaJ', self.data['steps'][10]['value'])
        ' Passo 12: click'
        ' Seletores: fieldset:has-text("Esta é uma simulação para aquisição de imóvel residencial (novo ou usado) ou par") | fieldset:has-text("1\n\t\t\t\t\t\t\n\t\t\t\t\t\t\tDados iniciais\n\t\t\t\t\t\t\tInforme qual é a sua opção de financiamento ou do empréstimo com garantia de imóve") | //fieldset[contains(text(), "1\n\t\t\t\t\t\t\n\t\t\t\t\t\t\tDados iniciais\n\t\t\t\t\t\t\tInforme qual é a sua opção de financiamento ou do empréstimo com garantia de imóve")]'
        page.click('fieldset:has-text("Esta é uma simulação para aquisição de imóvel residencial (novo ou usado) ou par")')
        ' Passo 13: click'
        ' Seletores: #pessoaF | input[name="pessoa"] | //input[@*]'
        page.click('#pessoaF')
        ' Passo 14: select'
        ' Seletores: #pessoaF | input[name="pessoa"] | input:has-text("checked")'
        page.select_option('#pessoaF', label='checked')
        ' Passo 15: fill'
        ' Seletores: #pessoaF | input[name="pessoa"] | //input[@*]'
        page.fill('#pessoaF', self.data['steps'][14]['value'])
        ' Passo 16: click'
        ' Seletores: span.ui-button-icon-primary.ui-icon.ui-icon-triangle-1-s | //span[@*]'
        page.click('span.ui-button-icon-primary.ui-icon.ui-icon-triangle-1-s')
        ' Passo 17: click'
        ' Seletores: #ui-id-26 > a:nth-of-type(1) | a:has-text("Informe a categoria") | //a[contains(text(), "Informe a categoria")]'
        page.click('#ui-id-26 > a:nth-of-type(1)')
        ' Passo 18: click'
        ' Seletores: label:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?") | label:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?") | //label[contains(text(), "Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?")]'
        page.click('label:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?")')
        ' Passo 19: click'
        ' Seletores: label:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?") | label:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?") | //label[contains(text(), "Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?")]'
        page.click('label:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?")')
        ' Passo 20: click'
        ' Seletores: label:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?") | label:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?") | //label[contains(text(), "Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?")]'
        page.click('label:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?")')
        ' Passo 21: click'
        ' Seletores: label:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?") | label:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?") | //label[contains(text(), "Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?")]'
        page.click('label:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?")')