import pytest
import json
from pathlib import Path
from playwright.sync_api import Page
from playwright.sync_api import expect

class TestgravacaoAuto:
    DATA_PATH = Path(__file__).with_suffix('.data.json')

    @pytest.fixture(autouse=True)
    def setup(self, page: Page):
        self.page = page
        with open(self.DATA_PATH) as f:
            self.data = json.load(f)

    def test_run(self, page: Page):
        """ Passo 1: click"""
        ' Seletores: input[placeholder="sem id, sem name"] | label:has-text("Campo sem ID (SEL-006)") | span:has-text("Campo sem ID (SEL-006)")'
        page.goto('http://localhost:8000/index.html')
        ' Passo 2: fill'
        ' Seletores: input[placeholder="sem id, sem name"] | label:has-text("Campo sem ID (SEL-006)") | span:has-text("Campo sem ID (SEL-006)")'
        page.fill('input[placeholder="sem id, sem name"]', self.data['steps'][1]['value'])
        ' Passo 3: click'
        ' Seletores: #campo-label-for | label:has-text("Label sem for (SEL-010)") | span:has-text("Label sem for (SEL-010)")'
        page.click('#campo-label-for')
        ' Passo 4: fill'
        ' Seletores: #campo-label-for | label:has-text("Label sem for (SEL-010)") | span:has-text("Label sem for (SEL-010)")'
        page.fill('#campo-label-for', self.data['steps'][3]['value'])
        ' Passo 5: click'
        ' Seletores: label:has-text("Opção A") | label:has-text("Opção A") | label.radio-label-custom'
        page.click('label:has-text("Opção A")')
        ' Passo 6: click'
        ' Seletores: button:has-text("Confirmar") | button.btn.btn-primary.acao-duplicada'
        page.click('button:has-text("Confirmar")')
        ' Passo 7: click'
        ' Seletores: #btn-fora-form | button:has-text("Botão fora do <form> (SEL-007)") | button:has-text("Ação fora do form")'
        page.click('#btn-fora-form')
        ' Passo 8: click'
        ' Seletores: #campo-cpf | input[placeholder="000.000.000-00"] | label:has-text("Máscara de input — CPF (INP-007)")'
        page.click('#campo-cpf')
        ' Passo 9: fill'
        ' Seletores: #campo-cpf | input[placeholder="000.000.000-00"] | label:has-text("Máscara de input — CPF (INP-007)")'
        page.fill('#campo-cpf', self.data['steps'][8]['value'])
        ' Passo 10: click'
        ' Seletores: #campo-data | input[placeholder="dd/mm/aaaa"] | label:has-text("Date picker jQuery UI (INP-009)")'
        page.click('#campo-data')
        ' Passo 11: click'
        ' Seletores: a:has-text("15") | a.ui-state-default.ui-state-hover'
        page.click('a:has-text("15")')
        ' Passo 12: click'
        ' Seletores: #campo-combobox | input[placeholder="Digite ou selecione"]'
        page.click('#campo-combobox')
        ' Passo 13: click'
        ' Seletores: div:has-text("Python") | div.combobox-item'
        page.click('div:has-text("Python")')
        ' Passo 14: upload'
        ' Seletores: #campo-upload | label:has-text("Upload de arquivo (INP-002)") | span:has-text("Upload de arquivo (INP-002)")'
        Path('fixture_upload.txt').write_text('Fixture criada pelo test runner')
        page.set_input_files('#campo-upload', 'fixture_upload.txt')
        ' Passo 15: click'
        ' Seletores: #campo-richedit | div:has-text("Rich text / contenteditable (INP-006)") | div:has-text("Digite aqui...")'
        page.click('#campo-richedit')
        ' Passo 16: drag'
        ' Seletores: #sortable-list > li:nth-of-type(1) | li:has-text("Item 1⠿ -> Arraste um item aqui")'
        page.locator('#sortable-list > li:nth-of-type(1)').drag_to(page.locator('#drop-zone'))
        ' Passo 17: click'
        ' Seletores: #campo-autocomplete | input[placeholder="Digite uma cidade"] | label:has-text("Autocomplete jQuery UI (TIM-006 / INP-010)")'
        page.click('#campo-autocomplete')
        ' Passo 18: fill'
        ' Seletores: #campo-autocomplete | input[placeholder="Digite uma cidade"] | label:has-text("Autocomplete jQuery UI (TIM-006 / INP-010)")'
        page.fill('#campo-autocomplete', self.data['steps'][17]['value'])
        ' Passo 19: click'
        ' Seletores: #ui-id-2 | div:has-text("Brasília") | div.ui-menu-item-wrapper'
        page.click('#ui-id-2')
        ' Passo 20: fill'
        ' Seletores: #campo-autocomplete | input[placeholder="Digite uma cidade"] | label:has-text("Autocomplete jQuery UI (TIM-006 / INP-010)")'
        page.fill('#campo-autocomplete', self.data['steps'][19]['value'])
        ' Passo 21: click'
        ' Seletores: #campo-lazy | input[placeholder="Campo carregado tardiamente"]'
        page.click('#campo-lazy')
        ' Passo 22: fill'
        ' Seletores: #campo-lazy | input[placeholder="Campo carregado tardiamente"]'
        page.fill('#campo-lazy', self.data['steps'][21]['value'])
        ' Passo 23: select'
        ' Seletores: #select-assincrono | label:has-text("Select com opções carregadas via JS (TIM-006)") | span:has-text("Select com opções carregadas via JS (TIM-006)")'
        page.select_option('#select-assincrono', label='Opção 2')
        ' Passo 24: click'
        ' Seletores: #shadow-host | div:has-text("Shadow DOM aberto (CTX-003)") | div:has-text("Shadow DOM será anexado via JS")'
        page.click('#shadow-host')
        ' Passo 25: fill'
        ' Seletores: #shadow-input | input[placeholder="Campo no Shadow DOM"]'
        page.fill('#shadow-input', self.data['steps'][24]['value'])
        ' Passo 26: click'
        ' Seletores: #btn-iframe | button:has-text("Clique no iframe")'
        page.frame_locator('#iframe-teste').locator('#btn-iframe').click()
        ' Passo 27: click'
        ' Seletores: #btn-abrir-modal | button:has-text("Modal/dialog (CTX-006)") | button:has-text("Abrir Modal")'
        page.click('#btn-abrir-modal')
        ' Passo 28: click'
        ' Seletores: #campo-modal | input[placeholder="Preencha dentro do modal"] | label:has-text("Campo dentro do modal")'
        page.click('#campo-modal')
        ' Passo 29: fill'
        ' Seletores: #campo-modal | input[placeholder="Preencha dentro do modal"] | label:has-text("Campo dentro do modal")'
        page.fill('#campo-modal', self.data['steps'][28]['value'])
        ' Passo 30: click'
        ' Seletores: #btn-confirmar-modal | button:has-text("Confirmar") | button.btn.btn-primary'
        page.click('#btn-confirmar-modal')
        ' Passo 31: click'
        ' Seletores: #btn-mostrar-overlay | button:has-text("Overlay bloqueando clique (STA-002)") | button:has-text("Mostrar Overlay")'
        page.click('#btn-mostrar-overlay')
        ' Passo 32: click'
        ' Seletores: #btn-fechar-overlay | button:has-text("Fechar Overlay") | button.btn'
        page.click('#btn-fechar-overlay')
        ' Passo 33: click'
        ' Seletores: #btn-alert | button:has-text("Alert") | button.btn.btn-primary'
        page.click('#btn-alert')
        ' Passo 34: click'
        ' Seletores: #btn-confirm | button:has-text("Confirm") | button.btn.btn-primary'
        page.click('#btn-confirm')
        ' Passo 35: click'
        ' Seletores: #btn-prompt | button:has-text("Prompt") | button.btn.btn-primary'
        page.click('#btn-prompt')
        ' Passo 36: click'
        ' Seletores: button:has-text("Remover") | button.btn.btn-danger'
        page.click('button:has-text("Remover")')
        ' Passo 37: click'
        ' Seletores: #btn-reordenar | button:has-text("Lista reordenável (DOM-002)") | button:has-text("Reordenar")'
        page.click('#btn-reordenar')
        ' Passo 38: click'
        ' Seletores: #btn-carregar-conteudo | button:has-text("Conteúdo carregado sob demanda (DOM-005)") | button:has-text("Carregar Conteúdo")'
        page.click('#btn-carregar-conteudo')
        ' Passo 39: click'
        ' Seletores: #campo-dinamico | input[placeholder="Campo carregado sob demanda"]'
        page.click('#campo-dinamico')
        ' Passo 40: fill'
        ' Seletores: #campo-dinamico | input[placeholder="Campo carregado sob demanda"]'
        page.fill('#campo-dinamico', self.data['steps'][39]['value'])
        ' Passo 41: click'
        ' Seletores: #nome-completo | input[name="nome"] | label:has-text("Nome completo")'
        page.click('#nome-completo')
        ' Passo 42: fill'
        ' Seletores: #nome-completo | input[name="nome"] | label:has-text("Nome completo")'
        page.fill('#nome-completo', self.data['steps'][41]['value'])
        ' Passo 43: fill'
        ' Seletores: #email-contato | input[name="email"] | label:has-text("E-mail")'
        page.fill('#email-contato', self.data['steps'][42]['value'])
        ' Passo 44: fill'
        ' Seletores: #telefone | input[name="telefone"] | input[placeholder="(00) 00000-0000"]'
        page.fill('#telefone', self.data['steps'][43]['value'])
        ' Passo 45: select'
        ' Seletores: #select-estado | select[name="estado"] | label:has-text("Estado")'
        page.select_option('#select-estado', label='São Paulo')
        ' Passo 46: click'
        ' Seletores: input[name="genero"]'
        page.click('input[name="genero"]')
        ' Passo 47: click'
        ' Seletores: input[name="interesse"]'
        page.click('input[name="interesse"]')
        ' Passo 48: click'
        ' Seletores: #mensagem | textarea[name="mensagem"] | textarea[placeholder="Digite sua mensagem"]'
        page.click('#mensagem')
        ' Passo 49: fill'
        ' Seletores: #mensagem | textarea[name="mensagem"] | textarea[placeholder="Digite sua mensagem"]'
        page.fill('#mensagem', self.data['steps'][48]['value'])
        ' Passo 50: click'
        ' Seletores: button:has-text("Enviar") | button.btn.btn-primary'
        page.click('button:has-text("Enviar")')