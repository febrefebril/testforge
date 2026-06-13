import pytest
import json
from pathlib import Path
from playwright.sync_api import Page
from playwright.sync_api import expect

class Tf-Pf:
    DATA_PATH = Path(__file__).with_suffix('.data.json')

    @pytest.fixture(autouse=True)
    def setup(self, page: Page):
        self.page = page
        with open(self.DATA_PATH) as f:
            self.data = json.load(f)

    def test_run(self, page: Page):
        """ Passo 1: click"""
        ' Seletores: #tipoImovelTrigger | div:has-text("Selecione") | div.ui-selectonemenu-trigger'
        page.goto('http://localhost:8081/primefaces.html')
        ' Passo 2: click'
        ' Seletores: li:has-text("Residencial") | li.ui-selectonemenu-item'
        page.click('li:has-text("Residencial")')
        ' Passo 3: click'
        ' Seletores: #ufSelectTrigger | div:has-text("Selecione") | div.ui-selectonemenu-trigger'
        page.click('#ufSelectTrigger')
        ' Passo 4: click'
        ' Seletores: li:has-text("Distrito Federal") | li.ui-selectonemenu-item'
        page.click('li:has-text("Distrito Federal")')
        ' Passo 5: click'
        ' Seletores: #cidadeAcInput | input[placeholder="Digite para buscar..."] | input.ui-autocomplete-input'
        page.click('#cidadeAcInput')
        ' Passo 6: click'
        ' Seletores: li:has-text("Brasília") | li.ui-autocomplete-item'
        page.click('li:has-text("Brasília")')
        ' Passo 7: click'
        ' Seletores: #bancoAcInput | input[placeholder="Nome do banco..."] | input.ui-autocomplete-input'
        page.click('#bancoAcInput')
        ' Passo 8: click'
        ' Seletores: li:has-text("Caixa Econômica") | li.ui-autocomplete-item'
        page.click('li:has-text("Caixa Econômica")')
        ' Passo 9: click'
        ' Seletores: #kendoCategoriaInput | input.k-input'
        page.click('#kendoCategoriaInput')
        ' Passo 10: click'
        ' Seletores: #kendoCategoriaInput | input.k-input'
        page.click('#kendoCategoriaInput')