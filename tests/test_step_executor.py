"""TestForge — StepExecutor tests."""
import pytest
from unittest.mock import MagicMock
from testforge.runner.step_executor import StepExecutor
from tests.helpers.incremental_fakes import make_fake_step


def _mock_page():
    page = MagicMock()
    page.url = "http://localhost"
    locator = MagicMock()
    locator.first = MagicMock()
    locator.first.get_attribute = MagicMock(return_value=None)
    page.locator = MagicMock(return_value=locator)
    return page


def test_execute_click_success():
    page = _mock_page()
    ex = StepExecutor(page)
    step = make_fake_step("click", "#btn")
    sel = ex.execute(step)
    assert sel == "#btn"
    page.click.assert_called_once()


def test_execute_click_raises_for_missing_selector():
    page = _mock_page()
    ex = StepExecutor(page)
    step = make_fake_step("click", selector="")
    with pytest.raises(ValueError):
        ex.execute(step)


def test_execute_fill_success():
    page = _mock_page()
    ex = StepExecutor(page)
    step = make_fake_step("fill", "#name", value="Joao")
    sel = ex.execute(step)
    assert sel == "#name"
    # CS-1: fill now goes through _fill_masked → el.fill on the locator,
    # not page.fill. The locator returned by page.locator(...).first is
    # the el that receives the fill call.
    page.locator.return_value.first.fill.assert_called_once()


def test_execute_select_option_uses_select_option_not_fill():
    page = _mock_page()
    ex = StepExecutor(page)
    step = make_fake_step("select_option", selector="select[name=uf]", value="MT")
    sel = ex.execute(step)
    assert sel == "select[name=uf]"
    page.select_option.assert_called_once()
    page.fill.assert_not_called()
    page.click.assert_not_called()


def test_execute_navigation_only_when_url_differs():
    page = _mock_page()
    page.url = "http://localhost"
    ex = StepExecutor(page)
    step = make_fake_step("navigation", selector="")
    step.url = "http://localhost"
    ex.execute(step, base_url="http://localhost")
    page.goto.assert_not_called()

class TestHotfix16FillInputClearAndDigits:
    """Hotfix 16: _fill_input must clear field and strip to raw digits."""

    def _masked_input(self, currencymask=True, date=False):
        page = MagicMock()
        page.url = "http://localhost"
        el = MagicMock()
        el.count = MagicMock(return_value=1)
        el.get_attribute = MagicMock(side_effect=lambda attr: (
            "true" if attr == "currencymask" and currencymask
            else ("DD/MM/AAAA" if attr == "placeholder" and date else None)
        ))
        page.locator = MagicMock(return_value=el)
        return page, el

    def test_currency_mask_clears_with_triple_click(self):
        page, el = self._masked_input(currencymask=True)
        ex = StepExecutor(page)
        assert ex._fill_input(page, label="Renda", value="1.000,00") is True
        # First click focuses; triple-click selects all.
        click_calls = el.click.call_args_list
        assert any(
            call.kwargs.get("click_count") == 3 for call in click_calls
        ), f"expected click_count=3, got {click_calls}"

    def test_currency_mask_types_raw_digits_not_inflated(self):
        page, el = self._masked_input(currencymask=True)
        ex = StepExecutor(page)
        ex._fill_input(page, label="Renda", value="1.000,00")
        # Must type "100000" — the raw digits — NOT "10000000".
        typed = [c.args[0] for c in el.press_sequentially.call_args_list]
        assert typed == ["100000"], f"got {typed}"

    def test_currency_mask_pure_digits_pass_through(self):
        page, el = self._masked_input(currencymask=True)
        ex = StepExecutor(page)
        ex._fill_input(page, label="Renda", value="500000")
        typed = [c.args[0] for c in el.press_sequentially.call_args_list]
        assert typed == ["500000"], f"got {typed}"

    def test_date_mask_keeps_slashes(self):
        page, el = self._masked_input(currencymask=False, date=True)
        ex = StepExecutor(page)
        ex._fill_input(page, label="Nascimento", value="03/03/1994")
        typed = [c.args[0] for c in el.press_sequentially.call_args_list]
        assert typed == ["03/03/1994"], f"got {typed}"

    def test_date_mask_clears_with_triple_click(self):
        page, el = self._masked_input(currencymask=False, date=True)
        ex = StepExecutor(page)
        ex._fill_input(page, label="Nascimento", value="03/03/1994")
        assert any(
            c.kwargs.get("click_count") == 3 for c in el.click.call_args_list
        )

    def test_non_masked_uses_fill(self):
        page = MagicMock()
        el = MagicMock()
        el.count = MagicMock(return_value=1)
        el.get_attribute = MagicMock(return_value=None)
        page.locator = MagicMock(return_value=el)
        ex = StepExecutor(page)
        assert ex._fill_input(page, label="Nome", value="Joao") is True
        el.fill.assert_called_once()


