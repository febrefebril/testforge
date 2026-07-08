import pytest
import json
from pathlib import Path
from playwright.sync_api import Page
from playwright.sync_api import expect

class Gravacao-Manual:
    DATA_PATH = Path(__file__).with_suffix('.data.json')

    @pytest.fixture(autouse=True)
    def setup(self, page: Page):
        self.page = page
        with open(self.DATA_PATH) as f:
            self.data = json.load(f)

    def test_run(self, page: Page):
        """ Passo 1: click"""
        ' Seletores: #secao-input | section:has-text("Campo sem ID (SEL-006)") | section:has-text("Input e Interação Especializada\nINP-007 | INP-009 | INP-010 | INP-002 | INP-005 | INP-006\n\n\n  \n  \n    Máscara de input —")'
        page.goto('http://localhost:8080/')
        ' Passo 2: click'
        ' Seletores: input[placeholder="sem id, sem name"] | label:has-text("Campo sem ID (SEL-006)") | span:has-text("Campo sem ID (SEL-006)")'
        page.click('input[placeholder="sem id, sem name"]')
        ' Passo 3: fill'
        ' Seletores: input[placeholder="sem id, sem name"] | label:has-text("Campo sem ID (SEL-006)") | span:has-text("Campo sem ID (SEL-006)")'
        page.fill('input[placeholder="sem id, sem name"]', self.data['steps'][2]['value'])
        ' Passo 4: fill'
        ' Seletores: input[placeholder="sem id, sem name"] | label:has-text("Campo sem ID (SEL-006)") | span:has-text("Campo sem ID (SEL-006)")'
        page.fill('input[placeholder="sem id, sem name"]', self.data['steps'][3]['value'])
        ' Passo 5: click'
        ' Seletores: #campo-label-for | label:has-text("Label sem for (SEL-010)") | span:has-text("Label sem for (SEL-010)")'
        page.click('#campo-label-for')
        ' Passo 6: fill'
        ' Seletores: #campo-label-for | label:has-text("Label sem for (SEL-010)") | span:has-text("Label sem for (SEL-010)")'
        page.fill('#campo-label-for', self.data['steps'][5]['value'])
        ' Passo 7: fill'
        ' Seletores: #campo-label-for | label:has-text("Label sem for (SEL-010)") | span:has-text("Label sem for (SEL-010)")'
        page.fill('#campo-label-for', self.data['steps'][6]['value'])
        ' Passo 8: click'
        ' Seletores: label:has-text("Opção A") | label:has-text("Opção A") | label.radio-label-custom'
        page.click('label:has-text("Opção A")')
        ' Passo 9: click'
        ' Seletores: label:has-text("Opção A") | label:has-text("Opção B") | label.radio-label-custom'
        page.click('label:has-text("Opção A")')
        ' Passo 10: click'
        ' Seletores: button:has-text("Confirmar") | button.btn.btn-primary.acao-duplicada'
        page.click('button:has-text("Confirmar")')
        ' Passo 11: click'
        ' Seletores: button:has-text("Confirmar") | button.btn.btn-primary.acao-duplicada'
        page.click('button:has-text("Confirmar")')
        ' Passo 12: click'
        ' Seletores: #secao-seletores > div:nth-of-type(1) > div:nth-of-type(5) > div:nth-of-type(1) > span:nth-of-type(1) | span:has-text("Clique aqui")'
        page.click('#secao-seletores > div:nth-of-type(1) > div:nth-of-type(5) > div:nth-of-type(1) > span:nth-of-type(1)')
        ' Passo 13: click'
        ' Seletores: #btn-fora-form | button:has-text("Botão fora do <form> (SEL-007)") | button:has-text("Ação fora do form")'
        page.click('#btn-fora-form')
        ' Passo 14: click'
        ' Seletores: #campo-cpf | input[placeholder="000.000.000-00"] | label:has-text("Máscara de input — CPF (INP-007)")'
        page.click('#campo-cpf')
        ' Passo 15: fill'
        ' Seletores: #campo-cpf | input[placeholder="000.000.000-00"] | label:has-text("Máscara de input — CPF (INP-007)")'
        page.fill('#campo-cpf', self.data['steps'][14]['value'])
        ' Passo 16: fill'
        ' Seletores: #campo-cpf | input[placeholder="000.000.000-00"] | label:has-text("Máscara de input — CPF (INP-007)")'
        page.fill('#campo-cpf', self.data['steps'][15]['value'])
        ' Passo 17: click'
        ' Seletores: a[href="#"] | a:has-text("5") | a.ui-state-default.ui-state-hover'
        page.click('a[href="#"]')
        ' Passo 18: click'
        ' Seletores: #campo-combobox | input[placeholder="Digite ou selecione"]'
        page.click('#campo-combobox')
        ' Passo 19: click'
        ' Seletores: div:has-text("Java") | div.combobox-item'
        page.click('div:has-text("Java")')
        ' Passo 20: click'
        ' Seletores: #campo-upload | label:has-text("Upload de arquivo (INP-002)") | span:has-text("Upload de arquivo (INP-002)")'
        page.click('#campo-upload')
        ' Passo 21: upload'
        ' Seletores: #campo-upload | label:has-text("Upload de arquivo (INP-002)") | span:has-text("Upload de arquivo (INP-002)")'
        page.set_input_files('#campo-upload', 'RedeDivergente.org')
        ' Passo 22: click'
        ' Seletores: #campo-richedit | div:has-text("Rich text / contenteditable (INP-006)") | div:has-text("Digite aqui...")'
        page.click('#campo-richedit')
        ' Passo 23: fill'
        ' Seletores: #campo-autocomplete | input[placeholder="Digite uma cidade"] | label:has-text("Autocomplete jQuery UI (TIM-006 / INP-010)")'
        page.fill('#campo-autocomplete', self.data['steps'][22]['value'])
        ' Passo 24: fill'
        ' Seletores: #campo-autocomplete | input[placeholder="Digite uma cidade"] | label:has-text("Autocomplete jQuery UI (TIM-006 / INP-010)")'
        page.fill('#campo-autocomplete', self.data['steps'][23]['value'])
        ' Passo 25: click'
        ' Seletores: #ui-id-5 | div:has-text("Goiânia") | div.ui-menu-item-wrapper.ui-state-active'
        page.click('#ui-id-5')
        ' Passo 26: fill'
        ' Seletores: #campo-autocomplete | input[placeholder="Digite uma cidade"] | label:has-text("Autocomplete jQuery UI (TIM-006 / INP-010)")'
        page.fill('#campo-autocomplete', self.data['steps'][25]['value'])
        ' Passo 27: click'
        ' Seletores: #campo-lazy | input[placeholder="Campo carregado tardiamente"]'
        page.click('#campo-lazy')
        ' Passo 28: click'
        ' Seletores: #campo-lazy | input[placeholder="Campo carregado tardiamente"]'
        page.click('#campo-lazy')
        ' Passo 29: fill'
        ' Seletores: #campo-lazy | input[placeholder="Campo carregado tardiamente"]'
        page.fill('#campo-lazy', self.data['steps'][28]['value'])
        ' Passo 30: fill'
        ' Seletores: #campo-lazy | input[placeholder="Campo carregado tardiamente"]'
        page.fill('#campo-lazy', self.data['steps'][29]['value'])
        ' Passo 31: fill'
        ' Seletores: #campo-lazy | input[placeholder="Campo carregado tardiamente"]'
        page.fill('#campo-lazy', self.data['steps'][30]['value'])
        ' Passo 32: fill'
        ' Seletores: #campo-lazy | input[placeholder="Campo carregado tardiamente"]'
        page.fill('#campo-lazy', self.data['steps'][31]['value'])
        ' Passo 33: select'
        ' Seletores: #select-assincrono | label:has-text("Select com opções carregadas via JS (TIM-006)") | span:has-text("Select com opções carregadas via JS (TIM-006)")'
        page.select_option('#select-assincrono', label='Opção 1')
        ' Passo 34: click'
        ' Seletores: #shadow-host | div:has-text("Shadow DOM aberto (CTX-003)") | div:has-text("Shadow DOM será anexado via JS")'
        page.click('#shadow-host')
        ' Passo 35: click'
        ' Seletores: #shadow-host | div:has-text("Shadow DOM aberto (CTX-003)") | div:has-text("Shadow DOM será anexado via JS")'
        page.click('#shadow-host')
        ' Passo 36: click'
        ' Seletores: #shadow-host | div:has-text("Shadow DOM aberto (CTX-003)") | div:has-text("Shadow DOM será anexado via JS")'
        page.click('#shadow-host')
        ' Passo 37: click'
        ' Seletores: #shadow-host | div:has-text("Shadow DOM aberto (CTX-003)") | div:has-text("Shadow DOM será anexado via JS")'
        page.click('#shadow-host')
        ' Passo 38: click'
        ' Seletores: #btn-abrir-modal | button:has-text("Modal/dialog (CTX-006)") | button:has-text("Abrir Modal")'
        page.click('#btn-abrir-modal')
        ' Passo 39: click'
        ' Seletores: #campo-modal | input[placeholder="Preencha dentro do modal"] | label:has-text("Campo dentro do modal")'
        page.click('#campo-modal')
        ' Passo 40: fill'
        ' Seletores: #campo-modal | input[placeholder="Preencha dentro do modal"] | label:has-text("Campo dentro do modal")'
        page.fill('#campo-modal', self.data['steps'][39]['value'])
        ' Passo 41: fill'
        ' Seletores: #campo-modal | input[placeholder="Preencha dentro do modal"] | label:has-text("Campo dentro do modal")'
        page.fill('#campo-modal', self.data['steps'][40]['value'])
        ' Passo 42: click'
        ' Seletores: #btn-confirmar-modal | button:has-text("Confirmar") | button.btn.btn-primary'
        page.click('#btn-confirmar-modal')
        ' Passo 43: click'
        ' Seletores: #btn-mostrar-overlay | button:has-text("Overlay bloqueando clique (STA-002)") | button:has-text("Mostrar Overlay")'
        page.click('#btn-mostrar-overlay')
        ' Passo 44: click'
        ' Seletores: #btn-fechar-overlay | button:has-text("Fechar Overlay") | button.btn'
        page.click('#btn-fechar-overlay')
        ' Passo 45: click'
        ' Seletores: #btn-atras-overlay | button:has-text("Overlay bloqueando clique (STA-002)") | button:has-text("Clicar (bloqueado por overlay)")'
        page.click('#btn-atras-overlay')
        ' Passo 46: click'
        ' Seletores: #btn-alert | button:has-text("Alert") | button.btn.btn-primary'
        page.click('#btn-alert')
        ' Passo 47: click'
        ' Seletores: #btn-confirm | button:has-text("Confirm") | button.btn.btn-primary'
        page.click('#btn-confirm')
        ' Passo 48: click'
        ' Seletores: #btn-prompt | button:has-text("Prompt") | button.btn.btn-primary'
        page.click('#btn-prompt')
        ' Passo 49: click'
        ' Seletores: button:has-text("Remover") | button.btn.btn-danger'
        page.click('button:has-text("Remover")')
        ' Passo 50: click'
        ' Seletores: button:has-text("Remover") | button.btn.btn-danger'
        page.click('button:has-text("Remover")')
        ' Passo 51: click'
        ' Seletores: div:has-text("Item A Remover") | div.item-lista'
        page.click('div:has-text("Item A Remover")')
        ' Passo 52: click'
        ' Seletores: #btn-reordenar | button:has-text("Lista reordenável (DOM-002)") | button:has-text("Reordenar")'
        page.click('#btn-reordenar')
        ' Passo 53: click'
        ' Seletores: #btn-carregar-conteudo | button:has-text("Conteúdo carregado sob demanda (DOM-005)") | button:has-text("Carregar Conteúdo")'
        page.click('#btn-carregar-conteudo')
        ' Passo 54: click'
        ' Seletores: #campo-dinamico | input[placeholder="Campo carregado sob demanda"]'
        page.click('#campo-dinamico')
        ' Passo 55: fill'
        ' Seletores: #campo-dinamico | input[placeholder="Campo carregado sob demanda"]'
        page.fill('#campo-dinamico', self.data['steps'][54]['value'])
        ' Passo 56: click'
        ' Seletores: #btn-dinamico | button:has-text("Botão dinâmico") | button.btn.btn-primary'
        page.click('#btn-dinamico')
        ' Passo 57: click'
        ' Seletores: #nome-completo | input[name="nome"] | label:has-text("Nome completo")'
        page.click('#nome-completo')
        ' Passo 58: fill'
        ' Seletores: #nome-completo | input[name="nome"] | label:has-text("Nome completo")'
        page.fill('#nome-completo', self.data['steps'][57]['value'])
        ' Passo 59: fill'
        ' Seletores: #email-contato | input[name="email"] | label:has-text("E-mail")'
        page.fill('#email-contato', self.data['steps'][58]['value'])
        ' Passo 60: fill'
        ' Seletores: #email-contato | input[name="email"] | label:has-text("E-mail")'
        page.fill('#email-contato', self.data['steps'][59]['value'])
        ' Passo 61: fill'
        ' Seletores: #email-contato | input[name="email"] | label:has-text("E-mail")'
        page.fill('#email-contato', self.data['steps'][60]['value'])
        ' Passo 62: fill'
        ' Seletores: #telefone | input[name="telefone"] | input[placeholder="(00) 00000-0000"]'
        page.fill('#telefone', self.data['steps'][61]['value'])
        ' Passo 63: fill'
        ' Seletores: #telefone | input[name="telefone"] | input[placeholder="(00) 00000-0000"]'
        page.fill('#telefone', self.data['steps'][62]['value'])
        ' Passo 64: fill'
        ' Seletores: #telefone | input[name="telefone"] | input[placeholder="(00) 00000-0000"]'
        page.fill('#telefone', self.data['steps'][63]['value'])
        ' Passo 65: fill'
        ' Seletores: #telefone | input[name="telefone"] | input[placeholder="(00) 00000-0000"]'
        page.fill('#telefone', self.data['steps'][64]['value'])
        ' Passo 66: fill'
        ' Seletores: #telefone | input[name="telefone"] | input[placeholder="(00) 00000-0000"]'
        page.fill('#telefone', self.data['steps'][65]['value'])
        ' Passo 67: select'
        ' Seletores: #select-estado | select[name="estado"] | label:has-text("Estado")'
        page.select_option('#select-estado', label='Distrito Federal')
        ' Passo 68: click'
        ' Seletores: input[name="genero"]'
        page.click('input[name="genero"]')
        ' Passo 69: click'
        ' Seletores: input[name="interesse"]'
        page.click('input[name="interesse"]')
        ' Passo 70: click'
        ' Seletores: #mensagem | textarea[name="mensagem"] | textarea[placeholder="Digite sua mensagem"]'
        page.click('#mensagem')
        ' Passo 71: fill'
        ' Seletores: #mensagem | textarea[name="mensagem"] | textarea[placeholder="Digite sua mensagem"]'
        page.fill('#mensagem', self.data['steps'][70]['value'])
        ' Passo 72: fill'
        ' Seletores: #mensagem | textarea[name="mensagem"] | textarea[placeholder="Digite sua mensagem"]'
        page.fill('#mensagem', self.data['steps'][71]['value'])
        ' Passo 73: fill'
        ' Seletores: #mensagem | textarea[name="mensagem"] | textarea[placeholder="Digite sua mensagem"]'
        page.fill('#mensagem', self.data['steps'][72]['value'])
        ' Passo 74: fill'
        ' Seletores: #mensagem | textarea[name="mensagem"] | textarea[placeholder="Digite sua mensagem"]'
        page.fill('#mensagem', self.data['steps'][73]['value'])
        ' Passo 75: fill'
        ' Seletores: #mensagem | textarea[name="mensagem"] | textarea[placeholder="Digite sua mensagem"]'
        page.fill('#mensagem', self.data['steps'][74]['value'])
        ' Passo 76: fill'
        ' Seletores: #mensagem | textarea[name="mensagem"] | textarea[placeholder="Digite sua mensagem"]'
        page.fill('#mensagem', self.data['steps'][75]['value'])
        ' Passo 77: fill'
        ' Seletores: #mensagem | textarea[name="mensagem"] | textarea[placeholder="Digite sua mensagem"]'
        page.fill('#mensagem', self.data['steps'][76]['value'])
        ' Passo 78: fill'
        ' Seletores: #mensagem | textarea[name="mensagem"] | textarea[placeholder="Digite sua mensagem"]'
        page.fill('#mensagem', self.data['steps'][77]['value'])
        ' Passo 79: fill'
        ' Seletores: #mensagem | textarea[name="mensagem"] | textarea[placeholder="Digite sua mensagem"]'
        page.fill('#mensagem', self.data['steps'][78]['value'])
        ' Passo 80: click'
        ' Seletores: button:has-text("Enviar") | button.btn.btn-primary'
        page.click('button:has-text("Enviar")')
        ' Passo 81: assert'
        ' Seletores: #mensagem | textarea[name="mensagem"] | textarea[placeholder="Digite sua mensagem"]'
        expect(page.locator('#mensagem')).to_contain_text('')