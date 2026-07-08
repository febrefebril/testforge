import pytest
import json
from pathlib import Path
from playwright.sync_api import Page
from playwright.sync_api import expect

class Tf-Jqui:
    DATA_PATH = Path(__file__).with_suffix('.data.json')

    @pytest.fixture(autouse=True)
    def setup(self, page: Page):
        self.page = page
        with open(self.DATA_PATH) as f:
            self.data = json.load(f)

    def test_run(self, page: Page):
        """ Passo 1: click"""
        ' Seletores: span:has-text("Selecione") | span.ui-selectmenu-text'
        page.goto('http://localhost:8081/jqueryui-selectmenu.html')
        ' Passo 2: click'
        ' Seletores: #ui-id-3 | div[role="option"]:has-text("Casado(a)") | div:has-text("Casado(a)")'
        page.click('#ui-id-3')
        ' Passo 3: click'
        ' Seletores: span:has-text("Selecione") | span.ui-selectmenu-text'
        page.click('span:has-text("Selecione")')
        ' Passo 4: click'
        ' Seletores: #ui-id-9 | div[role="option"]:has-text("Ensino Superior") | div:has-text("Ensino Superior")'
        page.click('#ui-id-9')