class TestHotfix17PlaceholderMaskFallback:
    """Hotfix 17: currency mask detected by placeholder when attribute missing."""

    def _placeholder_input(self, placeholder):
        page = MagicMock()
        page.url = "http://localhost"
        el = MagicMock()
        el.count = MagicMock(return_value=1)
        el.get_attribute = MagicMock(side_effect=lambda attr: (
            placeholder if attr == "placeholder" else None
        ))
        page.locator = MagicMock(return_value=el)
        return page, el

    def test_caixa_r_placeholder_triggers_currency_path(self):
        """Caixa SIOPI inputs use placeholder R$0,00 without currencymask attr."""
        page, el = self._placeholder_input("R$0,00")
        ex = StepExecutor(page)
        ex._fill_input(page, label="Prestação", value="1.000,00")
        # Should have typed raw digits, not the formatted string.
        typed = [c.args[0] for c in el.press_sequentially.call_args_list]
        assert typed == ["100000"], f"got {typed}"
        # And cleared via triple-click first.
        assert any(
            c.kwargs.get("click_count") == 3
            for c in el.click.call_args_list
        )

    def test_lowercase_0_00_placeholder_triggers_mask_path(self):
        page, el = self._placeholder_input("0,00")
        ex = StepExecutor(page)
        ex._fill_input(page, label="Valor", value="5.000,50")
        typed = [c.args[0] for c in el.press_sequentially.call_args_list]
        assert typed == ["500050"], f"got {typed}"

    def test_plain_text_placeholder_uses_fill(self):
        page, el = self._placeholder_input("Nome completo")
        ex = StepExecutor(page)
        ex._fill_input(page, label="Nome", value="Joao Silva")
        # No press_sequentially — non-masked path goes through el.fill
        el.fill.assert_called_once()
        el.press_sequentially.assert_not_called()


class TestCS1ConvergenceContract:
    """CS-1: all four fill helpers converge to _fill_masked.

    Regression guard: any future divergence (a contributor reintroducing
    inline mask logic in one helper) breaks this contract test.
    """

    def _attr_input(self, attrs):
        page = MagicMock()
        el = MagicMock()
        el.count = MagicMock(return_value=1)
        el.first = el
        el.get_attribute = MagicMock(side_effect=lambda a: attrs.get(a))
        page.locator = MagicMock(return_value=el)
        return page, el

    def test_press_sequentially_lives_in_one_place(self):
        """Source-level contract: grep finds press_sequentially exactly once."""
        from pathlib import Path
        src = (
            Path(__file__).resolve().parent.parent
            / "src/testforge/runner/step_executor.py"
        ).read_text()
        assert src.count("press_sequentially") == 1, (
            "press_sequentially must live in exactly one place "
            "(_fill_masked). Found multiple — a fill helper is "
            "reimplementing the masked-input path. Consolidate it."
        )

    def test_all_helpers_produce_same_currency_digits(self):
        """Currency value '1.000,00' through every helper presses '100000'."""
        attrs = {"placeholder": "R$0,00"}

        # _fill_input
        page, el = self._attr_input(attrs)
        ex = StepExecutor(page)
        ex._fill_input(page, label="Renda", value="1.000,00")
        a = [c.args[0] for c in el.press_sequentially.call_args_list]

        # _fill_by_aria_label
        page, el = self._attr_input(attrs)
        ex = StepExecutor(page)
        step = make_fake_step("click", "#x")
        ex._fill_by_aria_label(step, {"Renda": "1.000,00"})
        b = [c.args[0] for c in el.press_sequentially.call_args_list]

        # _try_data_fill — needs target.label/placeholder + matching key
        page, el = self._attr_input(attrs)
        ex = StepExecutor(page)
        step = make_fake_step("click", "#x")
        step.target.label = "Renda"
        ex._try_data_fill(step, "#x", {"Renda": "1.000,00"})
        c = [c.args[0] for c in el.press_sequentially.call_args_list]

        # _execute_fill — same shape via the action path
        page, el = self._attr_input(attrs)
        ex = StepExecutor(page)
        step = make_fake_step("fill", "#x", value="1.000,00")
        ex._execute_fill(step, ["#x"], data_values=None, field_value_map=None)
        d = [c.args[0] for c in el.press_sequentially.call_args_list]

        assert a == b == c == d == ["100000"], (
            f"divergent fill paths: _fill_input={a} _fill_by_aria_label={b} "
            f"_try_data_fill={c} _execute_fill={d}"
        )

    def test_all_helpers_clear_with_triple_click(self):
        """All four helpers clear the field before typing (currency case)."""
        attrs = {"placeholder": "R$0,00"}

        def click_counts(el):
            return [c.kwargs.get("click_count") for c in el.click.call_args_list]

        page, el = self._attr_input(attrs)
        StepExecutor(page)._fill_input(page, label="Renda", value="500")
        assert 3 in click_counts(el)

        page, el = self._attr_input(attrs)
        step = make_fake_step("click", "#x")
        StepExecutor(page)._fill_by_aria_label(step, {"Renda": "500"})
        assert 3 in click_counts(el)

        page, el = self._attr_input(attrs)
        step = make_fake_step("click", "#x")
        step.target.label = "Renda"
        StepExecutor(page)._try_data_fill(step, "#x", {"Renda": "500"})
        assert 3 in click_counts(el)

        page, el = self._attr_input(attrs)
        step = make_fake_step("fill", "#x", value="500")
        StepExecutor(page)._execute_fill(step, ["#x"], data_values=None, field_value_map=None)
        assert 3 in click_counts(el)


