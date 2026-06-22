import pytest
import json
from pathlib import Path
from playwright.sync_api import Page
from playwright.sync_api import expect

class Test20260602175150:
    DATA_PATH = Path(__file__).with_suffix('.data.json')

    @pytest.fixture(autouse=True)
    def setup(self, page: Page):
        self.page = page
        with open(self.DATA_PATH) as f:
            self.data = json.load(f)

    def test_run(self, page: Page):
        """ Passo 1: click"""
        ' Seletores: div:has-text("Esta é uma simulação para aquisição de imóvel residencial (novo ou usado) ou par") | div:has-text("Início › Produtos para você › Habitação ›\n\t\t\t\n\t\t\t\n\t\t\t\t\n\t\t\t\t\t\n\t\t\t\t\t\n\t\t\t\t\t\tSimulador Crédito imobiliário CAIXA, Programa M") | //div[contains(text(), "Início › Produtos para você › Habitação ›\n\t\t\t\n\t\t\t\n\t\t\t\t\n\t\t\t\t\t\n\t\t\t\t\t\n\t\t\t\t\t\tSimulador Crédito imobiliário CAIXA, Programa M")]'
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
        ' Seletores: span.ui-button-icon-primary.ui-icon.ui-icon-triangle-1-s | //span[@*]'
        page.click('span.ui-button-icon-primary.ui-icon.ui-icon-triangle-1-s')
        ' Passo 6: click'
        ' Seletores: span.ui-button-icon-primary.ui-icon.ui-icon-triangle-1-s | //span[@*]'
        page.click('span.ui-button-icon-primary.ui-icon.ui-icon-triangle-1-s')
        ' Passo 7: click'
        ' Seletores: li:has-text("Esta é uma simulação para aquisição de imóvel residencial (novo ou usado) ou par") | li:has-text("Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?\n\t\t\t\t\t\t\t\n\t\t\t\t\t\t\t\t\n\nInforme o tipo de financi") | //li[contains(text(), "Qual tipo de financiamento ou empréstimo com garantia de imóvel você deseja?\n\t\t\t\t\t\t\t\n\t\t\t\t\t\t\t\t\n\nInforme o tipo de financi")]'
        page.click('li:has-text("Esta é uma simulação para aquisição de imóvel residencial (novo ou usado) ou par")')
        ' Passo 8: click'
        ' Seletores: fieldset:has-text("Esta é uma simulação para aquisição de imóvel residencial (novo ou usado) ou par") | fieldset:has-text("1\n\t\t\t\t\t\t\n\t\t\t\t\t\t\tDados iniciais\n\t\t\t\t\t\t\tInforme qual é a sua opção de financiamento ou do empréstimo com garantia de imóve") | //fieldset[contains(text(), "1\n\t\t\t\t\t\t\n\t\t\t\t\t\t\tDados iniciais\n\t\t\t\t\t\t\tInforme qual é a sua opção de financiamento ou do empréstimo com garantia de imóve")]'
        page.click('fieldset:has-text("Esta é uma simulação para aquisição de imóvel residencial (novo ou usado) ou par")')
        ' Passo 9: click'
        ' Seletores: html:has-text("var CONTEXTO_APP =\t\'/siopiinternet-web\';\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\tfunction combo() {\n\t\tjQuery(\\"sel") | //html[contains(text(), "var CONTEXTO_APP =\t\'/siopiinternet-web\';\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\tfunction combo() {\n\t\tjQuery(\\"sel")] | html.js.flexbox.flexboxlegacy.no-touch.geolocation.rgba.hsla.multiplebgs.backgroundsize.borderimage.borderradius.boxshadow.textshadow.opacity.cssanimations.csscolumns.cssgradients.cssreflections.csstransforms.csstransforms3d.csstransitions.fontface.generatedcontent.svg.inlinesvg.smil.svgclippaths.cssvwunit.desktop'
        page.click('html:has-text("var CONTEXTO_APP =\t\'/siopiinternet-web\';\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\tfunction combo() {\n\t\tjQuery(\\"sel")')
        ' Passo 10: click'
        ' Seletores: li:has-text("Esta é uma simulação para aquisição de imóvel residencial (novo ou usado) ou par") | li:has-text("Este financiamento ou empréstimo com garantia de imóvel é para uma pessoa:") | //li[contains(text(), "Este financiamento ou empréstimo com garantia de imóvel é para uma pessoa:")]'
        page.click('li:has-text("Esta é uma simulação para aquisição de imóvel residencial (novo ou usado) ou par")')