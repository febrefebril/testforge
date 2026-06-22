import pytest
import json
from pathlib import Path
from playwright.sync_api import Page
from playwright.sync_api import expect

class TesttfAssertAll:
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
        for _sel in ['li:has-text("Residencial")', 'li.ui-selectonemenu-item']:
            try:
                page.click(_sel)
                break
            except Exception:
                continue
        else:
            raise AssertionError('click falhou: ' + str(['li:has-text("Residencial")', 'li.ui-selectonemenu-item']))
        ' Passo 3: select'
        ' Seletores: #tipoImovelSelect'
        page.select_option(['#tipoImovelSelect'][0], label='Residencial')
        ' Passo 4: assert'
        ' Seletores: h1:has-text("Tipo de Imóvel") | h1:has-text("🧪 PrimeFaces Widgets — Página de Teste")'
        expect(page.locator('h1:has-text("Tipo de Imóvel")')).to_contain_text('🧪 PrimeFaces Widgets — Página de Teste')
        ' Passo 5: assert'
        ' Seletores: #avistaRadio | input[name="financiamento"]'
        expect(page.locator('#avistaRadio')).to_be_checked()
        ' Passo 6: assert'
        ' Seletores: #nomeInput | label:has-text("Nome (desabilitado)") | span:has-text("Nome (desabilitado)")'
        expect(page.locator('#nomeInput')).to_be_disabled()
        ' Passo 7: assert'
        ' Seletores: #result | div:has-text("Tipo de Imóvel") | div:has-text("🖱️ Última interação: select: Residencial (value=1)\n  📋 Hidden select value: select#tipoImovelSelect = 1")'
        expect(page.locator('#result')).to_be_visible()
        ' Passo 8: assert'
        ' Seletores: #hiddenElement | div:has-text("Tipo de Imóvel") | div:has-text("Este elemento está oculto")'
        expect(page.locator('#hiddenElement')).not_to_be_visible()
        ' Passo 9: click'
        ' Seletores: #cidadeAcInput | input[placeholder="Digite para buscar..."] | input.ui-autocomplete-input'
        for _sel in ['#cidadeAcInput', 'input[placeholder="Digite para buscar..."]', 'input.ui-autocomplete-input']:
            try:
                page.click(_sel)
                break
            except Exception:
                continue
        else:
            raise AssertionError('click falhou: ' + str(['#cidadeAcInput', 'input[placeholder="Digite para buscar..."]', 'input.ui-autocomplete-input']))
        ' Passo 10: fill'
        ' Seletores: #cidadeAcInput | input[placeholder="Digite para buscar..."] | input.ui-autocomplete-input'
        for _sel in ['#cidadeAcInput', 'input[placeholder="Digite para buscar..."]', 'input.ui-autocomplete-input']:
            try:
                page.fill(_sel, self.data['steps'][9]['value'])
                break
            except Exception:
                continue
        else:
            raise AssertionError('fill falhou: ' + str(['#cidadeAcInput', 'input[placeholder="Digite para buscar..."]', 'input.ui-autocomplete-input']))
        ' Passo 11: click'
        ' Seletores: li:has-text("Brasília") | li.ui-autocomplete-item'
        for _sel in ['li:has-text("Brasília")', 'li.ui-autocomplete-item']:
            try:
                page.click(_sel)
                break
            except Exception:
                continue
        else:
            raise AssertionError('click falhou: ' + str(['li:has-text("Brasília")', 'li.ui-autocomplete-item']))
        ' Passo 12: fill'
        ' Seletores: #cidadeAcInput | input[placeholder="Digite para buscar..."] | input.ui-autocomplete-input'
        for _sel in ['#cidadeAcInput', 'input[placeholder="Digite para buscar..."]', 'input.ui-autocomplete-input']:
            try:
                page.fill(_sel, self.data['steps'][11]['value'])
                break
            except Exception:
                continue
        else:
            raise AssertionError('fill falhou: ' + str(['#cidadeAcInput', 'input[placeholder="Digite para buscar..."]', 'input.ui-autocomplete-input']))
        ' Passo 13: assert'
        ' Seletores: #cidadeAcInput | input[placeholder="Digite para buscar..."] | input.ui-autocomplete-input'
        expect(page.locator('#cidadeAcInput')).to_contain_text('')