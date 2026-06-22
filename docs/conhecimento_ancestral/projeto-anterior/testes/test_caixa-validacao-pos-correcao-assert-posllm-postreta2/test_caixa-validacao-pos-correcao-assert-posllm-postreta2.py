import pytest
import json
from pathlib import Path
from playwright.sync_api import Page
from playwright.sync_api import expect

class TestcaixaValidacaoPosCorrecaoAssertPosllmPostreta2:
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
        ' Seletores: div[role="button"]:has-text("attach_money Pela prestaçãoSei quanto posso pagar por mês Descubra qual imóvel cabe no seu bolso com essa parcela") | div:has-text("attach_money Pela prestaçãoSei quanto posso pagar por mês Descubra qual imóvel cabe no seu bolso com essa parcela") | div.flex.flex-col.items-center.text-center.bg-white.rounded-2xl.border.w-full.max-w-[346px].cursor-pointer.transition.hover:border-primary-90.hover:shadow-[0_2px_8px_rgba(0,0,0,0.12)].border-grayscale-50'
        for _sel in ['div[role="button"]:has-text("attach_money Pela prestaçãoSei quanto posso pagar por mês Descubra qual imóvel cabe no seu bolso com essa parcela")', 'div:has-text("attach_money Pela prestaçãoSei quanto posso pagar por mês Descubra qual imóvel cabe no seu bolso com essa parcela")', 'div.flex.flex-col.items-center.text-center.bg-white.rounded-2xl.border.w-full.max-w-[346px].cursor-pointer.transition.hover:border-primary-90.hover:shadow-[0_2px_8px_rgba(0,0,0,0.12)].border-grayscale-50']:
            try:
                page.click(_sel)
                break
            except Exception:
                continue
        else:
            raise AssertionError('click falhou: ' + str(['div[role="button"]:has-text("attach_money Pela prestaçãoSei quanto posso pagar por mês Descubra qual imóvel cabe no seu bolso com essa parcela")', 'div:has-text("attach_money Pela prestaçãoSei quanto posso pagar por mês Descubra qual imóvel cabe no seu bolso com essa parcela")', 'div.flex.flex-col.items-center.text-center.bg-white.rounded-2xl.border.w-full.max-w-[346px].cursor-pointer.transition.hover:border-primary-90.hover:shadow-[0_2px_8px_rgba(0,0,0,0.12)].border-grayscale-50']))
        ' Passo 3: click'
        ' Seletores: span.mat-mdc-button-touch-target'
        for _sel in ['span.mat-mdc-button-touch-target']:
            try:
                page.click(_sel)
                break
            except Exception:
                continue
        else:
            raise AssertionError('click falhou: ' + str(['span.mat-mdc-button-touch-target']))
        ' Passo 4: click'
        ' Seletores: button[aria-label="Choose month and year"] | button:has-text("JUN 2026") | button.mat-calendar-period-button.mdc-button.mat-mdc-button.mat-unthemed.mat-mdc-button-base.cdk-focused.cdk-mouse-focused'
        for _sel in ['button[aria-label="Choose month and year"]', 'button:has-text("JUN 2026")', 'button.mat-calendar-period-button.mdc-button.mat-mdc-button.mat-unthemed.mat-mdc-button-base.cdk-focused.cdk-mouse-focused']:
            try:
                page.click(_sel)
                break
            except Exception:
                continue
        else:
            raise AssertionError('click falhou: ' + str(['button[aria-label="Choose month and year"]', 'button:has-text("JUN 2026")', 'button.mat-calendar-period-button.mdc-button.mat-mdc-button.mat-unthemed.mat-mdc-button-base.cdk-focused.cdk-mouse-focused']))
        ' Passo 5: click'
        ' Seletores: button[aria-label="Previous 24 years"] | button.mat-calendar-previous-button.mdc-icon-button.mat-mdc-icon-button.mat-unthemed.mat-mdc-button-base.cdk-focused.cdk-mouse-focused'
        for _sel in ['button[aria-label="Previous 24 years"]', 'button.mat-calendar-previous-button.mdc-icon-button.mat-mdc-icon-button.mat-unthemed.mat-mdc-button-base.cdk-focused.cdk-mouse-focused']:
            try:
                page.click(_sel)
                break
            except Exception:
                continue
        else:
            raise AssertionError('click falhou: ' + str(['button[aria-label="Previous 24 years"]', 'button.mat-calendar-previous-button.mdc-icon-button.mat-mdc-icon-button.mat-unthemed.mat-mdc-button-base.cdk-focused.cdk-mouse-focused']))
        ' Passo 6: click'
        ' Seletores: button[aria-label="Previous 24 years"] | button.mat-calendar-previous-button.mdc-icon-button.mat-mdc-icon-button.mat-unthemed.mat-mdc-button-base.cdk-focused.cdk-mouse-focused'
        for _sel in ['button[aria-label="Previous 24 years"]', 'button.mat-calendar-previous-button.mdc-icon-button.mat-mdc-icon-button.mat-unthemed.mat-mdc-button-base.cdk-focused.cdk-mouse-focused']:
            try:
                page.click(_sel)
                break
            except Exception:
                continue
        else:
            raise AssertionError('click falhou: ' + str(['button[aria-label="Previous 24 years"]', 'button.mat-calendar-previous-button.mdc-icon-button.mat-mdc-icon-button.mat-unthemed.mat-mdc-button-base.cdk-focused.cdk-mouse-focused']))
        ' Passo 7: click'
        ' Seletores: button[aria-label="1968"] | button:has-text("1968") | button.mat-calendar-body-cell.mat-calendar-body-active'
        for _sel in ['button[aria-label="1968"]', 'button:has-text("1968")', 'button.mat-calendar-body-cell.mat-calendar-body-active']:
            try:
                page.click(_sel)
                break
            except Exception:
                continue
        else:
            raise AssertionError('click falhou: ' + str(['button[aria-label="1968"]', 'button:has-text("1968")', 'button.mat-calendar-body-cell.mat-calendar-body-active']))
        ' Passo 8: click'
        ' Seletores: button[aria-label="janeiro 1968"] | button:has-text("JAN") | button.mat-calendar-body-cell.mat-calendar-body-active'
        for _sel in ['button[aria-label="janeiro 1968"]', 'button:has-text("JAN")', 'button.mat-calendar-body-cell.mat-calendar-body-active']:
            try:
                page.click(_sel)
                break
            except Exception:
                continue
        else:
            raise AssertionError('click falhou: ' + str(['button[aria-label="janeiro 1968"]', 'button:has-text("JAN")', 'button.mat-calendar-body-cell.mat-calendar-body-active']))
        ' Passo 9: click'
        ' Seletores: button[aria-label="01/01/1968"] | button:has-text("1") | button.mat-calendar-body-cell.mat-calendar-body-active'
        for _sel in ['button[aria-label="01/01/1968"]', 'button:has-text("1")', 'button.mat-calendar-body-cell.mat-calendar-body-active']:
            try:
                page.click(_sel)
                break
            except Exception:
                continue
        else:
            raise AssertionError('click falhou: ' + str(['button[aria-label="01/01/1968"]', 'button:has-text("1")', 'button.mat-calendar-body-cell.mat-calendar-body-active']))
        ' Passo 10: click'
        ' Seletores: #mat-input-1 | input[aria-label="Prestação desejada *"] | input[placeholder="R$0,00"]'
        for _sel in ['#mat-input-1', 'input[aria-label="Prestação desejada *"]', 'input[placeholder="R$0,00"]', 'input.mat-mdc-input-element.ng-untouched.ng-pristine.ng-valid.mat-mdc-form-field-input-control.mdc-text-field__input.cdk-text-field-autofill-monitored']:
            try:
                page.click(_sel)
                break
            except Exception:
                continue
        else:
            raise AssertionError('click falhou: ' + str(['#mat-input-1', 'input[aria-label="Prestação desejada *"]', 'input[placeholder="R$0,00"]', 'input.mat-mdc-input-element.ng-untouched.ng-pristine.ng-valid.mat-mdc-form-field-input-control.mdc-text-field__input.cdk-text-field-autofill-monitored']))
        ' Passo 11: fill'
        ' Seletores: #mat-input-1 | input[aria-label="Prestação desejada *"] | input[placeholder="R$0,00"]'
        for _sel in ['#mat-input-1', 'input[aria-label="Prestação desejada *"]', 'input[placeholder="R$0,00"]', 'input.mat-mdc-input-element.ng-untouched.ng-valid.mat-mdc-form-field-input-control.mdc-text-field__input.cdk-text-field-autofill-monitored.ng-dirty']:
            try:
                page.fill(_sel, self.data['steps'][10]['value'])
                break
            except Exception:
                continue
        else:
            raise AssertionError('fill falhou: ' + str(['#mat-input-1', 'input[aria-label="Prestação desejada *"]', 'input[placeholder="R$0,00"]', 'input.mat-mdc-input-element.ng-untouched.ng-valid.mat-mdc-form-field-input-control.mdc-text-field__input.cdk-text-field-autofill-monitored.ng-dirty']))
        ' Passo 12: fill'
        ' Seletores: #mat-input-1 | input[aria-label="Prestação desejada *"] | input[placeholder="R$0,00"]'
        for _sel in ['#mat-input-1', 'input[aria-label="Prestação desejada *"]', 'input[placeholder="R$0,00"]', 'input.mat-mdc-input-element.ng-untouched.ng-valid.mat-mdc-form-field-input-control.mdc-text-field__input.cdk-text-field-autofill-monitored.ng-dirty']:
            try:
                page.fill(_sel, self.data['steps'][11]['value'])
                break
            except Exception:
                continue
        else:
            raise AssertionError('fill falhou: ' + str(['#mat-input-1', 'input[aria-label="Prestação desejada *"]', 'input[placeholder="R$0,00"]', 'input.mat-mdc-input-element.ng-untouched.ng-valid.mat-mdc-form-field-input-control.mdc-text-field__input.cdk-text-field-autofill-monitored.ng-dirty']))
        ' Passo 13: click'
        ' Seletores: span.mat-mdc-button-touch-target'
        for _sel in ['span.mat-mdc-button-touch-target']:
            try:
                page.click(_sel)
                break
            except Exception:
                continue
        else:
            raise AssertionError('click falhou: ' + str(['span.mat-mdc-button-touch-target']))
        ' Passo 14: assert'
        ' Seletores: p:has-text("R$\xa0149.699,72") | p.text-grayscale-130.text-size-small.m-0.mb-4'
        expect(page.locator('p:has-text("R$\xa0149.699,72")')).to_contain_text('R$\xa0149.699,72')