import pytest
import json
from pathlib import Path
from playwright.sync_api import Page
from playwright.sync_api import expect

class Tf-Assert-Test:
    DATA_PATH = Path(__file__).with_suffix('.data.json')

    @pytest.fixture(autouse=True)
    def setup(self, page: Page):
        self.page = page
        with open(self.DATA_PATH) as f:
            self.data = json.load(f)

    def test_run(self, page: Page):
        """ Passo 1: click"""
        ' Seletores: #tipoImovelSelect'
        page.goto('file:///home/febre/Projetos/testforge/tests/pagina-de-teste/primefaces/primefaces.html')
        ' Passo 2: click'
        ' Seletores: li:has-text("Residencial") | li.ui-selectonemenu-item'
        page.click('li:has-text("Residencial")')
        ' Passo 3: assert'
        ' Seletores: #tipoImovelSelect'
        expect(page.locator('#tipoImovelSelect')).to_contain_text('Selecione\n              Residencial\n              Comercial\n              Terreno\n              Rural')
        ' Passo 4: assert'
        ' Seletores: #cidadeAcInput | input[placeholder="Digite para buscar..."] | input.ui-autocomplete-input'
        expect(page.locator('#cidadeAcInput')).to_contain_text('')