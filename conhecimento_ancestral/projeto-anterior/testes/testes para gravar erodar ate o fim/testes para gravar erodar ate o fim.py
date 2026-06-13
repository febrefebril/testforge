import pytest
import json
from pathlib import Path
from playwright.sync_api import Page
from playwright.sync_api import expect

class Testes Para Gravar Erodar Ate O Fim:
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
        ' Seletores: label:has-text("Física") | label:has-text("Física") | //label[contains(text(), "Física")]'
        page.click('label:has-text("Física")')
        ' Passo 3: select'
        ' Seletores: #pessoaF | input[name="pessoa"] | input:has-text("checked")'
        page.select_option('#pessoaF', label='checked')
        ' Passo 4: fill'
        ' Seletores: #pessoaF | input[name="pessoa"] | //input[@*]'
        page.fill('#pessoaF', self.data['steps'][3]['value'])
        ' Passo 5: click'
        ' Seletores: #tipoImovel_input | input:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?") | input.ui-autocomplete-input.ui-widget.ui-widget-content.ui-corner-left.combobox'
        page.click('#tipoImovel_input')
        ' Passo 6: click'
        ' Seletores: a:has-text("Residencial") | //a[contains(text(), "Residencial")] | //a[@*]'
        page.click('a:has-text("Residencial")')
        ' Passo 7: click'
        ' Seletores: #grupoTipoFinanciamento_input | input:has-text("Selecione a opção de Financiamento/Empréstimo") | input.ui-autocomplete-input.ui-widget.ui-widget-content.ui-corner-left.combobox'
        page.click('#grupoTipoFinanciamento_input')
        ' Passo 8: click'
        ' Seletores: a:has-text("Aquisição de Imóvel Novo") | //a[contains(text(), "Aquisição de Imóvel Novo")] | //a[@*]'
        page.click('a:has-text("Aquisição de Imóvel Novo")')
        ' Passo 9: click'
        ' Seletores: #valorImovel | input[name="valorImovel"] | input:has-text("Valor aproximado do imóvel?")'
        page.click('#valorImovel')
        ' Passo 10: click'
        ' Seletores: #uf_input | input:has-text("Em qual cidade está localizado o imóvel?") | input.ui-autocomplete-input.ui-widget.ui-widget-content.ui-corner-left.combobox'
        page.click('#uf_input')
        ' Passo 11: click'
        ' Seletores: a:has-text("DF") | //a[contains(text(), "DF")] | //a[@*]'
        page.click('a:has-text("DF")')
        ' Passo 12: click'
        ' Seletores: #cidade_input | input:has-text("Em qual cidade está localizado o imóvel?") | input.ui-autocomplete-input.ui-widget.ui-widget-content.ui-corner-left.combobox'
        page.click('#cidade_input')
        ' Passo 13: click'
        ' Seletores: a:has-text("BRASILIA") | //a[contains(text(), "BRASILIA")] | //a[@*]'
        page.click('a:has-text("BRASILIA")')
        ' Passo 14: click'
        ' Seletores: #btn_next1 | div:has-text("Próxima etapa") | //div[contains(text(), "Próxima etapa")]'
        page.click('#btn_next1')
        ' Passo 15: click'
        ' Seletores: label:has-text("Qual é o seu CPF?") | label:has-text("Qual é o seu CPF?") | //label[contains(text(), "Qual é o seu CPF?")]'
        page.click('label:has-text("Qual é o seu CPF?")')
        ' Passo 16: click'
        ' Seletores: label:has-text("Qual é o seu CPF?") | label:has-text("Qual é o seu CPF?") | //label[contains(text(), "Qual é o seu CPF?")]'
        page.click('label:has-text("Qual é o seu CPF?")')
        ' Passo 17: click'
        ' Seletores: label:has-text("Qual é o seu CPF?") | label:has-text("Qual é o seu CPF?") | //label[contains(text(), "Qual é o seu CPF?")]'
        page.click('label:has-text("Qual é o seu CPF?")')
        ' Passo 18: click'
        ' Seletores: label:has-text("Qual é o seu CPF?") | label:has-text("Qual é o seu CPF?") | //label[contains(text(), "Qual é o seu CPF?")]'
        page.click('label:has-text("Qual é o seu CPF?")')
        ' Passo 19: click'
        ' Seletores: label:has-text("Qual é o seu CPF?") | label:has-text("Qual é o seu CPF?") | //label[contains(text(), "Qual é o seu CPF?")]'
        page.click('label:has-text("Qual é o seu CPF?")')
        ' Passo 20: assert'
        ' Seletores: label:has-text("Qual é o seu CPF?") | label:has-text("Qual é o seu CPF?") | //label[contains(text(), "Qual é o seu CPF?")]'
        expect(page.locator('label:has-text("Qual é o seu CPF?")')).to_contain_text('Qual é o seu CPF?')