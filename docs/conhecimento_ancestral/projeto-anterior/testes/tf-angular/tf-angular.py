import pytest
import json
from pathlib import Path
from playwright.sync_api import Page
from playwright.sync_api import expect

class Tf-Angular:
    DATA_PATH = Path(__file__).with_suffix('.data.json')

    @pytest.fixture(autouse=True)
    def setup(self, page: Page):
        self.page = page
        with open(self.DATA_PATH) as f:
            self.data = json.load(f)

    def test_run(self, page: Page):
        """ Passo 1: click"""
        ' Seletores: #matCategoria | div:has-text("Categoria") | div[role="listbox"]:has-text("Selecione\n            ▼")'
        page.goto('http://localhost:8081/angular-select.html')
        ' Passo 2: click'
        ' Seletores: #matCategoria | div:has-text("Categoria") | div[role="listbox"]:has-text("Selecione\n            ▼")'
        page.click('#matCategoria')
        ' Passo 3: click'
        ' Seletores: div[role="option"]:has-text("✓\n            Eletrônicos") | div:has-text("✓\n            Eletrônicos") | div.mat-option'
        page.click('div[role="option"]:has-text("✓\n            Eletrônicos")')
        ' Passo 4: click'
        ' Seletores: #matPagamento | div:has-text("Forma de Pagamento") | div[role="listbox"]:has-text("Selecione\n            ▼")'
        page.click('#matPagamento')
        ' Passo 5: click'
        ' Seletores: div[role="option"]:has-text("✓\n            PIX") | div:has-text("✓\n            PIX") | div.mat-option'
        page.click('div[role="option"]:has-text("✓\n            PIX")')