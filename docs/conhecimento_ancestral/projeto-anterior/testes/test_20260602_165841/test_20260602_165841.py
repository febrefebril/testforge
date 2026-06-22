import pytest
import json
from pathlib import Path
from playwright.sync_api import Page
from playwright.sync_api import expect

class Test20260602165841:
    DATA_PATH = Path(__file__).with_suffix('.data.json')

    @pytest.fixture(autouse=True)
    def setup(self, page: Page):
        self.page = page
        with open(self.DATA_PATH) as f:
            self.data = json.load(f)

    def test_run(self, page: Page):
        """ Passo 1: click"""
        ' Seletores: #pessoaF | //input[@*]'
        page.goto('https://www8.caixa.gov.br/siopiinternet-web/simulaOperacaoInternet.do?method=inicializarCasoUso')
        ' Passo 2: select'
        ' Seletores: #pessoaF | input:has-text("checked") | //input[contains(text(), "checked")]'
        page.select_option('#pessoaF', label='checked')
        ' Passo 3: fill'
        ' Seletores: #pessoaF | //input[@*]'
        page.fill('#pessoaF', self.data['steps'][2]['value'])
        ' Passo 4: click'
        ' Seletores: #tipoImovel_input | //input[@*]'
        page.click('#tipoImovel_input')
        ' Passo 5: click'
        ' Seletores: #ui-id-20 > a:nth-of-type(1) | a:has-text("Residencial") | //a[contains(text(), "Residencial")]'
        page.click('#ui-id-20 > a:nth-of-type(1)')
        ' Passo 6: click'
        ' Seletores: #grupoTipoFinanciamento_input | //input[@*]'
        page.click('#grupoTipoFinanciamento_input')
        ' Passo 7: click'
        ' Seletores: #ui-id-26 > a:nth-of-type(1) | a:has-text("Aquisição de Imóvel Usado") | //a[contains(text(), "Aquisição de Imóvel Usado")]'
        page.click('#ui-id-26 > a:nth-of-type(1)')
        ' Passo 8: click'
        ' Seletores: #valorImovel | //input[@*]'
        page.click('#valorImovel')
        ' Passo 9: click'
        ' Seletores: #uf_input | //input[@*]'
        page.click('#uf_input')
        ' Passo 10: click'
        ' Seletores: #ui-id-39 > a:nth-of-type(1) | a:has-text("DF") | //a[contains(text(), "DF")]'
        page.click('#ui-id-39 > a:nth-of-type(1)')
        ' Passo 11: click'
        ' Seletores: #cidade_input | //input[@*]'
        page.click('#cidade_input')
        ' Passo 12: click'
        ' Seletores: #ui-id-63 > a:nth-of-type(1) | a:has-text("BRASILIA") | //a[contains(text(), "BRASILIA")]'
        page.click('#ui-id-63 > a:nth-of-type(1)')
        ' Passo 13: click'
        ' Seletores: #btn_next1 | div:has-text("Próxima etapa") | //div[contains(text(), "Próxima etapa")]'
        page.click('#btn_next1')
        ' Passo 14: click'
        ' Seletores: #nuCpfCnpjInteressado | //input[@*]'
        page.click('#nuCpfCnpjInteressado')
        ' Passo 15: fill'
        ' Seletores: #nuCpfCnpjInteressado | input:has-text("Qual é o seu CPF?") | //input[contains(text(), "Qual é o seu CPF?")]'
        page.fill('#nuCpfCnpjInteressado', self.data['steps'][14]['value'])
        ' Passo 16: fill'
        ' Seletores: #nuCpfCnpjInteressado | input:has-text("Qual é o seu CPF?") | //input[contains(text(), "Qual é o seu CPF?")]'
        page.fill('#nuCpfCnpjInteressado', self.data['steps'][15]['value'])
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
        ' Seletores: #nuTelefoneCelular | //input[@*]'
        page.click('#nuTelefoneCelular')
        ' Passo 23: fill'
        ' Seletores: #nuTelefoneCelular | input:has-text("Qual é o número do seu telefone celular?") | //input[contains(text(), "Qual é o número do seu telefone celular?")]'
        page.fill('#nuTelefoneCelular', self.data['steps'][22]['value'])
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
        ' Passo 30: click'
        ' Seletores: #rendaFamiliarBruta | //input[@*]'
        page.click('#rendaFamiliarBruta')
        ' Passo 31: click'
        ' Seletores: div:nth-of-type(1) > form:nth-of-type(1) > div:nth-of-type(1) > fieldset:nth-of-type(2) > ul:nth-of-type(1) > li:nth-of-type(4) > div:nth-of-type(1) > button:nth-of-type(1) | //button[@*]'
        page.click('div:nth-of-type(1) > form:nth-of-type(1) > div:nth-of-type(1) > fieldset:nth-of-type(2) > ul:nth-of-type(1) > li:nth-of-type(4) > div:nth-of-type(1) > button:nth-of-type(1)')
        ' Passo 32: click'
        ' Seletores: #ui-datepicker-div > div:nth-of-type(1) > div:nth-of-type(1) > select:nth-of-type(2) | select:has-text("194519461947194819491950195119521953195419551956195719581959196019611962196319641965196619671968196919701971197219731974") | //select[contains(text(), "194519461947194819491950195119521953195419551956195719581959196019611962196319641965196619671968196919701971197219731974")]'
        page.click('#ui-datepicker-div > div:nth-of-type(1) > div:nth-of-type(1) > select:nth-of-type(2)')
        ' Passo 33: click'
        ' Seletores: #ui-datepicker-div > table:nth-of-type(1) > tbody:nth-of-type(1) > tr:nth-of-type(1) > td:nth-of-type(4) > a:nth-of-type(1) | a:has-text("2") | //a[contains(text(), "2")]'
        page.click('#ui-datepicker-div > table:nth-of-type(1) > tbody:nth-of-type(1) > tr:nth-of-type(1) > td:nth-of-type(4) > a:nth-of-type(1)')