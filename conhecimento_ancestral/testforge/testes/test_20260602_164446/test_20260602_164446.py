import pytest
import json
from pathlib import Path
from playwright.sync_api import Page
from playwright.sync_api import expect

class Test20260602164446:
    DATA_PATH = Path(__file__).with_suffix('.data.json')

    @pytest.fixture(autouse=True)
    def setup(self, page: Page):
        self.page = page
        with open(self.DATA_PATH) as f:
            self.data = json.load(f)

    def test_run(self, page: Page):
        """ Passo 1: click"""
        ' Seletores: div:nth-of-type(1) > div:nth-of-type(2) > div:nth-of-type(2) > img:nth-of-type(1) | //img[@*]'
        page.goto('https://www8.caixa.gov.br/siopiinternet-web/simulaOperacaoInternet.do?method=inicializarCasoUso')
        ' Passo 2: click'
        ' Seletores: fieldset:has-text("1\n\t\t\t\t\t\t\n\t\t\t\t\t\t\tDados iniciais\n\t\t\t\t\t\t\tInforme qual é a sua opção de financiamento ou do empréstimo com garantia de imóve") | //fieldset[contains(text(), "1\n\t\t\t\t\t\t\n\t\t\t\t\t\t\tDados iniciais\n\t\t\t\t\t\t\tInforme qual é a sua opção de financiamento ou do empréstimo com garantia de imóve")] | //fieldset[@*]'
        page.click('fieldset:has-text("1\n\t\t\t\t\t\t\n\t\t\t\t\t\t\tDados iniciais\n\t\t\t\t\t\t\tInforme qual é a sua opção de financiamento ou do empréstimo com garantia de imóve")')
        ' Passo 3: click'
        ' Seletores: #pessoaF | //input[@*]'
        page.click('#pessoaF')
        ' Passo 4: select'
        ' Seletores: #pessoaF | input:has-text("checked") | //input[contains(text(), "checked")]'
        page.select_option('#pessoaF', label='checked')
        ' Passo 5: fill'
        ' Seletores: #pessoaF | //input[@*]'
        page.fill('#pessoaF', self.data['steps'][4]['value'])
        ' Passo 6: click'
        ' Seletores: #tipoImovel_input | //input[@*]'
        page.click('#tipoImovel_input')
        ' Passo 7: click'
        ' Seletores: #ui-id-20 > a:nth-of-type(1) | a:has-text("Residencial") | //a[contains(text(), "Residencial")]'
        page.click('#ui-id-20 > a:nth-of-type(1)')
        ' Passo 8: click'
        ' Seletores: #grupoTipoFinanciamento_input | //input[@*]'
        page.click('#grupoTipoFinanciamento_input')
        ' Passo 9: click'
        ' Seletores: #ui-id-26 > a:nth-of-type(1) | a:has-text("Aquisição de Imóvel Usado") | //a[contains(text(), "Aquisição de Imóvel Usado")]'
        page.click('#ui-id-26 > a:nth-of-type(1)')
        ' Passo 10: click'
        ' Seletores: #valorImovel | //input[@*]'
        page.click('#valorImovel')
        ' Passo 11: click'
        ' Seletores: #uf_input | //input[@*]'
        page.click('#uf_input')
        ' Passo 12: click'
        ' Seletores: #ui-id-39 > a:nth-of-type(1) | a:has-text("DF") | //a[contains(text(), "DF")]'
        page.click('#ui-id-39 > a:nth-of-type(1)')
        ' Passo 13: click'
        ' Seletores: #cidade_input | //input[@*]'
        page.click('#cidade_input')
        ' Passo 14: click'
        ' Seletores: #ui-id-63 > a:nth-of-type(1) | a:has-text("BRASILIA") | //a[contains(text(), "BRASILIA")]'
        page.click('#ui-id-63 > a:nth-of-type(1)')
        ' Passo 15: click'
        ' Seletores: #btn_next1 | div:has-text("Próxima etapa") | //div[contains(text(), "Próxima etapa")]'
        page.click('#btn_next1')
        ' Passo 16: click'
        ' Seletores: #nuCpfCnpjInteressado | //input[@*]'
        page.click('#nuCpfCnpjInteressado')
        ' Passo 17: fill'
        ' Seletores: #nuCpfCnpjInteressado | input:has-text("Qual é o seu CPF?") | //input[contains(text(), "Qual é o seu CPF?")]'
        page.fill('#nuCpfCnpjInteressado', self.data['steps'][16]['value'])
        ' Passo 18: fill'
        ' Seletores: #nuCpfCnpjInteressado | input:has-text("Qual é o seu CPF?") | //input[contains(text(), "Qual é o seu CPF?")]'
        page.fill('#nuCpfCnpjInteressado', self.data['steps'][17]['value'])
        ' Passo 19: fill'
        ' Seletores: #nuCpfCnpjInteressado | input:has-text("Qual é o seu CPF?") | //input[contains(text(), "Qual é o seu CPF?")]'
        page.fill('#nuCpfCnpjInteressado', self.data['steps'][18]['value'])
        ' Passo 20: fill'
        ' Seletores: #nuCpfCnpjInteressado | input:has-text("Qual é o seu CPF?") | //input[contains(text(), "Qual é o seu CPF?")]'
        page.fill('#nuCpfCnpjInteressado', self.data['steps'][19]['value'])
        ' Passo 21: fill'
        ' Seletores: #nuCpfCnpjInteressado | input:has-text("Qual é o seu CPF?") | //input[contains(text(), "Qual é o seu CPF?")]'
        page.fill('#nuCpfCnpjInteressado', self.data['steps'][20]['value'])
        ' Passo 22: click'
        ' Seletores: ul:has-text("Qual é o seu CPF?\n\t\t\t\t\t\t\t\t\t\n\t\t\t\t\t\t\t\t\t\n\t\t\t\t\t\t\t\t\n\t\t\t\t\t\t\t\n\t\t\t\t\t\t\n\t\t\t\t\t\t\n\t\t\t\t\t\t\t\n\t\t\t\t\t\t\t\t\n\t\t\t\t\t\t\t\t\tQual é o número do seu te") | //ul[contains(text(), "Qual é o seu CPF?\n\t\t\t\t\t\t\t\t\t\n\t\t\t\t\t\t\t\t\t\n\t\t\t\t\t\t\t\t\n\t\t\t\t\t\t\t\n\t\t\t\t\t\t\n\t\t\t\t\t\t\n\t\t\t\t\t\t\t\n\t\t\t\t\t\t\t\t\n\t\t\t\t\t\t\t\t\tQual é o número do seu te")] | //ul[@*]'
        page.click('ul:has-text("Qual é o seu CPF?\n\t\t\t\t\t\t\t\t\t\n\t\t\t\t\t\t\t\t\t\n\t\t\t\t\t\t\t\t\n\t\t\t\t\t\t\t\n\t\t\t\t\t\t\n\t\t\t\t\t\t\n\t\t\t\t\t\t\t\n\t\t\t\t\t\t\t\t\n\t\t\t\t\t\t\t\t\tQual é o número do seu te")')
        ' Passo 23: click'
        ' Seletores: #nuTelefoneCelular | //input[@*]'
        page.click('#nuTelefoneCelular')
        ' Passo 24: fill'
        ' Seletores: #nuTelefoneCelular | input:has-text("Qual é o número do seu telefone celular?") | //input[contains(text(), "Qual é o número do seu telefone celular?")]'
        page.fill('#nuTelefoneCelular', self.data['steps'][23]['value'])
        ' Passo 25: fill'
        ' Seletores: #nuTelefoneCelular | input:has-text("Qual é o número do seu telefone celular?") | //input[contains(text(), "Qual é o número do seu telefone celular?")]'
        page.fill('#nuTelefoneCelular', self.data['steps'][24]['value'])
        ' Passo 26: fill'
        ' Seletores: #nuTelefoneCelular | input:has-text("Qual é o número do seu telefone celular?") | //input[contains(text(), "Qual é o número do seu telefone celular?")]'
        page.fill('#nuTelefoneCelular', self.data['steps'][25]['value'])
        ' Passo 27: fill'
        ' Seletores: #nuTelefoneCelular | input:has-text("Qual é o número do seu telefone celular?") | //input[contains(text(), "Qual é o número do seu telefone celular?")]'
        page.fill('#nuTelefoneCelular', self.data['steps'][26]['value'])
        ' Passo 28: fill'
        ' Seletores: #nuTelefoneCelular | input:has-text("Qual é o número do seu telefone celular?") | //input[contains(text(), "Qual é o número do seu telefone celular?")]'
        page.fill('#nuTelefoneCelular', self.data['steps'][27]['value'])
        ' Passo 29: fill'
        ' Seletores: #nuTelefoneCelular | input:has-text("Qual é o número do seu telefone celular?") | //input[contains(text(), "Qual é o número do seu telefone celular?")]'
        page.fill('#nuTelefoneCelular', self.data['steps'][28]['value'])
        ' Passo 30: fill'
        ' Seletores: #nuTelefoneCelular | input:has-text("Qual é o número do seu telefone celular?") | //input[contains(text(), "Qual é o número do seu telefone celular?")]'
        page.fill('#nuTelefoneCelular', self.data['steps'][29]['value'])
        ' Passo 31: click'
        ' Seletores: #rendaFamiliarBruta | //input[@*]'
        page.click('#rendaFamiliarBruta')
        ' Passo 32: click'
        ' Seletores: #dataNascimento | //input[@*]'
        page.click('#dataNascimento')
        ' Passo 33: select'
        ' Seletores: #ui-datepicker-div > div:nth-of-type(1) > div:nth-of-type(1) > select:nth-of-type(2) | select:has-text("1994") | //select[contains(text(), "1994")]'
        page.select_option('#ui-datepicker-div > div:nth-of-type(1) > div:nth-of-type(1) > select:nth-of-type(2)', label='1994')
        ' Passo 34: click'
        ' Seletores: #ui-datepicker-div > table:nth-of-type(1) > tbody:nth-of-type(1) > tr:nth-of-type(2) > td:nth-of-type(4) > a:nth-of-type(1) | a:has-text("8") | //a[contains(text(), "8")]'
        page.click('#ui-datepicker-div > table:nth-of-type(1) > tbody:nth-of-type(1) > tr:nth-of-type(2) > td:nth-of-type(4) > a:nth-of-type(1)')