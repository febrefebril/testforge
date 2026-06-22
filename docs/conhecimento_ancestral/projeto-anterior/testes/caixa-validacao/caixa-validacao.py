import pytest
import json
from pathlib import Path
from playwright.sync_api import Page
from playwright.sync_api import expect

class Caixa-Validacao:
    DATA_PATH = Path(__file__).with_suffix('.data.json')

    @pytest.fixture(autouse=True)
    def setup(self, page: Page):
        self.page = page
        with open(self.DATA_PATH) as f:
            self.data = json.load(f)

    def test_run(self, page: Page):
        """ Passo 1: click"""
        ' Seletores: #pessoaF | input[name="pessoa"]'
        page.goto('https://www8.caixa.gov.br/siopiinternet-web/simulaOperacaoInternet.do?method=inicializarCasoUso')
        ' Passo 2: click'
        ' Seletores: #tipoImovel_input | label:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?") | span:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?")'
        page.click('#tipoImovel_input')
        ' Passo 3: click'
        ' Seletores: a:has-text("Residencial")'
        page.click('a:has-text("Residencial")')
        ' Passo 4: fill'
        ' Seletores: #tipoImovel_input | label:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?") | span:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?")'
        page.fill('#tipoImovel_input', self.data['steps'][3]['value'])
        ' Passo 5: click'
        ' Seletores: #grupoTipoFinanciamento_input | label:has-text("Selecione a opção de Financiamento/Empréstimo") | span:has-text("Selecione a opção de Financiamento/Empréstimo")'
        page.click('#grupoTipoFinanciamento_input')
        ' Passo 6: click'
        ' Seletores: a:has-text("Aquisição de Imóvel Usado")'
        page.click('a:has-text("Aquisição de Imóvel Usado")')
        ' Passo 7: fill'
        ' Seletores: #grupoTipoFinanciamento_input | label:has-text("Selecione a opção de Financiamento/Empréstimo") | span:has-text("Selecione a opção de Financiamento/Empréstimo")'
        page.fill('#grupoTipoFinanciamento_input', self.data['steps'][6]['value'])
        ' Passo 8: click'
        ' Seletores: #valorImovel | input[name="valorImovel"] | label:has-text("Valor aproximado do imóvel?")'
        page.click('#valorImovel')
        ' Passo 9: fill'
        ' Seletores: #valorImovel | input[name="valorImovel"] | label:has-text("Valor aproximado do imóvel?")'
        page.fill('#valorImovel', self.data['steps'][8]['value'])
        ' Passo 10: fill'
        ' Seletores: #valorImovel | input[name="valorImovel"] | label:has-text("Valor aproximado do imóvel?")'
        page.fill('#valorImovel', self.data['steps'][9]['value'])
        ' Passo 11: fill'
        ' Seletores: #valorImovel | input[name="valorImovel"] | label:has-text("Valor aproximado do imóvel?")'
        page.fill('#valorImovel', self.data['steps'][10]['value'])
        ' Passo 12: fill'
        ' Seletores: #valorImovel | input[name="valorImovel"] | label:has-text("Valor aproximado do imóvel?")'
        page.fill('#valorImovel', self.data['steps'][11]['value'])
        ' Passo 13: click'
        ' Seletores: #uf_input | label:has-text("Em qual cidade está localizado o imóvel?") | span:has-text("Em qual cidade está localizado o imóvel?")'
        page.click('#uf_input')
        ' Passo 14: click'
        ' Seletores: a:has-text("DF")'
        page.click('a:has-text("DF")')
        ' Passo 15: fill'
        ' Seletores: #uf_input | label:has-text("Em qual cidade está localizado o imóvel?") | span:has-text("Em qual cidade está localizado o imóvel?")'
        page.fill('#uf_input', self.data['steps'][14]['value'])
        ' Passo 16: click'
        ' Seletores: #cidade_input | label:has-text("Em qual cidade está localizado o imóvel?") | span:has-text("Em qual cidade está localizado o imóvel?")'
        page.click('#cidade_input')
        ' Passo 17: click'
        ' Seletores: a:has-text("BRASILIA")'
        page.click('a:has-text("BRASILIA")')
        ' Passo 18: fill'
        ' Seletores: #cidade_input | label:has-text("Em qual cidade está localizado o imóvel?") | span:has-text("Em qual cidade está localizado o imóvel?")'
        page.fill('#cidade_input', self.data['steps'][17]['value'])
        ' Passo 19: click'
        ' Seletores: #btn_next1 | div:has-text("Próxima etapa") | div.div_button.submit-d.submit-blue'
        page.click('#btn_next1')
        ' Passo 20: click'
        ' Seletores: #nuTelefoneCelular | input[name="nuTelefoneCelular"] | label:has-text("Qual é o número do seu telefone celular?")'
        page.click('#nuTelefoneCelular')
        ' Passo 21: click'
        ' Seletores: #nuCpfCnpjInteressado | input[name="nuCpfCnpjInteressado"] | label:has-text("Qual é o seu CPF?")'
        page.click('#nuCpfCnpjInteressado')
        ' Passo 22: fill'
        ' Seletores: #nuCpfCnpjInteressado | input[name="nuCpfCnpjInteressado"] | label:has-text("Qual é o seu CPF?")'
        page.fill('#nuCpfCnpjInteressado', self.data['steps'][21]['value'])
        ' Passo 23: fill'
        ' Seletores: #nuCpfCnpjInteressado | input[name="nuCpfCnpjInteressado"] | label:has-text("Qual é o seu CPF?")'
        page.fill('#nuCpfCnpjInteressado', self.data['steps'][22]['value'])
        ' Passo 24: fill'
        ' Seletores: #nuCpfCnpjInteressado | input[name="nuCpfCnpjInteressado"] | label:has-text("Qual é o seu CPF?")'
        page.fill('#nuCpfCnpjInteressado', self.data['steps'][23]['value'])
        ' Passo 25: fill'
        ' Seletores: #nuCpfCnpjInteressado | input[name="nuCpfCnpjInteressado"] | label:has-text("Qual é o seu CPF?")'
        page.fill('#nuCpfCnpjInteressado', self.data['steps'][24]['value'])
        ' Passo 26: fill'
        ' Seletores: #nuCpfCnpjInteressado | input[name="nuCpfCnpjInteressado"] | label:has-text("Qual é o seu CPF?")'
        page.fill('#nuCpfCnpjInteressado', self.data['steps'][25]['value'])
        ' Passo 27: fill'
        ' Seletores: #nuCpfCnpjInteressado | input[name="nuCpfCnpjInteressado"] | label:has-text("Qual é o seu CPF?")'
        page.fill('#nuCpfCnpjInteressado', self.data['steps'][26]['value'])
        ' Passo 28: fill'
        ' Seletores: #nuCpfCnpjInteressado | input[name="nuCpfCnpjInteressado"] | label:has-text("Qual é o seu CPF?")'
        page.fill('#nuCpfCnpjInteressado', self.data['steps'][27]['value'])
        ' Passo 29: fill'
        ' Seletores: #nuTelefoneCelular | input[name="nuTelefoneCelular"] | label:has-text("Qual é o número do seu telefone celular?")'
        page.fill('#nuTelefoneCelular', self.data['steps'][28]['value'])
        ' Passo 30: fill'
        ' Seletores: #nuTelefoneCelular | input[name="nuTelefoneCelular"] | label:has-text("Qual é o número do seu telefone celular?")'
        page.fill('#nuTelefoneCelular', self.data['steps'][29]['value'])
        ' Passo 31: fill'
        ' Seletores: #nuTelefoneCelular | input[name="nuTelefoneCelular"] | label:has-text("Qual é o número do seu telefone celular?")'
        page.fill('#nuTelefoneCelular', self.data['steps'][30]['value'])
        ' Passo 32: fill'
        ' Seletores: #nuTelefoneCelular | input[name="nuTelefoneCelular"] | label:has-text("Qual é o número do seu telefone celular?")'
        page.fill('#nuTelefoneCelular', self.data['steps'][31]['value'])
        ' Passo 33: click'
        ' Seletores: #rendaFamiliarBruta | input[name="rendaFamiliarBruta"] | label:has-text("Renda bruta familiar mensal?")'
        page.click('#rendaFamiliarBruta')
        ' Passo 34: fill'
        ' Seletores: #rendaFamiliarBruta | input[name="rendaFamiliarBruta"] | label:has-text("Renda bruta familiar mensal?")'
        page.fill('#rendaFamiliarBruta', self.data['steps'][33]['value'])
        ' Passo 35: fill'
        ' Seletores: #rendaFamiliarBruta | input[name="rendaFamiliarBruta"] | label:has-text("Renda bruta familiar mensal?")'
        page.fill('#rendaFamiliarBruta', self.data['steps'][34]['value'])
        ' Passo 36: fill'
        ' Seletores: #rendaFamiliarBruta | input[name="rendaFamiliarBruta"] | label:has-text("Renda bruta familiar mensal?")'
        page.fill('#rendaFamiliarBruta', self.data['steps'][35]['value'])
        ' Passo 37: click'
        ' Seletores: button:has-text("Data de nascimento do proponente?") | button.ui-datepicker-trigger'
        page.click('button:has-text("Data de nascimento do proponente?")')
        ' Passo 38: click'
        ' Seletores: a:has-text("1") | a.ui-state-default.ui-state-hover'
        page.click('a:has-text("1")')