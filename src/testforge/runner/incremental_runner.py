"""TestForge — IncrementalRunner.

Executor incremental que orquestra pré-condição, execução, pós-condição,
evidência, healing com CuradorAutomatico e oracle pós-healing.

Regra central:
  CuradorAutomatico responde: "consegui executar uma alternativa?"
  IncrementalRunner responde: "essa alternativa resolveu o step?"
  Oracle responde:            "o efeito esperado apareceu?"
  PromotionGate responde:     "essa cura pode virar aprendizado?"
"""
from __future__ import annotations
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .step_result import (
    IncrementalStepResult,
    PreconditionResult,
    PostconditionResult,
    HealingAttempt,
)
from .step_precondition import StepPreconditionValidator
from .step_executor import StepExecutor
from .step_postcondition import StepPostconditionValidator
from .incremental_ui import IncrementalUI


_DANGEROUS_LOCATORS = {
    "body", "html", "button", "input", "select", "a", "div", "span",
    "text=selecione", "text=ok", "text=cancelar", "text=sim",
    "text=nao",
}


class IncrementalRunner:
    def __init__(
        self,
        script_path: str,
        headless: bool = True,
        timeout: int = 60,
        verbose: bool = False,
        data: str = "",
        browser: str = "chromium",
        stop_on_failure: bool = True,
        interactive: bool = False,
        no_healing: bool = False,
        shadow: bool = False,
        output_root: str = "runs",
        capture: bool = True,
        debug_healing: bool = False,
        verify_ssl: bool = False,
    ):
        self.script_path = script_path
        self.headless = headless
        self.timeout = timeout
        self.verbose = verbose
        self.data_path = data
        self.browser_type = browser
        self.stop_on_failure = stop_on_failure
        self.interactive = interactive
        self.no_healing = no_healing
        self.shadow_mode = shadow
        self.output_root = output_root
        self.capture_enabled = capture
        self.debug_healing = debug_healing
        self.verify_ssl = verify_ssl
        self.replay_recorder = None

        self.page = None
        self.base_url = ""
        self.recording_id = ""
        self.app_name = "web"
        self.steps = []
        self.step_results = []
        self.failed_step_indices = set()
        self._data_values = {}
        self._field_value_map = {}

        self.precondition_validator = None
        self.step_executor = None
        self.postcondition_validator = None
        self.evidence_collector = None
        self.metrics = None
        self.promotion_gate = None

        self.ui = IncrementalUI(verbose=verbose)

    def _load_script_metadata(self):
        if not os.path.exists(self.script_path):
            raise FileNotFoundError(f"Script nao encontrado: {self.script_path}")
        with open(self.script_path) as f:
            code = f.read()
        for line in code.split("\n"):
            line = line.strip()
            if line.startswith("BASE_URL"):
                try:
                    self.base_url = line.split('"')[1]
                except Exception:
                    pass
            if "source:" in line and not self.recording_id:
                tok = line.split("source:")[-1].strip().rstrip(chr(34) + chr(39) + ".")
                self.recording_id = tok

    def _load_semantic_steps(self):
        if not self.recording_id:
            return
        from testforge.semantic import RecordingNormalizer
        rec_dir = self._find_recording_dir(self.recording_id)
        if not rec_dir:
            return
        normalizer = RecordingNormalizer()
        stc = normalizer.normalize(rec_dir, f"ST-{self.recording_id}", "web", self.base_url)
        self.steps = stc.steps
        self.app_name = stc.application or "web"
        self._field_value_map = stc.field_values or {}

        # Report field-value map and suggest data file for missing values
        if self._field_value_map:
            missing = []
            print(f"  📋 {len(self._field_value_map)} campo(s) mapeado(s) com intenção")
            for key, fvm in sorted(self._field_value_map.items()):
                val_display = fvm.value if fvm.value else "<pendente>"
                if not fvm.value:
                    missing.append(key)
                print(f"    {key}: {val_display} ({fvm.intention})")
            if missing:
                template = {k: "<valor>" for k in missing}
                print(f"  [WARN] {len(missing)} campo(s) sem valor na gravação (currencymask)")
                print(f"  💡 Crie um data file: --data dados.json")
                print(f"  📋 Template: {json.dumps(template, indent=2, ensure_ascii=False)}")

    def _find_recording_dir(self, rec_id):
        # Hotfix 15: also check the package's project root so the runner
        # finds recordings even when invoked from a different CWD. Layout:
        # <repo>/src/testforge/runner/incremental_runner.py ->
        # parents[3] == <repo>/. Same anchor as the CLI's _PROJECT_ROOT.
        try:
            project_root = Path(__file__).resolve().parents[3]
        except Exception:
            project_root = None
        candidates = [
            Path.cwd() / "recordings" / rec_id,
            Path(self.script_path).parent.parent / "recordings" / rec_id,
            Path(self.script_path).parent.parent.parent / "recordings" / rec_id,
        ]
        if project_root is not None:
            candidates.append(project_root / "recordings" / rec_id)
        for c in candidates:
            if c.is_dir():
                return str(c)
        return None

    def _load_data_file(self):
        if not self.data_path:
            return
        if not os.path.exists(self.data_path):
            return
        with open(self.data_path) as f:
            raw = json.load(f)
        if "fields" in raw:
            self._data_values = raw["fields"]
        elif "scenarios" in raw:
            self._data_values = raw["scenarios"].get("default", {})
        else:
            self._data_values = raw

        # Cross-reference data_values with field_value_map: populate missing
        # field_value_map entries with matching data_values keys.
        if self._data_values and self._field_value_map:
            import re as _re
            def _norm(s):
                if not s: return ""
                return _re.sub(r'[-_\s]+', '_', s.strip().lower())
            updates = 0
            for key, val in self._data_values.items():
                ck = _norm(key)
                for fk, fvm in self._field_value_map.items():
                    if hasattr(fvm, 'value') and not fvm.value and _norm(fk) == ck:
                        fvm.value = str(val)
                        updates += 1
                    elif isinstance(fvm, dict) and not fvm.get('value'):
                        if _norm(fk) == ck:
                            fvm['value'] = str(val)
                            updates += 1
            if updates:
                print(f"  🔗 {updates} campo(s) populados do data file para field_value_map")

    def _init_components(self):
        self.precondition_validator = StepPreconditionValidator(self.page)
        self.step_executor = StepExecutor(self.page)
        self.postcondition_validator = StepPostconditionValidator(self.page)

        # ReplayRecorder: capture execution telemetry in recording-compatible format
        if self.capture_enabled and self.recording_id:
            try:
                from testforge.recorder.replay_recorder import ReplayRecorder
                self.replay_recorder = ReplayRecorder(
                    self.page,
                    self.recording_id,
                    output_root=str(Path(self.output_root).parent / "recordings"),
                )
                cap_dir = self.replay_recorder.start()
                print(f"  📹 Captura: {cap_dir}")
            except Exception as exc:
                print(f"  [WARN] ReplayRecorder: {exc}")
                self.replay_recorder = None

        try:
            from testforge.evidence import EvidenceCollector
            self.evidence_collector = EvidenceCollector(self.page)
            self.evidence_collector.start(self._run_id())
        except Exception:
            self.evidence_collector = None

        try:
            from testforge.metrics import MetricsRepository
            self.metrics = MetricsRepository()
        except Exception:
            self.metrics = None

        try:
            from testforge.promotion import PromotionGate
            self.promotion_gate = PromotionGate()
        except Exception:
            self.promotion_gate = None

    def _make_curator(self, catalog=None, step_runner=None):
        from testforge.healing import CuradorAutomatico, HealingCatalog
        from testforge.runner.fallback_runner import SmartStepRunner

        if step_runner is None:
            smart_runner = SmartStepRunner(self.page)
            def step_runner(step_data):
                strategy = step_data.get("strategy", "")
                return smart_runner.execute(step_data, strategy)

        return CuradorAutomatico(
            catalog=catalog or HealingCatalog(),
            step_runner=step_runner,
            debug_healing=getattr(self, 'debug_healing', False),
        )

    def _primary_selector(self, step):
        if step.target and getattr(step.target, "candidates", None):
            cands = step.target.candidates
            if cands:
                return cands[0].selector or ""
        return ""

    def _next_executable_step(self, step_num):
        idx = step_num
        while idx < len(self.steps):
            s = self.steps[idx]
            if not getattr(s, "skip_reason", ""):
                return s
            idx += 1
        return None

    def _describe_intention(self, step, step_num):
        target_text = ""
        if step.target:
            target_text = (
                getattr(step.target, "text", "")
                or getattr(step.target, "label", "")
                or getattr(step.target, "accessible_name", "")
                or ""
            )
        intention = f"{step.action} step {step_num}" + (f" on '{target_text}'" if target_text else "")

        # Enrich with field_value_map intention when available
        ctx = getattr(step, "context", {}) or {}
        if ctx.get("resolved_intention"):
            intention += f" [intent: {ctx['resolved_intention']}]"
        if ctx.get("resolved_value"):
            intention += f" [value: {ctx['resolved_value']}]"
        return intention

    def _build_healing_payload(self, step, step_num, original_error, failure_phase):
        if not self.evidence_collector:
            return None
        selector = self._primary_selector(step)
        text_value = ""
        if step.target:
            text_value = (
                getattr(step.target, "text", "")
                or getattr(step.target, "label", "")
                or getattr(step.target, "accessible_name", "")
                or ""
            )
        step_context = {
            "action": step.action,
            "selector": selector or "(empty)",
            "value": step.value or "",
            "text": text_value,
            "intention": self._describe_intention(step, step_num),
            "url": self.page.url,
            "framework": self.app_name or "generic",
            "step_number": step_num,
            "failure_phase": failure_phase,
            "original_error": original_error,
        }
        # Include resolved value + intention from field_value_map for healing context
        ctx = getattr(step, "context", {}) or {}
        if ctx.get("resolved_value"):
            step_context["field_value"] = ctx["resolved_value"]
        if ctx.get("resolved_intention"):
            step_context["field_intention"] = ctx["resolved_intention"]
        return self.evidence_collector.build_llm_payload(
            step_context=step_context,
            include_screenshot=False,
        )

    @staticmethod
    def _is_dangerously_generic(locator):
        if not locator:
            return True
        n = locator.strip().lower()
        if n in _DANGEROUS_LOCATORS:
            return True
        if n.startswith("/html/") or n.startswith("xpath=/html/"):
            return True
        if "nth-child" in n and len(n) < 30:
            return True
        return False

    @staticmethod
    def _is_incompatible_strategy(step, strategy):
        action = step.action
        allowed = {
            "fill": {
                "press_sequentially", "masked_input_detection",
                "semantic_locator_conversion", "label_click",
                "synthetic_click", "visibility_wait",
            },
            "click": {
                "semantic_locator_conversion", "has_text_fallback",
                "visibility_wait", "overlay_dismiss", "dialog_handler",
                "iframe_switch", "label_click", "synthetic_click",
                "xpath_fallback",
                # Masked input strategies: click on masked fields should allow
                # press_sequentially (e.g. currency/date masks that reject fill())
                "press_sequentially", "masked_input_detection",
            },
            "select_option": {
                "semantic_locator_conversion", "visibility_wait", "xpath_fallback",
            },
            "assert": {
                "semantic_locator_conversion", "has_text_fallback", "visibility_wait",
            },
        }.get(action, set())
        if not allowed:
            return False
        return strategy not in allowed

    def _validate_curator_proposal(self, outcome, step, original_selector):
        failures = []
        if outcome is None:
            return False, ["missing_outcome"]
        if not outcome.layer_used:
            failures.append("missing_layer_used")
        proposal = outcome.proposal
        if proposal:
            if not proposal.new_locator:
                failures.append("missing_new_locator")
            if proposal.confidence < 0.5:
                failures.append("low_confidence")
            if not proposal.family:
                failures.append("missing_family")
            if not proposal.taxonomy_id:
                failures.append("missing_taxonomy_id")
            if not proposal.strategy:
                failures.append("missing_strategy")
            if self._is_dangerously_generic(proposal.new_locator):
                failures.append("generic_or_dangerous_locator")
            if self._is_incompatible_strategy(step, proposal.strategy):
                failures.append("incompatible_action_strategy")
            if (
                proposal.new_locator == original_selector
                and outcome.layer_used != "L0"
                # Allow same locator when strategy changes execution approach
                # (e.g. fill → press_sequentially for masked inputs).
                # Only reject when it's a true retry of the same failed approach.
                and proposal.strategy not in (
                    "press_sequentially", "masked_input_detection",
                    "dialog_handler", "overlay_dismiss", "iframe_switch",
                )
            ):
                failures.append("same_locator_as_failed_original")
        return len(failures) == 0, failures

    def _map_curation_outcome(self, outcome, original_selector, failure_phase, original_error):
        healing = HealingAttempt(
            attempted=True,
            status=outcome.status,
            layer=outcome.layer_used or "",
            family=outcome.family or "",
            taxonomy_id=outcome.taxonomy_id or "",
            failure_phase=failure_phase,
            original_error=original_error,
            original_locator=original_selector,
            entry_id=getattr(outcome, "entry_id", "") or "",
        )
        if outcome.proposal:
            healing.strategy = outcome.proposal.strategy or ""
            healing.proposed_locator = outcome.proposal.new_locator or ""
            healing.confidence = outcome.proposal.confidence or 0.0
            healing.rationale = (outcome.proposal.rationale or "")[:300]
            healing.raw_response = outcome.proposal.raw_response or ""
        return healing

    def _validate_healing_with_oracle(self, step, step_num, result, url_before=""):
        post = self.postcondition_validator.validate(
            step=step, page=self.page,
            next_step=self._next_executable_step(step_num),
            url_before=url_before,
        )
        result.postcondition = post
        return post.passed

    def _heal_failed_step(self, step, step_num, original_error,
                          failure_phase, result, url_before=""):
        from testforge.healing import ProgressResult
        from testforge.metrics import StepOutcome

        original_selector = self._primary_selector(step)

        if self.metrics:
            self.metrics.record_step(
                StepOutcome.FAILURE_DETECTED,
                step_num=step_num, action=step.action,
                selector=original_selector or "",
            )

        if self.no_healing:
            result.status = "failed"
            result.error_message = f"Healing desativado. Erro: {original_error}"
            return result

        payload = self._build_healing_payload(
            step=step, step_num=step_num,
            original_error=original_error, failure_phase=failure_phase,
        )
        if payload is None or not payload.is_sufficient:
            result.status = "failed"
            result.error_message = (
                "Healing nao tentado: evidencia insuficiente — "
                f"{getattr(payload, 'insufficiency_reason', 'sem evidencia')}"
            )
            result.healing = HealingAttempt(
                attempted=False,
                rejection_reason=["insufficient_evidence"],
                failure_phase=failure_phase,
                original_error=original_error,
            )
            return result

        curator = self._make_curator()
        step_data = {
            "selector": original_selector or "",
            "action": step.action,
            "value": step.value or "",
            "base_url": self.base_url,
            "candidates": [
                {"selector": c.selector, "score": c.score, "strategy": c.strategy}
                for c in (step.target.candidates if step.target and step.target.candidates else [])
                if c.selector and c.selector != original_selector
            ],
        }

        if self.metrics:
            self.metrics.record_step(
                StepOutcome.HEALING_ATTEMPTED,
                step_num=step_num, action=step.action,
                selector=original_selector or "",
            )

        outcome = curator.cure(
            step_data=step_data,
            error_message=original_error,
            evidence=payload,
        )
        result.healing = self._map_curation_outcome(
            outcome=outcome,
            original_selector=original_selector,
            failure_phase=failure_phase,
            original_error=original_error,
        )

        proposal_ok, proposal_failures = self._validate_curator_proposal(
            outcome=outcome, step=step, original_selector=original_selector,
        )
        if not proposal_ok:
            if self.metrics:
                self.metrics.record_step(
                    StepOutcome.HEALING_REJECTED,
                    step_num=step_num, action=step.action,
                    family_code=result.healing.family,
                    healing_layer=result.healing.layer,
                    selector=original_selector or "",
                )
            result.status = "healing_rejected"
            result.healing.validated = False
            result.healing.rejection_reason = list(proposal_failures)
            result.error_message = "Proposta do curador rejeitada: " + ", ".join(proposal_failures)
            return result

        if outcome.status != ProgressResult.PASSED_STEP:
            if self.metrics:
                self.metrics.record_step(
                    StepOutcome.HEALING_REJECTED,
                    step_num=step_num, action=step.action,
                    family_code=outcome.family or "",
                    healing_layer=outcome.layer_used or "",
                    selector=original_selector or "",
                )
            result.status = "failed"
            result.healing.validated = False
            result.healing.rejection_reason = [
                "curator_did_not_pass_step", outcome.status
            ]
            result.error_message = (
                f"Healing nao resolveu: {outcome.status}. "
                f"{outcome.error_message or ''}"
            )
            return result

        proposed_selector = result.healing.proposed_locator or original_selector
        if self.metrics:
            self.metrics.record_step(
                StepOutcome.HEALING_APPLIED,
                step_num=step_num, action=step.action,
                family_code=outcome.family or "",
                healing_layer=outcome.layer_used or "",
                selector=proposed_selector,
            )

        if self.shadow_mode:
            result.status = "shadow_healed"
            result.healing.validated = False
            return result

        oracle_ok = self._validate_healing_with_oracle(
            step=step, step_num=step_num, result=result, url_before=url_before,
        )
        if oracle_ok:
            if self.metrics:
                self.metrics.record_step(
                    StepOutcome.ORACLE_VALIDATED,
                    step_num=step_num, action=step.action,
                    family_code=outcome.family or "",
                    healing_layer=outcome.layer_used or "",
                    selector=proposed_selector,
                )
            result.status = "healed_validated"
            result.selected_locator = proposed_selector
            result.healing.validated = True
            result.healing.oracle_passed = True
            result.healing.rejection_reason = []
            self._evaluate_healing_promotion(result)
            return result

        if self.metrics:
            self.metrics.record_step(
                StepOutcome.HEALING_REJECTED,
                step_num=step_num, action=step.action,
                family_code=outcome.family or "",
                healing_layer=outcome.layer_used or "",
                selector=proposed_selector,
            )
        result.status = "healing_rejected"
        result.healing.validated = False
        result.healing.oracle_passed = False
        post_failures = []
        if result.postcondition:
            post_failures = list(result.postcondition.failures or [])
        result.healing.rejection_reason = ["postcondition_failed"] + post_failures
        result.error_message = (
            "Healing executou, mas pos-condicao/oracle falhou: "
            f"{result.postcondition.message if result.postcondition else ''}"
        )
        return result

    def _evaluate_healing_promotion(self, result):
        if not self.promotion_gate or not result.healing:
            return
        oracle_results = []
        if result.postcondition:
            oracle_results = list(result.postcondition.oracle_results or [])
        evidence = {
            "screenshots": [
                result.evidence_before.get("screenshot"),
                result.evidence_after.get("screenshot"),
            ],
        }
        try:
            decision = self.promotion_gate.evaluate(
                oracle_results=oracle_results,
                evidence=evidence,
                uniqueness_score=1.0,
            )
            result.healing.promotion_state = decision.state.value
            result.healing.promotion_allowed = decision.allowed
            result.healing.promotion_blocks = list(decision.blocks or [])
        except Exception:
            pass

    def _capture_evidence(self, step_num, phase):
        if not self.evidence_collector:
            return {}
        step_id = f"step_{step_num:04d}"
        evidence = {}
        try:
            evidence["screenshot"] = self.evidence_collector.capture_screenshot(step_id, phase)
        except Exception:
            evidence["screenshot"] = ""
        try:
            evidence["dom"] = self.evidence_collector.capture_dom(step_id, phase)
        except Exception:
            evidence["dom"] = ""
        return evidence

    _BODY_SELECTORS = {"body", "#body", "html", "#html", "xpath=/html/body", "xpath=//body"}

    def _run_one_step(self, index, step):
        step_num = index + 1
        started = time.time()

        skip_reason = getattr(step, "skip_reason", "") or ""
        if not skip_reason and step.action == "assert":
            sel = ""
            if step.target and getattr(step.target, "candidates", None):
                sel = (step.target.candidates[0].selector or "").strip().lower()
            if sel in self._BODY_SELECTORS:
                skip_reason = "assert_on_body_element_skipped"

        if skip_reason:
            result = IncrementalStepResult(
                step_num=step_num,
                action=step.action,
                original_locator=self._primary_selector(step),
                value=step.value or "",
            )
            result.status = "skipped"
            result.skip_reason = skip_reason
            result.duration_ms = 0
            return result

        result = IncrementalStepResult(
            step_num=step_num,
            action=step.action,
            original_locator=self._primary_selector(step),
            value=step.value or "",
        )

        pre = self.precondition_validator.validate(
            step=step,
            failed_step_indices=self.failed_step_indices,
            all_steps=self.steps,
        )
        result.precondition = pre

        if not pre.passed:
            if "blocked_by_previous_failure" in pre.failures:
                result.status = "blocked"
                result.skip_reason = pre.message
                result.error_message = pre.message
                result.duration_ms = int((time.time() - started) * 1000)
                return result
            result.evidence_before = self._capture_evidence(step_num, "before")
            url_before = self.page.url
            result = self._heal_failed_step(
                step=step, step_num=step_num,
                original_error=pre.message,
                failure_phase="precondition",
                result=result,
                url_before=url_before,
            )
            result.evidence_after = self._capture_evidence(step_num, "after")
            result.duration_ms = int((time.time() - started) * 1000)
            return result

        if pre.checks.get("skipped"):
            result.status = "skipped"
            result.skip_reason = pre.message
            result.duration_ms = int((time.time() - started) * 1000)
            return result

        result.evidence_before = self._capture_evidence(step_num, "before")
        url_before = self.page.url

        try:
            sel_used = self.step_executor.execute(
                step, base_url=self.base_url, data_values=self._data_values,
                field_value_map=self._field_value_map,
            )
            result.selected_locator = sel_used or result.original_locator
        except Exception as exc:
            result = self._heal_failed_step(
                step=step, step_num=step_num,
                original_error=str(exc),
                failure_phase="execution",
                result=result,
                url_before=url_before,
            )
            result.evidence_after = self._capture_evidence(step_num, "after")
            result.duration_ms = int((time.time() - started) * 1000)
            return result

        post = self.postcondition_validator.validate(
            step=step,
            page=self.page,
            next_step=self._next_executable_step(step_num),
            url_before=url_before,
        )
        result.postcondition = post

        if post.passed:
            result.status = "passed"
        else:
            result = self._heal_failed_step(
                step=step, step_num=step_num,
                original_error=post.message or "postcondition_failed",
                failure_phase="postcondition",
                result=result,
                url_before=url_before,
            )

        result.evidence_after = self._capture_evidence(step_num, "after")
        result.duration_ms = int((time.time() - started) * 1000)
        return result

    def _run_id(self):
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        return f"{self.recording_id or 'run'}_{ts}"

    def run(self):
        from playwright.sync_api import sync_playwright
        from testforge.browser import launch_browser
        from testforge.healing.llm_client import is_available

        self._load_script_metadata()
        self._load_data_file()

        healer = "LLM real (Azure/OpenAI)" if is_available() else "MockLLMHealer"
        mode = "shadow" if self.shadow_mode else ("no-healing" if self.no_healing else "incremental")
        self.ui.header(
            script_path=self.script_path,
            recording_id=self.recording_id or "(desconhecido)",
            base_url=self.base_url,
            healer=healer,
            mode=mode,
        )

        with sync_playwright() as pw:
            browser = launch_browser(pw, self.browser_type, headless=self.headless, verify_ssl=self.verify_ssl)
            _vp = {"width": 1280, "height": 720} if self.headless else None
            _ctx_kwargs: dict = {"viewport": _vp} if _vp else {}
            if not self.verify_ssl:
                _ctx_kwargs["ignore_https_errors"] = True
            ctx = browser.new_context(**_ctx_kwargs)
            self.page = ctx.new_page()

            try:
                self._load_semantic_steps()
            except Exception as exc:
                print(f"[TestForge] Falha ao carregar steps semanticos: {exc}")

            if not self.steps:
                print("[TestForge] Nenhum step encontrado — encerrando.")
                browser.close()
                return self._finalize_report({})

            if self.base_url:
                try:
                    self.page.goto(self.base_url)
                    self.page.wait_for_timeout(400)
                except Exception:
                    pass

            self._init_components()

            for i, step in enumerate(self.steps):
                result = self._run_one_step(i, step)
                self.step_results.append(result)
                self.ui.step(i + 1, len(self.steps), result)
                if self.replay_recorder:
                    self.replay_recorder.capture_step(
                        i, step,
                        status=result.status,
                        error_message=result.error_message or "",
                    )

                if result.status in ("failed", "healing_rejected"):
                    if getattr(step, "blocking", False):
                        self.failed_step_indices.add(i)
                    if self.stop_on_failure:
                        break

            if self.replay_recorder:
                cap_info = self.replay_recorder.finish()
                print(f"  📹 Captura salva: {cap_info['session_dir']} ({cap_info['steps_captured']} steps)")

            browser.close()

        totals = self._compute_totals()
        return self._finalize_report(totals)

    def _compute_totals(self):
        t = {"total": len(self.step_results)}
        for k in ("passed", "healed_validated", "healing_rejected",
                  "failed", "blocked", "skipped", "shadow_healed"):
            t[k] = sum(1 for r in self.step_results if r.status == k)
        return t

    def _finalize_report(self, totals):
        report = {
            "run_id": self._run_id(),
            "recording_id": self.recording_id,
            "script_path": self.script_path,
            "base_url": self.base_url,
            "mode": "shadow" if self.shadow_mode else ("no-healing" if self.no_healing else "incremental"),
            "summary": totals,
            "steps": [r.to_dict() for r in self.step_results],
        }
        try:
            out_dir = Path(self.output_root) / (self.recording_id or "run") / self._run_id().split("_")[-1]
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "execution_report.json").write_text(
                json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
            )
            self._write_healing_report(out_dir)
            # Record aggregate run metrics before writing
            if self.metrics:
                any_healing = any(r.healing for r in self.step_results if r.healing and r.healing.attempted)
                self.metrics.record_run(healed=any_healing)
            self._write_metrics(out_dir)
        except Exception as exc:
            print(f"[TestForge] Falha ao escrever relatorio: {exc}")
        self.ui.summary(totals)
        return report

    def _write_healing_report(self, out_dir):
        lines = ["# TestForge Healing Report", ""]
        validated = [r for r in self.step_results if r.status == "healed_validated"]
        rejected = [r for r in self.step_results if r.status == "healing_rejected"]
        lines.append(f"- Validados: {len(validated)}")
        lines.append(f"- Rejeitados: {len(rejected)}")
        lines.append("")
        if validated:
            lines.append("## Healings validados")
            for r in validated:
                h = r.healing or HealingAttempt()
                lines.append(f"### Step {r.step_num} — {r.action}")
                lines.append(f"- Locator original: `{h.original_locator}`")
                lines.append(f"- Locator proposto: `{h.proposed_locator}`")
                lines.append(f"- Layer: {h.layer} | Family: {h.family} | Strategy: {h.strategy}")
                lines.append(f"- Confidence: {h.confidence:.2f}")
                lines.append("")
        if rejected:
            lines.append("## Healings rejeitados")
            for r in rejected:
                h = r.healing or HealingAttempt()
                lines.append(f"### Step {r.step_num} — {r.action}")
                lines.append(f"- Motivo: {','.join(h.rejection_reason) or 'n/a'}")
                lines.append(f"- Locator proposto: `{h.proposed_locator}`")
                lines.append("")
        (out_dir / "healing_report.md").write_text("\n".join(lines), encoding="utf-8")

    def _write_metrics(self, out_dir):
        if not self.metrics:
            return
        try:
            snap = self.metrics.snapshot.to_dict()
            (out_dir / "metrics.json").write_text(
                json.dumps(snap, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception:
            pass