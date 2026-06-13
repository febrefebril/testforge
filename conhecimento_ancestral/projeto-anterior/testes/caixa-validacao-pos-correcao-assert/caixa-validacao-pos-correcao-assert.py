import pytest
import json
from pathlib import Path
from playwright.sync_api import Page
from playwright.sync_api import expect

class Caixa-Validacao-Pos-Correcao-Assert:
    DATA_PATH = Path(__file__).with_suffix('.data.json')

    @pytest.fixture(autouse=True)
    def setup(self, page: Page):
        self.page = page
        with open(self.DATA_PATH) as f:
            self.data = json.load(f)

    def test_run(self, page: Page):
        """ Passo 1: click"""
        ' Seletores: p:has-text("Veja estimativas a partir da prestação que você pretende assumir, da sua renda, ou do valor do imóvel.") | p.text-grayscale-90.text-size-nano.font-weight-400'
        page.goto('https://simuladorhabitacao.caixa.gov.br/home')
        ' Passo 2: click'
        ' Seletores: p:has-text("Sei quanto posso pagar por mês") | p.text-size-micro.text-grayscale-90.mt-1.font-weight-400'
        page.click('p:has-text("Sei quanto posso pagar por mês")')
        ' Passo 3: click'
        ' Seletores: span.mat-mdc-button-touch-target'
        page.click('span.mat-mdc-button-touch-target')
        ' Passo 4: click'
        ' Seletores: span.mat-mdc-button-touch-target'
        page.click('span.mat-mdc-button-touch-target')
        ' Passo 5: click'
        ' Seletores: span.mat-focus-indicator'
        page.click('span.mat-focus-indicator')
        ' Passo 6: click'
        ' Seletores: span.mat-focus-indicator'
        page.click('span.mat-focus-indicator')
        ' Passo 7: click'
        ' Seletores: span:has-text("1970") | span.mat-calendar-body-cell-content.mat-focus-indicator'
        page.click('span:has-text("1970")')
        ' Passo 8: click'
        ' Seletores: span:has-text("FEV") | span.mat-calendar-body-cell-content.mat-focus-indicator'
        page.click('span:has-text("FEV")')
        ' Passo 9: click'
        ' Seletores: span:has-text("4") | span.mat-calendar-body-cell-content.mat-focus-indicator'
        page.click('span:has-text("4")')
        ' Passo 10: click'
        ' Seletores: #mat-input-1 | input[aria-label="Prestação desejada *"] | input[placeholder="R$0,00"]'
        page.click('#mat-input-1')
        ' Passo 11: fill'
        ' Seletores: #mat-input-1 | input[aria-label="Prestação desejada *"] | input[placeholder="R$0,00"]'
        page.fill('#mat-input-1', self.data['steps'][10]['value'])
        ' Passo 12: fill'
        ' Seletores: #mat-input-1 | input[aria-label="Prestação desejada *"] | input[placeholder="R$0,00"]'
        page.fill('#mat-input-1', self.data['steps'][11]['value'])
        ' Passo 13: fill'
        ' Seletores: #mat-input-1 | input[aria-label="Prestação desejada *"] | input[placeholder="R$0,00"]'
        page.fill('#mat-input-1', self.data['steps'][12]['value'])
        ' Passo 14: click'
        ' Seletores: span:has-text("Calcular") | span.mdc-button__label'
        page.click('span:has-text("Calcular")')
        ' Passo 15: assert'
        ' Seletores: p:has-text("R$\xa0880.020,62") | p.text-grayscale-130.text-size-small.m-0.mb-4'
        expect(page.locator('p:has-text("R$\xa0880.020,62")')).to_contain_text('R$\xa0880.020,62')