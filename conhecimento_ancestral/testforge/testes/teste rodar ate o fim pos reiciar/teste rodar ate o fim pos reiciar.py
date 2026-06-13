import pytest
import json
from pathlib import Path
from playwright.sync_api import Page
from playwright.sync_api import expect

class Teste Rodar Ate O Fim Pos Reiciar:
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
        ' Passo 2: click'
        ' Seletores: #pessoaF | input[name="pessoa"] | //input[@*]'
        page.click('#pessoaF')
        ' Passo 3: fill'
        ' Seletores: #tipoImovel_input | input:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?") | input:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?")'
        page.fill('#tipoImovel_input', self.data['steps'][2]['value'])
        ' Passo 4: click'
        ' Seletores: #tipoImovel_input | input:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?") | input.ui-autocomplete-input.ui-widget.ui-widget-content.ui-corner-left.combobox'
        page.click('#tipoImovel_input')
        ' Passo 5: click'
        ' Seletores: a:has-text("Residencial") | //a[contains(text(), "Residencial")] | //a[@*]'
        page.click('a:has-text("Residencial")')
        ' Passo 6: fill'
        ' Seletores: #tipoImovel_input | input:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?") | input:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?")'
        page.fill('#tipoImovel_input', self.data['steps'][5]['value'])
        ' Passo 7: fill'
        ' Seletores: #grupoTipoFinanciamento_input | input:has-text("Selecione a opção de Financiamento/Empréstimo") | input:has-text("Selecione a opção de Financiamento/Empréstimo")'
        page.fill('#grupoTipoFinanciamento_input', self.data['steps'][6]['value'])
        ' Passo 8: click'
        ' Seletores: #grupoTipoFinanciamento_input | input:has-text("Selecione a opção de Financiamento/Empréstimo") | input.ui-autocomplete-input.ui-widget.ui-widget-content.ui-corner-left.combobox'
        page.click('#grupoTipoFinanciamento_input')
        ' Passo 9: fill'
        ' Seletores: #tipoImovel_input | input:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?") | input:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?")'
        page.fill('#tipoImovel_input', self.data['steps'][8]['value'])
        ' Passo 10: click'
        ' Seletores: a:has-text("Aquisição de Imóvel Usado") | //a[contains(text(), "Aquisição de Imóvel Usado")] | //a[@*]'
        page.click('a:has-text("Aquisição de Imóvel Usado")')
        ' Passo 11: fill'
        ' Seletores: #grupoTipoFinanciamento_input | input:has-text("Selecione a opção de Financiamento/Empréstimo") | input:has-text("Selecione a opção de Financiamento/Empréstimo")'
        page.fill('#grupoTipoFinanciamento_input', self.data['steps'][10]['value'])
        ' Passo 12: click'
        ' Seletores: #valorImovel | input[name="valorImovel"] | input:has-text("Valor aproximado do imóvel?")'
        page.click('#valorImovel')
        ' Passo 13: fill'
        ' Seletores: #valorImovel | input[name="valorImovel"] | input:has-text("Valor aproximado do imóvel?")'
        page.fill('#valorImovel', self.data['steps'][12]['value'])
        ' Passo 14: fill'
        ' Seletores: #valorImovel | input[name="valorImovel"] | input:has-text("Valor aproximado do imóvel?")'
        page.fill('#valorImovel', self.data['steps'][13]['value'])
        ' Passo 15: fill'
        ' Seletores: #grupoTipoFinanciamento_input | input:has-text("Selecione a opção de Financiamento/Empréstimo") | input:has-text("Selecione a opção de Financiamento/Empréstimo")'
        page.fill('#grupoTipoFinanciamento_input', self.data['steps'][14]['value'])
        ' Passo 16: fill'
        ' Seletores: #valorImovel | input[name="valorImovel"] | input:has-text("Valor aproximado do imóvel?")'
        page.fill('#valorImovel', self.data['steps'][15]['value'])
        ' Passo 17: fill'
        ' Seletores: #uf_input | input:has-text("Em qual cidade está localizado o imóvel?") | input:has-text("Em qual cidade está localizado o imóvel?")'
        page.fill('#uf_input', self.data['steps'][16]['value'])
        ' Passo 18: click'
        ' Seletores: #uf_input | input:has-text("Em qual cidade está localizado o imóvel?") | input.ui-autocomplete-input.ui-widget.ui-widget-content.ui-corner-left.combobox'
        page.click('#uf_input')
        ' Passo 19: click'
        ' Seletores: a:has-text("DF") | //a[contains(text(), "DF")] | //a[@*]'
        page.click('a:has-text("DF")')
        ' Passo 20: fill'
        ' Seletores: #uf_input | input:has-text("Em qual cidade está localizado o imóvel?") | input:has-text("Em qual cidade está localizado o imóvel?")'
        page.fill('#uf_input', self.data['steps'][19]['value'])
        ' Passo 21: fill'
        ' Seletores: #cidade_input | input:has-text("Em qual cidade está localizado o imóvel?") | input:has-text("Em qual cidade está localizado o imóvel?")'
        page.fill('#cidade_input', self.data['steps'][20]['value'])
        ' Passo 22: click'
        ' Seletores: #cidade_input | input:has-text("Em qual cidade está localizado o imóvel?") | input.ui-autocomplete-input.ui-widget.ui-widget-content.ui-corner-left.combobox'
        page.click('#cidade_input')
        ' Passo 23: click'
        ' Seletores: a:has-text("BRASILIA") | //a[contains(text(), "BRASILIA")] | //a[@*]'
        page.click('a:has-text("BRASILIA")')
        ' Passo 24: fill'
        ' Seletores: #cidade_input | input:has-text("Em qual cidade está localizado o imóvel?") | input:has-text("Em qual cidade está localizado o imóvel?")'
        page.fill('#cidade_input', self.data['steps'][23]['value'])
        ' Passo 25: click'
        ' Seletores: #btn_next1 | div:has-text("Próxima etapa") | //div[contains(text(), "Próxima etapa")]'
        page.click('#btn_next1')
        ' Passo 26: fill'
        ' Seletores: #grupoTipoFinanciamento_input | input:has-text("Selecione a opção de Financiamento/Empréstimo") | input:has-text("Selecione a opção de Financiamento/Empréstimo")'
        page.fill('#grupoTipoFinanciamento_input', self.data['steps'][25]['value'])
        ' Passo 27: assert'
        ' Seletores: label:has-text("Qual é o seu CPF?") | label:has-text("Qual é o seu CPF?") | //label[contains(text(), "Qual é o seu CPF?")]'
        expect(page.locator('label:has-text("Qual é o seu CPF?")')).to_contain_text('Qual é o seu CPF?')