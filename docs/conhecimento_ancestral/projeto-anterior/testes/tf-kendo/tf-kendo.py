import pytest
import json
from pathlib import Path
from playwright.sync_api import Page
from playwright.sync_api import expect

class Tf-Kendo:
    DATA_PATH = Path(__file__).with_suffix('.data.json')

    @pytest.fixture(autouse=True)
    def setup(self, page: Page):
        self.page = page
        with open(self.DATA_PATH) as f:
            self.data = json.load(f)

    def test_run(self, page: Page):
        """ Passo 1: click"""
        ' Seletores: #kendoCategoriaWrap | span:has-text("Selecione\n            ▼") | span.k-dropdown-wrap'
        page.goto('http://localhost:8081/kendo-dropdown.html')
        ' Passo 2: click'
        ' Seletores: li:has-text("Roupas e Acessórios") | li.k-item'
        page.click('li:has-text("Roupas e Acessórios")')
        ' Passo 3: click'
        ' Seletores: #kendoCategoriaWrap | span:has-text("Roupas e Acessórios\n            ▼") | span.k-dropdown-wrap'
        page.click('#kendoCategoriaWrap')
        ' Passo 4: click'
        ' Seletores: li:has-text("Eletrônicos") | li.k-item'
        page.click('li:has-text("Eletrônicos")')
        ' Passo 5: click'
        ' Seletores: #kendoFornecedorWrap | span:has-text("Selecione\n            ▼") | span.k-dropdown-wrap'
        page.click('#kendoFornecedorWrap')
        ' Passo 6: click'
        ' Seletores: li:has-text("Distribuidora Nacional") | li.k-item'
        page.click('li:has-text("Distribuidora Nacional")')