class TestHotfix19FieldValueMapDataclassUnwrap:
    """Hotfix 19 / CS-4c: _resolve_field_value must unwrap FieldValueMap
    dataclass instances, not str() them. The previous code typed the
    dataclass __repr__ into masked inputs, producing ~378-char values
    with ~19 digits that the mask rendered as junk."""

    def test_unwraps_dataclass_entry_by_exact_key(self):
        from testforge.runner.step_executor import StepExecutor
        from testforge.semantic.model import FieldValueMap
        from tests.helpers.incremental_fakes import make_fake_step
        page = MagicMock()
        ex = StepExecutor(page)
        step = make_fake_step("click", "#x")
        step.target.accessible_name = "Prestação desejada *"
        fvm = {
            "Prestação desejada *": FieldValueMap(
                field_key="prestação_desejada_*",
                value="1.000,00",
                intention="fill Prestação desejada * with '1.000,00' (from final_state)",
                identifiers={"placeholder": "R$0,00"},
                source="final_state",
                step_index=12,
            ),
        }
        val, intention = ex._resolve_field_value(step, {}, fvm)
        assert val == "1.000,00", f"got {val!r}"
        assert "Prestação" in intention or intention == "fill Prestação desejada * with '1.000,00' (from final_state)"

    def test_unwraps_dataclass_entry_by_canonical_key(self):
        from testforge.runner.step_executor import StepExecutor
        from testforge.semantic.model import FieldValueMap
        from tests.helpers.incremental_fakes import make_fake_step
        page = MagicMock()
        ex = StepExecutor(page)
        step = make_fake_step("click", "#x")
        step.target.accessible_name = "Prestação desejada *"
        # Key is the canonical form, target identifier is the raw form.
        fvm = {
            "prestação_desejada_*": FieldValueMap(
                field_key="prestação_desejada_*",
                value="1.000,00",
                source="final_state",
            ),
        }
        val, _ = ex._resolve_field_value(step, {}, fvm)
        assert val == "1.000,00", f"got {val!r}"

    def test_does_not_type_dataclass_repr(self):
        """Regression guard: the resolved value must never be a
        ~378-char dataclass __repr__."""
        from testforge.runner.step_executor import StepExecutor
        from testforge.semantic.model import FieldValueMap
        from tests.helpers.incremental_fakes import make_fake_step
        page = MagicMock()
        ex = StepExecutor(page)
        step = make_fake_step("click", "#x")
        step.target.accessible_name = "Prestação desejada *"
        fvm = {
            "prestação_desejada_*": FieldValueMap(
                field_key="prestação_desejada_*",
                value="1.000,00",
                intention="x" * 200,
                identifiers={"a" * 50: "b" * 50},
            ),
        }
        val, _ = ex._resolve_field_value(step, {}, fvm)
        # __repr__ would be > 200 chars; the unwrapped value is 8.
        assert len(val) == 8
        assert "FieldValueMap" not in val

    def test_dict_entry_still_works(self):
        """Back-compat: plain dicts (legacy shape) still unwrap correctly."""
        from testforge.runner.step_executor import StepExecutor
        from tests.helpers.incremental_fakes import make_fake_step
        page = MagicMock()
        ex = StepExecutor(page)
        step = make_fake_step("click", "#x")
        step.target.accessible_name = "Renda"
        fvm = {"Renda": {"value": "5000", "intention": "fill renda"}}
        val, intention = ex._resolve_field_value(step, {}, fvm)
        assert val == "5000"
        assert intention == "fill renda"

    def test_data_values_substring_match_unwraps(self):
        from testforge.runner.step_executor import StepExecutor
        from tests.helpers.incremental_fakes import make_fake_step
        page = MagicMock()
        ex = StepExecutor(page)
        step = make_fake_step("click", "#x")
        step.target.accessible_name = "Prestação"
        data_values = {"Prestação desejada": "1.000,00"}
        val, _ = ex._resolve_field_value(step, data_values, {})
        assert val == "1.000,00"
