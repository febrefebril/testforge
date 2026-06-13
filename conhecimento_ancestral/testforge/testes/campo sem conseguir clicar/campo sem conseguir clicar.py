import pytest
import json
from pathlib import Path
from playwright.sync_api import Page
from playwright.sync_api import expect

class Campo Sem Conseguir Clicar:
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
        ' Seletores: #tipoImovel_input | input:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?") | input.ui-autocomplete-input.ui-widget.ui-widget-content.ui-corner-left.combobox'
        page.click('#tipoImovel_input')
        ' Passo 5: click'
        ' Seletores: #ui-id-21 > a:nth-of-type(1) | a:has-text("Comercial") | //a[contains(text(), "Comercial")]'
        page.click('#ui-id-21 > a:nth-of-type(1)')
        ' Passo 6: click'
        ' Seletores: #grupoTipoFinanciamento_input | input:has-text("Selecione a opção de Financiamento/Empréstimo") | input.ui-autocomplete-input.ui-widget.ui-widget-content.ui-corner-left.combobox'
        page.click('#grupoTipoFinanciamento_input')
        ' Passo 7: click'
        ' Seletores: #ui-id-26 > a:nth-of-type(1) | a:has-text("Aquisição de Imóvel Usado") | //a[contains(text(), "Aquisição de Imóvel Usado")]'
        page.click('#ui-id-26 > a:nth-of-type(1)')
        ' Passo 8: click'
        ' Seletores: #valorImovel | input[name="valorImovel"] | input:has-text("Valor aproximado do imóvel?")'
        page.click('#valorImovel')
        ' Passo 9: click'
        ' Seletores: #uf_input | input:has-text("Em qual cidade está localizado o imóvel?") | input.ui-autocomplete-input.ui-widget.ui-widget-content.ui-corner-left.combobox'
        page.click('#uf_input')
        ' Passo 10: click'
        ' Seletores: #ui-id-37 > a:nth-of-type(1) | a:has-text("DF") | //a[contains(text(), "DF")]'
        page.click('#ui-id-37 > a:nth-of-type(1)')
        ' Passo 11: click'
        ' Seletores: #cidade_input | input:has-text("Em qual cidade está localizado o imóvel?") | input.ui-autocomplete-input.ui-widget.ui-widget-content.ui-corner-left.combobox'
        page.click('#cidade_input')
        ' Passo 12: click'
        ' Seletores: #ui-id-61 > a:nth-of-type(1) | a:has-text("BRASILIA") | //a[contains(text(), "BRASILIA")]'
        page.click('#ui-id-61 > a:nth-of-type(1)')
        ' Passo 13: click'
        ' Seletores: #btn_next1 | div:has-text("Próxima etapa") | //div[contains(text(), "Próxima etapa")]'
        page.click('#btn_next1')
        ' Passo 14: click'
        ' Seletores: #nuCpfCnpjInteressado | input[name="nuCpfCnpjInteressado"] | input:has-text("Qual é o seu CPF?")'
        page.click('#nuCpfCnpjInteressado')
        ' Passo 15: fill'
        ' Seletores: #nuCpfCnpjInteressado | input[name="nuCpfCnpjInteressado"] | input:has-text("Qual é o seu CPF?")'
        page.fill('#nuCpfCnpjInteressado', self.data['steps'][14]['value'])
        ' Passo 16: fill'
        ' Seletores: #nuCpfCnpjInteressado | input[name="nuCpfCnpjInteressado"] | input:has-text("Qual é o seu CPF?")'
        page.fill('#nuCpfCnpjInteressado', self.data['steps'][15]['value'])
        ' Passo 17: fill'
        ' Seletores: #nuCpfCnpjInteressado | input[name="nuCpfCnpjInteressado"] | input:has-text("Qual é o seu CPF?")'
        page.fill('#nuCpfCnpjInteressado', self.data['steps'][16]['value'])
        ' Passo 18: fill'
        ' Seletores: #nuCpfCnpjInteressado | input[name="nuCpfCnpjInteressado"] | input:has-text("Qual é o seu CPF?")'
        page.fill('#nuCpfCnpjInteressado', self.data['steps'][17]['value'])
        ' Passo 19: fill'
        ' Seletores: #nuCpfCnpjInteressado | input[name="nuCpfCnpjInteressado"] | input:has-text("Qual é o seu CPF?")'
        page.fill('#nuCpfCnpjInteressado', self.data['steps'][18]['value'])
        ' Passo 20: fill'
        ' Seletores: #nuCpfCnpjInteressado | input[name="nuCpfCnpjInteressado"] | input:has-text("Qual é o seu CPF?")'
        page.fill('#nuCpfCnpjInteressado', self.data['steps'][19]['value'])
        ' Passo 21: fill'
        ' Seletores: #nuTelefoneCelular | input[name="nuTelefoneCelular"] | input:has-text("Qual é o número do seu telefone celular?")'
        page.fill('#nuTelefoneCelular', self.data['steps'][20]['value'])
        ' Passo 22: fill'
        ' Seletores: #nuTelefoneCelular | input[name="nuTelefoneCelular"] | input:has-text("Qual é o número do seu telefone celular?")'
        page.fill('#nuTelefoneCelular', self.data['steps'][21]['value'])
        ' Passo 23: fill'
        ' Seletores: #nuTelefoneCelular | input[name="nuTelefoneCelular"] | input:has-text("Qual é o número do seu telefone celular?")'
        page.fill('#nuTelefoneCelular', self.data['steps'][22]['value'])
        ' Passo 24: fill'
        ' Seletores: #nuTelefoneCelular | input[name="nuTelefoneCelular"] | input:has-text("Qual é o número do seu telefone celular?")'
        page.fill('#nuTelefoneCelular', self.data['steps'][23]['value'])
        ' Passo 25: click'
        ' Seletores: ul:has-text("Qual é o seu CPF?") | ul:has-text("Qual é o seu CPF?\n\t\t\t\t\t\t\t\t\t\n\t\t\t\t\t\t\t\t\t\n\t\t\t\t\t\t\t\t\n\t\t\t\t\t\t\t\n\t\t\t\t\t\t\n\t\t\t\t\t\t\n\t\t\t\t\t\t\t\n\t\t\t\t\t\t\t\t\n\t\t\t\t\t\t\t\t\tQual é o número do seu te") | //ul[contains(text(), "Qual é o seu CPF?\n\t\t\t\t\t\t\t\t\t\n\t\t\t\t\t\t\t\t\t\n\t\t\t\t\t\t\t\t\n\t\t\t\t\t\t\t\n\t\t\t\t\t\t\n\t\t\t\t\t\t\n\t\t\t\t\t\t\t\n\t\t\t\t\t\t\t\t\n\t\t\t\t\t\t\t\t\tQual é o número do seu te")]'
        page.click('ul:has-text("Qual é o seu CPF?")')
        ' Passo 26: click'
        ' Seletores: #rendaFamiliarBruta | input[name="rendaFamiliarBruta"] | input:has-text("Renda bruta familiar mensal?")'
        page.click('#rendaFamiliarBruta')
        ' Passo 27: click'
        ' Seletores: #dataNascimento | input[name="dataNascimento"] | input:has-text("Data de nascimento do proponente?")'
        page.click('#dataNascimento')
        ' Passo 28: click'
        ' Seletores: #ui-datepicker-div > table:nth-of-type(1) > tbody:nth-of-type(1) > tr:nth-of-type(1) > td:nth-of-type(3) > a:nth-of-type(1) | a[href="#"] | a:has-text("1")'
        page.click('#ui-datepicker-div > table:nth-of-type(1) > tbody:nth-of-type(1) > tr:nth-of-type(1) > td:nth-of-type(3) > a:nth-of-type(1)')