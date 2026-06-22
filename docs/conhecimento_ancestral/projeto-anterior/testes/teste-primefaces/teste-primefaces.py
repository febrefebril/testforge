import pytest
import json
from pathlib import Path
from playwright.sync_api import Page
from playwright.sync_api import expect

class Teste-Primefaces:
    DATA_PATH = Path(__file__).with_suffix('.data.json')

    @pytest.fixture(autouse=True)
    def setup(self, page: Page):
        self.page = page
        with open(self.DATA_PATH) as f:
            self.data = json.load(f)

    def test_run(self, page: Page):
        """ Passo 1: click"""
        ' Seletores: #tipoImovelLabel | label:has-text("Selecione") | label:has-text("Selecione")'
        page.goto('http://localhost:8081/primefaces.html')
        ' Passo 2: select'
        ' Seletores: #tipoImovelSelect'
        page.select_option('#tipoImovelSelect', label='Residencial')
        ' Passo 3: click'
        ' Seletores: #ufSelectLabel | label:has-text("Selecione") | label:has-text("Selecione")'
        page.click('#ufSelectLabel')
        ' Passo 4: select'
        ' Seletores: #ufSelectOption'
        page.select_option('#ufSelectOption', label='Distrito Federal')
        ' Passo 5: assert'
        ' Seletores: h2:has-text("Tipo de Imóvel") | h2:has-text("PrimeFaces SelectOneMenu")'
        expect(page.locator('h2:has-text("Tipo de Imóvel")')).to_contain_text('PrimeFaces SelectOneMenu')