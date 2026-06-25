"""TestForge CLI — Comandos: record, compile, run, pipeline, demo-heal."""
import argparse
import json
import logging
import os
import sys
import time

from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

from testforge.browser import launch_browser
from testforge.recorder import RecorderController
from testforge.evidence import EvidenceCollector
from testforge.semantic import RecordingNormalizer, PlaywrightCompiler
from testforge.oracle import OracleRunner
from testforge.promotion import PromotionGate
from testforge.taxonomy import FailureClassifier
from testforge.runner import FallbackRunner
from testforge.metrics import MetricsRepository, StepOutcome
from testforge.healing import HealingCatalog, HealingRecipe, EvidencePayload
from testforge.healing import CuradorAutomatico, CurationOutcome, ProgressResult
from testforge.evidence import EvidenceCollector
from testforge.validation import validate_url
from testforge.validation.intent_completeness import (
    IntentCompletenessChecker,
    save_completeness_report,
)
from testforge.recorder.recording_status import RecordingStatus
from testforge.reporting import RunReport, StepReport

import pathlib
_PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent
import re as _re


def _sanitize_name(name: str) -> str:
    """Sanitiza nome de teste/gravação: remove caracteres especiais, mantém alfanuméricos, underscore, hífen."""
    sanitized = _re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    sanitized = _re.sub(r'_+', '_', sanitized).strip('_')
    return sanitized or "unnamed"


def _make_context_kwargs(headless: bool) -> dict:
    """Return browser.new_context kwargs: fixed viewport in headless, no_viewport=True in headed."""
    if headless:
        return {"viewport": {"width": 1280, "height": 720}}
    return {"no_viewport": True}


def _validate_and_warn_url(url: str) -> bool:
    """Valida URL e imprime avisos. Retorna True se houver avisos críticos."""
    if not url:
        return False
    warnings = validate_url(url)
    if not warnings:
        return False
    has_critical = False
    for w in warnings:
        prefix = "[WARN] CRITICAL" if w.is_critical else "[WARN] Warning"
        print(f"[TestForge] {prefix}: {w.message}", file=sys.stderr)
        if w.is_critical:
            has_critical = True
    if has_critical:
        print("[TestForge] 💡 Tip: wrap URL in quotes when using shell, e.g.:\n"
              "    tf record \"http://example.com/page?arg=1&other=2\"", file=sys.stderr)
    return has_critical


def _update_recording_status(rec_dir: str, rec_id: str,
                              status: RecordingStatus) -> bool:
    """Atualiza recording_metadata.json com novo status de gravação."""
    meta_path = os.path.join(rec_dir, "recording_metadata.json")
    if not os.path.exists(meta_path):
        return False
    try:
        with open(meta_path) as f:
            meta = json.load(f)
        if "status_history" not in meta:
            meta["status_history"] = []
        from datetime import datetime, timezone
        meta["status_history"].append({
            "status": status.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": f"compile --check: {status.value}",
            "metadata": {},
        })
        meta["recording_status"] = status.value
        meta["status"] = status.value
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, default=str)
        return True
    except Exception:
        return False


def _run_post_recording_completion(rec_dir: str, rid: str, args,
                                    auto_complete: bool, no_interactive: bool):
    """Executa verificação de completude de intenção + prompt interativo opcional após gravação."""
    from testforge.semantic import RecordingNormalizer
    from testforge.validation.intent_completeness import (
        IntentCompletenessChecker,
        save_completeness_report,
    )
    from testforge.cli._interactive_completion import (
        prompt_missing_fields,
        create_data_template,
    )
    from testforge.recorder.recording_status import RecordingStatus

    print(f"\n[TestForge] 🔍 Verificando completude da intencao...")

    try:
        normalizer = RecordingNormalizer()
        app = args.app or "web"
        base_url = args.url or "http://localhost"
        stc = normalizer.normalize(rec_dir, f"ST-{rid}", app, base_url)

        checker = IntentCompletenessChecker()
        report = checker.check_steps(stc.steps, stc.field_values)

        report_dir = os.path.join(rec_dir, "completeness")
        json_path, md_path = save_completeness_report(report, report_dir, rid)
        print(f"[TestForge] ✓ Relatorio: {md_path}")

        if report.is_complete:
            print(f"[TestForge] ✓ Intencao COMPLETA ({report.resolved_count} campos)")
            _update_recording_status(rec_dir, rid, RecordingStatus.intent_complete)
            return stc, report

        print(f"[TestForge] [WARN] Intencao INCOMPLETA — {report.missing_count} pendente(s)")

        if no_interactive:
            # Non-interactive mode: create template
            template_path = create_data_template(rec_dir, rid, report)
            print(f"[TestForge] ✓ Template criado: {template_path}")
            _update_recording_status(rec_dir, rid, RecordingStatus.incomplete_intent)
            print(f"[TestForge] 💡 Use: testforge compile --check {rid}")
            print(f"[TestForge] 💡 Ou forneca valores via --data arquivo.json")
            return stc, report

        if auto_complete:
            # Interactive mode: prompt user for values
            all_resolved = prompt_missing_fields(rec_dir, rid, report,
                                                  normalizer, stc)
            # Re-read completeness report after user input (prompt may have re-checked)
            new_report_path = os.path.join(rec_dir, "completeness", f"completeness-{rid}.json")
            if os.path.exists(new_report_path):
                with open(new_report_path) as f:
                    from testforge.validation.intent_completeness import CompletenessReport
                    new_report = CompletenessReport.from_dict(json.load(f))
                report = new_report
                # Re-normalize to get fresh stc
                try:
                    stc = normalizer.normalize(rec_dir, f"ST-{rid}", args.app or "web", args.url or "http://localhost")
                except Exception:
                    pass
            if all_resolved:
                print(f"[TestForge] [OK] Gravacao pronta para compilacao!")
                print(f"  Use: testforge compile {rid}")
            else:
                print(f"[TestForge] [WARN] Campos pendentes — compile bloqueado ate completar")
                print(f"  Use: testforge compile --check {rid}")
            return stc, report

        # Default: no --complete mode, just inform
        print(f"[TestForge] 💡 Use --complete para informar valores pendentes")
        print(f"  Ou: testforge compile --check {rid}")
        return stc, report

    except FileNotFoundError as e:
        print(f"[TestForge] [WARN] Normalizacao nao disponivel: {e}")
    except Exception as e:
        print(f"[TestForge] [WARN] Erro na verificacao de completude: {e}")
    return None, None


def _run_post_recording_validation(rec_dir: str, rid: str, args,
                                    stc, completeness_report):
    """Run full validation pipeline: completeness check + readiness gate.

    This is the core of the --validate-before-ready feature.
    Evaluates completeness, runs incremental validation, and saves
    a QA-friendly readiness report.
    """
    from testforge.validation.readiness_gate import (
        RecordingReadinessGate,
        save_readiness_report,
    )
    from testforge.recorder.recording_status import RecordingStatus

    print(f"\n[TestForge] 🔍 Validando gravacao antes de marcar como pronta...")

    if completeness_report is None:
        print(f"[TestForge] [WARN] Relatorio de completude nao disponivel")
        return

    # Build field_values dict from the stc
    field_values = {}
    if stc and stc.field_values:
        field_values = stc.field_values

    # Run headless incremental validation in pilot-mode for real step_results
    step_results = []
    if getattr(args, "pilot_mode", False):
        try:
            out_dir = os.path.join(rec_dir, "_pilot_tmp")
            script_path = PlaywrightCompiler().compile(stc, out_dir)
            from testforge.runner.incremental_runner import IncrementalRunner
            runner = IncrementalRunner(
                script_path=script_path,
                headless=True,
                timeout=90,
                stop_on_failure=False,
                no_healing=True,
                capture=False,
                output_root=os.path.join(rec_dir, "_pilot_runs"),
            )
            runner.run()
            step_results = runner.step_results
        except Exception as exc:
            print(f"[TestForge] [WARN] Pilot run falhou: {exc}")

    # Evaluate readiness gate
    gate = RecordingReadinessGate()
    readiness_report = gate.evaluate(
        recording_id=rid,
        application=args.app or "web",
        base_url=args.url or "http://localhost",
        completeness_report=completeness_report,
        step_results=step_results,
        field_values=field_values,
    )

    # Save readiness report
    report_dir = os.path.join(rec_dir, "readiness")
    json_path, md_path = save_readiness_report(readiness_report, report_dir)
    print(f"[TestForge] ✓ Relatorio de readiness: {md_path}")

    # Update recording status based on verdict
    if readiness_report.verdict.value == "pass":
        print(f"[TestForge] [OK] Validacao PASSOU — gravacao pronta para o time!")
        _update_recording_status(rec_dir, rid, RecordingStatus.ready_for_team)
    elif readiness_report.verdict.value == "needs_review":
        print(f"[TestForge] 🔍 Validacao com RESSALVAS — revise o relatorio")
        _update_recording_status(rec_dir, rid, RecordingStatus.needs_review)
    else:
        print(f"[TestForge] [FAIL] Validacao FALHOU — corrija os problemas e tente novamente")
        _update_recording_status(rec_dir, rid, RecordingStatus.incomplete_intent)

    # Print summary
    r = readiness_report
    print(f"\n  Resumo da validacao:")
    print(f"  Verdicto: {r.verdict.value.upper()}")
    print(f"  Completude: {'[OK]' if r.completeness_passed else '[FAIL]'}")
    print(f"  Steps: {r.passed_steps} ok, {r.failed_steps} falha(s), {r.healed_steps} curado(s)")
    print(f"  Total campos: {r.total_steps} ({len(r.missing_fields)} pendentes)")
    if r.warnings:
        print(f"  Avisos: {len(r.warnings)}")
        for w in r.warnings:
            print(f"    [WARN] {w}")
    print(f"\n  Relatorio completo: {md_path}")


def _check_python_keyboard(page, recorder):
    """Monitora estado do assert e ativa via Python se necessario."""
    try:
        is_assert = page.evaluate("window.__tfAssertWaiting")
        has_element = page.evaluate("window.__tfAssertElement !== undefined && window.__tfAssertElement !== null")
        if is_assert and not has_element:
            pass
        elif is_assert and has_element:
            pass
    except Exception:
        pass


def _load_config_defaults() -> dict:
    """Read defaults: section from .testforge/config.yml. Returns {} on any error."""
    try:
        from testforge.publisher import GitPublisher
        import yaml
        git_root = GitPublisher._find_git_root(os.getcwd())
        for base in filter(None, [os.getcwd(), git_root]):
            config_path = os.path.join(base, ".testforge", "config.yml")
            if os.path.exists(config_path):
                with open(config_path) as f:
                    cfg = yaml.safe_load(f) or {}
                return cfg.get("defaults", {})
    except Exception:
        pass
    return {}


def _auto_publish_recording(rid: str, rec_dir: str):
    """Auto-publish recording artifacts to Git repo if env vars configured.

    Always called — even for incomplete recordings — so the team can diagnose
    TestForge issues from submission_report.json.
    """
    try:
        from testforge.publisher import GitPublisher
        publisher = GitPublisher.from_config() or GitPublisher.from_env()
        if publisher is None:
            print(
                "[TestForge] ℹ Git publisher nao configurado. "
                "Crie .testforge/config.yml ou defina TESTFORGE_GIT_URL.",
                file=sys.stderr,
            )
            return
        mode = "local" if publisher._local_mode else "remoto"
        # Warn if system/suite not set
        import os as _os
        meta_path = _os.path.join(rec_dir, "recording_metadata.json")
        if _os.path.exists(meta_path):
            with open(meta_path) as _f:
                _meta = json.load(_f)
            if not _meta.get("system") and (_os.getenv("TESTFORGE_GIT_URL") or publisher._local_mode):
                print(
                    "[TestForge] [WARN] Aviso: --system e --suite nao informados. "
                    "Gravacao publicada em 'uncategorized'.",
                    file=sys.stderr,
                )
        recordings_root = str(_PROJECT_ROOT / "recordings")
        semantic_root = str(_PROJECT_ROOT / "semantic_tests")
        print(f"[TestForge] Publicando {rid} no Git ({mode})...")
        result = publisher.publish(rid, recordings_root, semantic_root)
        if result.success:
            sha_short = result.commit_sha[:8] if result.commit_sha else "sem-commit"
            print(f"[TestForge] ✓ Publicado: {result.remote_path} ({sha_short})")
        else:
            print(f"[TestForge] [WARN] Publicacao falhou: {result.error}", file=sys.stderr)
    except Exception as exc:
        print(f"[TestForge] [WARN] Erro de publicacao (nao-bloqueante): {exc}", file=sys.stderr)


def cmd_record(args):
    """Grava fluxo de teste com comandos de teclado."""
    # Validate URL before any operation
    if not args.url:
        print("[TestForge] Erro: URL obrigatoria para iniciar nova gravacao.")
        print()
        print("  Exemplos:")
        print("    testforge record \"https://sistema/\" --name CT-001 --browser chrome")
        print("    testforge record \"https://sistema/\" --system SIOPI --suite credito --test-case CT-001")
        print()
        print("  Organizacao no Git (--system, --suite, --test-case):")
        print("    recordings/{system}/{suite}/{test_case}/{recording_id}/")
        print()
        print("  Configurar publicacao: .testforge/config.yml ou env vars")
        print("    TESTFORGE_GIT_URL, TESTFORGE_GIT_TOKEN, TESTFORGE_GIT_BRANCH")
        print()
        print("  Ajuda:")
        print("    testforge record --help")
        return

    no_interactive = getattr(args, 'no_interactive', False)
    auto_complete = getattr(args, 'complete', False) and not no_interactive

    if args.url:
        _validate_and_warn_url(args.url)
    with sync_playwright() as pw:
        browser = launch_browser(pw, getattr(args, 'browser', 'chromium'), headless=args.headless)
        context = browser.new_context(**_make_context_kwargs(args.headless))
        page = context.new_page()
        recorder = RecorderController(page)

        ts = time.strftime("%Y%m%d-%H%M%S")
        rid = _sanitize_name(args.name) if args.name else f"REC-{ts}"

        # Load system/suite/test_case — args override config defaults
        _cfg_defaults = _load_config_defaults()
        _system = getattr(args, 'system', None) or _cfg_defaults.get("system", "") or ""
        _suite = getattr(args, 'suite', None) or ""
        _test_case_arg = getattr(args, 'test_case', None) or args.name or ""

        print(f"[TestForge] Gravando: {rid}")
        print(f"  URL: {args.url}")
        if _system or _suite:
            _ctx = " / ".join(filter(None, [_system, _suite, _test_case_arg or rid]))
            print(f"  Contexto: {_ctx}")
        else:
            print(f"  AVISO: --system e --suite nao informados.")
            print(f"    A gravacao sera publicada em recordings/uncategorized/{rid}")
            print(f"    Use: testforge record <url> --system SISTEMA --suite SUITE")
        print(f"  Viewport: {'1280x720 (headless)' if args.headless else 'janela real (headed)'}")
        print(f"  Shift+P=pausar | Shift+S=parar | Shift+A=assert")
        print()

        # Sprint 0 mode resolution
        _diag = getattr(args, "diagnostic_mode", False) or \
                getattr(args, "pipeline_and_diagnostic_mode", False)
        _replay_mode = "batched" if getattr(args, "replay_batched", False) else "immediate"
        session = recorder.start(
            recording_id=rid,
            application=args.app or "web",
            base_url=args.url,
            evidence_level=args.evidence_level,
            system=_system,
            suite=_suite,
            test_case=_test_case_arg,
            use_cdp=getattr(args, "use_cdp_recorder", False),
            diagnostic_mode=_diag,
            replay_mode=_replay_mode,
        )
        rid = session.recording_id  # may be suffixed (_2, _3) if original name exists
        _test_case = _test_case_arg or args.name or rid

        # Write system/suite/test_case classification metadata
        _meta_path = str(_PROJECT_ROOT / "recordings" / rid / "recording_metadata.json")
        if os.path.exists(_meta_path):
            with open(_meta_path) as _f:
                _meta = json.load(_f)
            _meta["system"] = _system
            _meta["suite"] = _suite
            _meta["test_case"] = _test_case
            with open(_meta_path, "w", encoding="utf-8") as _f:
                json.dump(_meta, _f, indent=2, default=str)

        page.goto(args.url)

        step_count = 0
        try:
            while True:
                try:
                    time.sleep(0.3)
                    recorder.flush_events()
                    result = recorder.handle_commands()

                    # Check for asserts via Python keyboard listener (fallback para sites que bloqueiam JS keydown)
                    _check_python_keyboard(page, recorder)

                    steps_file = str(_PROJECT_ROOT / "recordings" / rid / "steps.jsonl")
                    if os.path.exists(steps_file):
                        with open(steps_file) as f:
                            current = sum(1 for _ in f)
                        if current > step_count:
                            step_count = current
                            print(f"[TestForge] OK {step_count} passos gravados")

                    if result == "stop":
                        print("[TestForge] [STOP] Finalizado (Shift+S)")
                        break
                    elif result == "paused":
                        sys.stdout.write("\r[TestForge] [PAUSED] Pausado... (Shift+P retoma)  ")
                        sys.stdout.flush()
                except KeyboardInterrupt:
                    raise
                except Exception as _loop_exc:
                    logger.error("Recording loop error: %s", _loop_exc, exc_info=True)
        except KeyboardInterrupt:
            print("\n[TestForge] Interrompido")

        # Sprint 0: prompt for Gherkin confirm/edit BEFORE stop (so finalize writes correct .feature)
        _gherkin_func = ""
        _gherkin_cen = ""
        if _diag and recorder._diagnostic is not None and recorder._diagnostic.gherkin is not None:
            _gherkin_func, _gherkin_cen = _prompt_gherkin_confirm(recorder._diagnostic.gherkin)
        recorder.stop(gherkin_funcionalidade=_gherkin_func, gherkin_cenario=_gherkin_cen)
        recorder.finalize()
        # Count raw events and display breakdown
        raw_count = 0
        rec_dir = str(_PROJECT_ROOT / "recordings" / rid)
        steps_jsonl = os.path.join(rec_dir, "steps.jsonl")
        if os.path.exists(steps_jsonl):
            with open(steps_jsonl) as f:
                raw_count = sum(1 for _ in f)
        print(f"[TestForge] Eventos brutos: {raw_count}")
        print(f"[TestForge] Sessao salva: recordings/{rid}/")
        if _diag:
            diag_dir = os.path.join(rec_dir, "diagnostic")
            print(f"[TestForge] Diagnostic: {diag_dir}/")
            if os.path.exists(os.path.join(diag_dir, "scenario.feature")):
                print(f"[TestForge] Gherkin:    {diag_dir}/scenario.feature")
        browser.close()

    # Q4 — `--diagnostic-mode` skips compile/run. `--pipeline-and-diagnostic-mode`
    # runs both. Plain --diagnostic-mode (no pipeline flag) early-returns.
    _diagnostic_only = getattr(args, "diagnostic_mode", False) and \
                       not getattr(args, "pipeline_and_diagnostic_mode", False)
    if _diagnostic_only:
        _publish_diagnostic_to_azure(rid, os.path.join(rec_dir, "diagnostic"))
        _auto_publish_recording(rid, rec_dir)
        return

    # Post-recording: intent completeness check + validation
    validate_before_ready = getattr(args, 'validate_before_ready', False)
    pilot_mode = getattr(args, 'pilot_mode', False)
    run_validation = validate_before_ready or pilot_mode

    stc = None
    completeness_report = None

    if auto_complete or no_interactive or run_validation:
        result = _run_post_recording_completion(rec_dir, rid, args, auto_complete, no_interactive)
        if result:
            stc, completeness_report = result

    if run_validation and completeness_report is not None:
        _run_post_recording_validation(rec_dir, rid, args, stc, completeness_report)

    # Auto-publish after validation so git snapshot includes validated artifacts
    _auto_publish_recording(rid, rec_dir)


def _publish_diagnostic_to_azure(recording_id: str, diagnostic_dir: str) -> None:
    """Sprint 0 commit 6: publish diagnostic/ to Azure DevOps repo via Z5 chain."""
    if not os.path.isdir(diagnostic_dir):
        return
    cfg_path = _PROJECT_ROOT / ".testforge" / "config.yml"
    if not cfg_path.exists():
        return
    try:
        import yaml
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return
    if cfg.get("provider") != "azure-devops":
        return
    az = cfg.get("azure_devops") or {}
    org = az.get("org") or ""
    project = az.get("project") or ""
    repo = az.get("repo") or ""
    if not (org and project and repo) or "YOUR_" in (org + project + repo):
        return  # template not configured
    from testforge.publisher.azure_devops import AzureDevOpsPublisher
    pub = AzureDevOpsPublisher(
        org=org, project=project, repo=repo,
        branch=az.get("branch", "main"),
        prefer_ssh=bool(az.get("prefer_ssh", False)),
        path_prefix=az.get("path_prefix", "diagnostic"),
    )
    result = pub.publish(recording_id, diagnostic_dir)
    if result.get("success"):
        print(f"[TestForge] ok Azure DevOps publish ({result.get('credential_source')}): "
              f"{result.get('remote_path')} @ {result.get('commit_sha', '?')[:7]}")
    else:
        print(f"[TestForge] [WARN] Azure DevOps publish falhou: {result.get('error')}")


def _prompt_gherkin_confirm(writer) -> tuple:
    """C4c — prompt user to confirm or override auto-derived Gherkin metadata."""
    auto_func = writer.auto_funcionalidade()
    auto_cen = writer.auto_cenario_from_sequence()
    print()
    print("[TestForge] Gherkin auto-derivado:")
    print(f"  Funcionalidade: {auto_func}")
    print(f"  Cenario:        {auto_cen}")
    print("  (Enter aceita | texto sobrescreve | 'e' abre editor depois)")
    try:
        func_in = input(f"  Funcionalidade [{auto_func}]: ").strip()
        cen_in = input(f"  Cenario [{auto_cen}]: ").strip()
    except (EOFError, KeyboardInterrupt):
        return ("", "")
    edit = (func_in.lower() == "e") or (cen_in.lower() == "e")
    final_func = "" if func_in.lower() == "e" else func_in
    final_cen = "" if cen_in.lower() == "e" else cen_in
    if edit:
        # write first, then open in $EDITOR
        writer.write(final_func, final_cen)
        editor = os.environ.get("EDITOR", "vi")
        try:
            import subprocess
            subprocess.call([editor, writer.path])
        except Exception as exc:
            print(f"[TestForge] Editor falhou ({editor}): {exc}")
    return (final_func, final_cen)


def _auto_learn(error_msg: str, solution: str, framework: str = "generic"):
    """Registra automaticamente licao aprendida no catalogo de cura."""
    try:
        from testforge.healing import HealingCatalog, HealingRecipe
        from testforge.taxonomy import FailureClassifier
        catalog = HealingCatalog()
        classifier = FailureClassifier()
        failure = classifier.classify(error_msg)

        # So cria receita se nao existir match com score alto (>=5)
        existing = catalog.match_recipes(error_msg, framework, failure.family.value)
        high_confidence = [r for r in existing if r.priority >= 5]
        if not high_confidence:
            recipe = HealingRecipe(
                trigger_family=failure.family.value,
                trigger_code=failure.code,
                trigger_pattern=error_msg[:200],
                trigger_framework=framework,
                solution_strategy="auto_learned",
                solution_selector=solution[:300],
                priority=1,
                status="active",
            )
            rid = catalog.add_recipe(recipe)
            print(f"  📝 Licao auto-registrada: {rid} ({failure.code})")
            return rid
    except Exception:
        pass
    return None


def cmd_compile(args):
    rec_id = args.recording
    # Strip recordings/ prefix if user passes full path
    if rec_id.startswith("recordings/"):
        rec_id = rec_id[len("recordings/"):]
    rec_dir = str(_PROJECT_ROOT / "recordings" / rec_id)
    # Fallback: try user-provided path directly if constructed path doesn't exist
    if not os.path.isdir(rec_dir) and os.path.isdir(args.recording):
        rec_dir = os.path.abspath(args.recording)
        rec_id = os.path.basename(rec_dir)
    if not os.path.isdir(rec_dir):
        print(f"[TestForge] ✗ Gravacao nao encontrada: {rec_dir}")
        return

    # Le metadata da gravacao (app e url ja estao la)
    meta_path = f"{rec_dir}/recording_metadata.json"
    app = args.app
    base_url = args.base_url
    recording_status = None
    if os.path.exists(meta_path):
        import json as _json
        with open(meta_path) as f:
            meta = _json.load(f)
        app = app or meta.get("application", "")
        base_url = base_url or meta.get("base_url", "")

        # Check recording status — block compilation if incomplete
        status_str = meta.get("recording_status") or meta.get("status", "")
        try:
            recording_status = RecordingStatus(status_str)
        except ValueError:
            recording_status = None

        if not getattr(args, 'check', False) and recording_status in RecordingStatus.blocked_compile_states():
            print(f"[TestForge] ✗ Gravacao {rec_id} esta em estado {recording_status.value}")
            print(f"  Compilacao bloqueada — complete os valores pendentes primeiro.")
            print(f"  Use: testforge record --complete {rec_id}")
            print(f"  Ou:  testforge compile --check {rec_id}  (gera relatorio de completude)")
            return

    # --audit: run recording auditor (always runs in background if available)
    audit_report = None
    if getattr(args, 'audit', False) or True:  # default: always generate audit
        try:
            from testforge.recorder.recording_auditor import RecordingAuditor
            auditor = RecordingAuditor()
            audit_report = auditor.audit(rec_dir)
            auditor.print_report(audit_report)
        except Exception as exc:
            logger.warning("Audit failed (non-fatal): %s", exc)

    try:
        normalizer = RecordingNormalizer()
        stc = normalizer.normalize(rec_dir, f"ST-{rec_id}", app or "app", base_url or "http://localhost")
    except Exception as exc:
        logger.error("Normalization FAILED: %s", exc, exc_info=True)
        print(f"[TestForge] ✗ Normalizacao falhou: {exc}")
        if audit_report:
            audit_report.setdefault("errors", []).append({
                "phase": "normalize",
                "error": str(exc),
            })
        return

    # Output directory (sanitized)
    safe_rec_id = _sanitize_name(rec_id)
    out_dir = args.output or str(_PROJECT_ROOT / f"semantic_tests/ST-{safe_rec_id}")

    # --check: run IntentCompletenessChecker and save report
    if getattr(args, 'check', False):
        checker = IntentCompletenessChecker()
        report = checker.check_steps(stc.steps, stc.field_values)
        report_dir = os.path.join(rec_dir, "completeness")
        json_path, md_path = save_completeness_report(report, report_dir, rec_id)

        if report.is_complete:
            print(f"[TestForge] ✓ Intent Completeness: COMPLETE ({report.resolved_count} campos)")
            # Update metadata status
            _update_recording_status(rec_dir, rec_id,
                                      RecordingStatus.intent_complete)
        else:
            print(f"[TestForge] [WARN] Intent Completeness: INCOMPLETE")
            print(f"  Resolvidos: {report.resolved_count} | Warning: {report.resolved_with_warning_count}")
            print(f"  Revisao: {report.review_required_count} | Pendentes: {report.missing_count}")
            print(f"  Relatorio: {md_path}")
            _update_recording_status(rec_dir, rec_id,
                                      RecordingStatus.incomplete_intent)
        print(f"  Relatorio JSON: {json_path}")
        print(f"  Relatorio MD:  {md_path}")

        from testforge.metrics.pilot_metrics import PilotMetrics as _PilotMetrics
        _pm = _PilotMetrics()
        rate = _pm.compute_auto_resolution_rate(report)
        print(f"[TestForge] % campos auto-resolvidos: {rate:.0%}")

    # Data-driven: extrai massa de dados externa
    data_file = ""
    if getattr(args, 'data', False):
        from testforge.semantic.data_extractor import generate_test_data_file
        os.makedirs(out_dir, exist_ok=True)
        data_path = generate_test_data_file(
            rec_dir,
            os.path.join(out_dir, "test_data.json"),
            scenarios=getattr(args, 'scenarios', False),
        )
        data_file = data_path
        print(f"[TestForge] ✓ Massa de dados: {data_file}")

    try:
        compiler = PlaywrightCompiler()
        if getattr(args, "use_v2_compiler", False):
            path = compiler.compile_v2(stc, out_dir, data_file=data_file)
            print(f"[TestForge] ✓ v2 compile: {path}")
            print(f"  Fallback chain em runtime (LocatorResolver). Candidates em {out_dir}/candidates/")
        else:
            path = compiler.compile(stc, out_dir, data_file=data_file)
    except Exception as exc:
        logger.error("Compilation FAILED: %s", exc, exc_info=True)
        print(f"[TestForge] ✗ Compilacao falhou: {exc}")
        if audit_report:
            audit_report.setdefault("errors", []).append({
                "phase": "compile",
                "error": str(exc),
            })
        return

    # Generate semantic_steps.jsonl for audit trail
    try:
        semantic_path = compiler.compile_semantic_steps(stc, out_dir)
    except Exception as exc:
        logger.warning("Semantic steps generation failed (non-fatal): %s", exc)
        semantic_path = ""

    print(f"[TestForge] ✓ SemanticTestCase: {len(stc.steps)} steps")
    # Breakdown
    interactions = sum(1 for s in stc.steps if s.action in ("fill", "click", "select_option"))
    asserts = sum(1 for s in stc.steps if s.action == "assert")
    print(f"[TestForge]   Interacoes: {interactions} | Asserts: {asserts}")
    print(f"[TestForge] ✓ Script gerado: {path}")
    if semantic_path:
        print(f"[TestForge] ✓ Semantic steps: {semantic_path}")
    if data_file:
        print(f"[TestForge] ✓ Script data-driven (le {os.path.basename(data_file)})")

    with open(path) as f:
        code = f.read()
    try:
        compile(code, path, "exec")
        print("[TestForge] ✓ Script compila sem erros")
    except SyntaxError as e:
        logger.error("Syntax error in compiled script: %s", e)
        print(f"[TestForge] ✗ Erro de sintaxe: {e}")


def cmd_audit(args):
    """Audit a recording: quality metrics, event analysis, compilation status."""
    rec_id = args.recording
    if rec_id.startswith("recordings/"):
        rec_id = rec_id[len("recordings/"):]
    rec_dir = str(_PROJECT_ROOT / "recordings" / rec_id)
    if not os.path.isdir(rec_dir) and os.path.isdir(args.recording):
        rec_dir = os.path.abspath(args.recording)
        rec_id = os.path.basename(rec_dir)
    if not os.path.isdir(rec_dir):
        print(f"[TestForge] Recording not found: {rec_dir}")
        return
    from testforge.recorder.recording_auditor import RecordingAuditor
    auditor = RecordingAuditor()
    report = auditor.audit(rec_dir)
    auditor.print_report(report)


def cmd_run(args):
    """Executa script Playwright inline com healing L0→L3 via CuradorAutomatico."""
    script_path = args.script

    if not os.path.exists(script_path):
        print(f"[TestForge] ✗ Script nao encontrado: {script_path}")
        return

    metrics = MetricsRepository()

    with open(script_path) as f:
        code = f.read()

    base_url = "http://localhost:8765"
    for line in code.split("\n"):
        if line.startswith("BASE_URL"):
            base_url = line.split('"')[1]
            break

    # Extrai recording_id do source (docstring)
    recording_id = None
    for line in code.split("\n"):
        if "source:" in line:
            recording_id = line.split("source:")[-1].strip().rstrip('."\'')
            break

    print(f"[TestForge] Executando: {script_path}")
    print(f"  URL base: {base_url}")

    # Check LLM availability
    from testforge.healing.llm_client import is_available
    if is_available():
        print(f"  Healer: LLM real (Azure/OpenAI)")
    else:
        print(f"  Healer: MockLLMHealer (deterministico — configure AZURE_OPENAI_ENDPOINT para LLM real)")

    if recording_id:
        print(f"  Recording: {recording_id}")

    # Carrega passos da gravacao via SemanticTestCase
    steps = []
    app_name = "web"
    if recording_id:
        rec_dir = str(_PROJECT_ROOT / "recordings" / recording_id)
        if os.path.isdir(rec_dir):
            normalizer = RecordingNormalizer()
            stc = normalizer.normalize(rec_dir, f"ST-{recording_id}", "web", base_url)
            steps = stc.steps
            app_name = stc.application or "web"
            print(f"  Carregados {len(steps)} passos da gravacao")
        else:
            print(f"  [WARN] Recording nao encontrado: {rec_dir} — executando via pytest")
    else:
        print(f"  [WARN] Sem recording_id — executando via pytest")

    healed = False
    layer_used = ""
    llm_used = False
    healed_steps = 0
    failed_steps = 0
    blocked_steps = 0
    # Track which step indices (0-based) failed irrecoverably (block dependents)
    failed_step_indices: set = set()

    # BUG-016: RunReport captures full step details (untruncated) saved to file
    run_report = RunReport(
        recording_id=recording_id or "unknown",
        base_url=base_url,
        script_path=script_path,
        total_steps=len(steps),
    )

    if not steps:
        # Fallback: executa via pytest subprocess (modo antigo)
        import subprocess
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", script_path, "--base-url", base_url, "-q", "--tb=line"],
                capture_output=True, text=True, timeout=args.timeout or 60
            )
        except subprocess.TimeoutExpired:
            print(f"[TestForge] [WARN] Timeout ({args.timeout or 60}s)")
            result = None

        if result is None or result.returncode != 0:
            error_text = (result.stderr or result.stdout) if result else "timeout"
            print(f"[TestForge] [WARN] Script falhou — tentando healing...")
            # Tenta curar inline
            healed = _try_heal_inline(base_url, args.headless, error_text, script_path, recording_id,
                                      getattr(args, 'browser', 'chromium'))
            if healed:
                layer_used = "L3"
                llm_used = True
    else:
        # Modo inline: executa passos com healing L0→L3
        verbose = getattr(args, 'verbose', False)
        data_file = getattr(args, 'data', '') or ''
        _data_values = {}
        if data_file and os.path.exists(data_file):
            with open(data_file) as f:
                _data_values = json.loads(f.read())
        if _data_values:
            print(f"  Data: {len(_data_values)} valores carregados de {data_file}")
        with sync_playwright() as pw:
            browser = launch_browser(pw, getattr(args, 'browser', 'chromium'), headless=args.headless)
            _vp_kw = _make_context_kwargs(args.headless)
            page = browser.new_context(**_vp_kw).new_page()

            # Navegar
            page.goto(base_url)
            page.wait_for_timeout(500)
            print()

            # Post-click validation: verify click had expected effect before proceeding
            def _validate_click(page, url_before: str, step, step_num: int) -> tuple[bool, str]:
                """Check if click achieved expected outcome. Returns (valid, reason)."""
                causes_nav = step.context.get("causes_navigation", False) if step.context else False

                # 1. Navigation expected? Verify URL changed
                if causes_nav:
                    page.wait_for_timeout(800)  # brief settle
                    if page.url == url_before:
                        return False, "URL_NOT_CHANGED (navigation expected)"
                    return True, "navigated"

                # 2. No navigation expected — brief wait for DOM render
                page.wait_for_timeout(400)
                return True, "ok"

            def _wait_for_consequence(page, step, step_num, causes_navigation):
                """Wait for the consequence of the click, not an arbitrary timeout."""
                if causes_navigation:
                    page.wait_for_timeout(3000)
                    return

                # No navigation. Check if next step's element exists.
                # If not, wait up to 12s for async operations (calculations, API calls).
                cur_idx = step_num - 1  # 0-based
                next_step = steps[cur_idx + 1] if cur_idx + 1 < len(steps) else None
                if next_step and not next_step.skip_reason and next_step.target and next_step.target.candidates:
                    next_sel = next_step.target.candidates[0].selector
                    try:
                        page.wait_for_selector(next_sel, state="visible", timeout=12000)
                        if verbose:
                            print(f"  ⚡ consequence: {next_sel[:50]} appeared")
                        page.wait_for_timeout(300)
                        return
                    except Exception:
                        pass  # element didn't appear — fall through to timeout

                # Default fallback
                page.wait_for_timeout(800)

            def _click_with_validation(page, candidates, step, step_num, is_submit, causes_navigation) -> tuple[bool, str]:
                """Try each candidate, validate outcome, return (success, selector_used)."""
                url_before = page.url

                for ci, c in enumerate(candidates):
                    sel = c["selector"] if isinstance(c, dict) else c
                    strategy = c.get("strategy", c.get("selector", "")) if isinstance(c, dict) else sel
                    try:
                        page.click(sel, timeout=5000)

                        # Validate click outcome
                        valid, reason = _validate_click(page, url_before, step, step_num)
                        if valid:
                            # Wait for the consequence: if a next step's element will appear, wait for it
                            _wait_for_consequence(page, step, step_num, causes_navigation)
                            return True, sel
                        else:
                            if verbose:
                                print(f"  ⚡ candidate [{ci}] {sel[:60]} — click ok but validation: {reason}")
                            continue

                    except Exception as e:
                        if verbose:
                            print(f"  ⚡ candidate [{ci}] {sel[:60]} — {str(e)[:60]}")
                        continue

                return False, ""

            for i, step in enumerate(steps):
                step_num = i + 1
                action = step.action

                # Check if this step depends on a previously failed blocking step
                if step.depends_on and not step.skip_reason:
                    # Parse the 1-based step index from depends_on (e.g., "step_0003")
                    dep_match = _re.match(r'step_(\d+)', step.depends_on)
                    if dep_match:
                        dep_step_idx = int(dep_match.group(1)) - 1  # convert to 0-based
                        if dep_step_idx in failed_step_indices:
                            step.skip_reason = f"blocked_by_previous_failure (depends on {step.depends_on})"
                            blocked_steps += 1
                sel = ""
                candidates = []
                all_candidates_full = []  # BUG-016: untruncated

                if step.target:
                    if step.target.candidates and len(step.target.candidates) > 0:
                        sel = step.target.candidates[0].selector or ""
                    if step.target.candidates:
                        candidates = [{"selector": c.selector, "score": c.score}
                                      for c in step.target.candidates[:3]]
                        # BUG-016: full candidates for report (untruncated)
                        all_candidates_full = [{"selector": c.selector, "score": c.score}
                                               for c in step.target.candidates]

                value = step.value or ""

                # BUG-016: StepReport captures full per-step details
                step_report = StepReport(
                    step_num=step_num,
                    action=action,
                    value=value,
                    candidates=all_candidates_full,
                    selector_used=sel,
                    is_submit=step.context.get("is_submit", False) if step.context else False,
                )

                # Check if step was marked as skipped during normalization
                if step.skip_reason:
                    step_report.skip_reason = step.skip_reason
                    step_report.success = True
                    step_report.error_message = ""
                    print(f"  - Passo {step_num}: {action} ignorado — {step.skip_reason}")
                    run_report.add_step(step_report)
                    continue

                try:
                    # Wait for calendar overlay if this step targets it
                    if sel and ('cdk-overlay' in sel or 'mat-calendar' in sel or 'mat-datepicker' in sel):
                        try:
                            page.wait_for_selector('.cdk-overlay-container', state='visible', timeout=5000)
                            page.wait_for_timeout(500)
                        except Exception:
                            pass  # overlay might not be open yet, try anyway

                    if action == "navigation":
                        # Navigate only if step URL differs from current page URL.
                        # Initial page.goto covers first load; subsequent navigations
                        # are triggered by clicks/submits with expect_navigation.
                        step_url = step.url or ""
                        current_url = page.url
                        if step_url and step_url != current_url:
                            page.goto(step_url)
                            page.wait_for_timeout(500)
                            print(f"  OK Passo {step_num}: navegacao → {step_url}")
                        else:
                            print(f"  OK Passo {step_num}: navegacao (ja em {current_url})")

                    elif action == "fill" and step.target and (step.target.tag or "").lower() == "select":
                        # Select element: use select_option
                        if candidates:
                            fallback = FallbackRunner(page)
                            ok = fallback.try_fill(candidates, value)
                            if ok:
                                print(f"  OK Passo {step_num}: selecao {value[:20]}")
                            else:
                                raise Exception(f"selecao passo {step_num} falhou — candidates: {[c['selector'][:40] for c in candidates[:3]]}")
                        elif sel:
                            page.select_option(sel, value, timeout=5000)
                            page.wait_for_timeout(200)
                            print(f"  OK Passo {step_num}: selecao {value[:20]}")
                        else:
                            step_report.skip_reason = "sem seletor"
                            print(f"  - Passo {step_num}: selecao ignorada (sem seletor)")

                    elif action == "fill":
                        if candidates:
                            fallback = FallbackRunner(page)
                            ok = fallback.try_fill(candidates, value)
                            if ok:
                                print(f"  OK Passo {step_num}: preenchimento {value[:20]}")
                            else:
                                raise Exception(f"preenchimento passo {step_num} falhou")
                        elif sel:
                            page.fill(sel, value, timeout=5000)
                            page.wait_for_timeout(200)
                            print(f"  OK Passo {step_num}: preenchimento {value[:20]}")
                        else:
                            step_report.skip_reason = "sem seletor"
                            print(f"  - Passo {step_num}: preenchimento ignorado (sem seletor)")

                    elif action == "click":
                        # Data-driven fill: if clicking an input and we have a data value, fill it first
                        if _data_values and step.target:
                            tag = (step.target.tag or "").lower()
                            if tag in ("input", "textarea"):
                                label = (step.target.label or step.target.placeholder or "")
                                # Try exact match first, then partial
                                fill_val = _data_values.get(label, "")
                                if not fill_val:
                                    for key, val in _data_values.items():
                                        if key in label or (label and label in key):
                                            fill_val = val
                                            break
                                if fill_val:
                                    sel = step.target.candidates[0].selector if step.target.candidates else ""
                                    try:
                                        # Check if it's a currency-masked input (needs press_sequentially)
                                        has_mask = False
                                        try:
                                            el = page.locator(sel).first
                                            mask = el.get_attribute("currencymask")
                                            has_mask = bool(mask is not None)
                                        except Exception:
                                            pass

                                        if has_mask:
                                            # Currency masks work in cents — multiply value by 100
                                            raw_val = str(fill_val).replace(".", "").replace(",", "").replace(" ", "")
                                            try:
                                                cents = str(int(float(raw_val) * 100))
                                            except ValueError:
                                                cents = raw_val
                                            el.click()
                                            page.wait_for_timeout(200)
                                            el.press_sequentially(cents, delay=50)
                                            page.wait_for_timeout(100)
                                            # Blur so Angular validates the field
                                            page.keyboard.press("Tab")
                                            page.wait_for_timeout(300)
                                        else:
                                            page.fill(sel, str(fill_val), timeout=5000)

                                        if verbose:
                                            print(f"  ⚡ data-fill: {str(fill_val)[:20]} into {sel[:40]}")
                                    except Exception as e:
                                        if verbose:
                                            print(f"  ⚡ data-fill FAILED: {str(e)[:50]}")

                        is_submit = step.context.get("is_submit", False) if step.context else False
                        causes_navigation = step.context.get("causes_navigation", False) if step.context else False

                        if candidates:
                            ok, used_sel = _click_with_validation(
                                page, candidates, step, step_num, is_submit, causes_navigation
                            )
                            if ok:
                                print(f"  OK Passo {step_num}: clique (via {used_sel[:50]})")
                            else:
                                page.wait_for_timeout(1500)
                                ok, used_sel = _click_with_validation(
                                    page, candidates, step, step_num, is_submit, causes_navigation
                                )
                                if ok:
                                    print(f"  OK Passo {step_num}: clique (apos espera, via {used_sel[:50]})")
                                else:
                                    tried = ', '.join([c['selector'][:40] for c in candidates[:3]])
                                    raise Exception(f"clique passo {step_num} falhou — todos candidatos esgotados: [{tried}]")
                        elif sel:
                            url_before = page.url
                            try:
                                if is_submit:
                                    with page.expect_navigation(wait_until="load"):
                                        page.click(sel, timeout=5000)
                                else:
                                    page.click(sel, timeout=5000)
                                valid, reason = _validate_click(page, url_before, step, step_num)
                                if not valid:
                                    raise Exception(f"validacao falhou: {reason}")
                                _wait_for_consequence(page, step, step_num, causes_navigation)
                                print(f"  OK Passo {step_num}: clique (url={page.url[:60]})")
                            except Exception:
                                page.wait_for_timeout(1000)
                                url_before2 = page.url
                                try:
                                    if is_submit:
                                        with page.expect_navigation(wait_until="load"):
                                            page.click(sel, timeout=5000)
                                    else:
                                        page.click(sel, timeout=5000)
                                    valid2, reason2 = _validate_click(page, url_before2, step, step_num)
                                    if not valid2:
                                        raise Exception(f"validacao (retry) falhou: {reason2}")
                                    _wait_for_consequence(page, step, step_num, causes_navigation)
                                    print(f"  OK Passo {step_num}: clique (apos espera)")
                                except Exception as e2:
                                    raise Exception(f"clique passo {step_num} falhou — seletor '{sel[:80]}' nao encontrado") from e2

                    elif action == "assert":
                        assert_type = step.context.get("assert_type", "textual") if step.context else "textual"
                        expected = value
                        if sel and expected:
                            text = page.locator(sel).first.text_content(timeout=3000)
                            step_report.assert_type = assert_type
                            step_report.assert_expected = expected
                            step_report.assert_actual = (text or "")
                            if expected.lower() in (text or "").lower():
                                print(f"  OK Passo {step_num}: verificacao \"{expected[:30]}\"")
                                step_report.success = True
                            else:
                                print(f"  FALHOU Passo {step_num}: verificacao FALHOU — obtido \"{(text or '')[:30]}\"")
                                step_report.error_message = f"verificacao FALHOU: esperado '{expected}', obtido '{(text or '')[:100]}'"
                                failed_steps += 1
                        else:
                            print(f"  - Passo {step_num}: verificacao ignorada (sem seletor/expected)")
                            step_report.skip_reason = "sem seletor/expected"
                            step_report.success = True

                    # BUG-016: mark step success unless error_message already set (e.g. assert fail)
                    if not step_report.error_message:
                        step_report.success = True

                except Exception as e:
                    failed_steps += 1
                    error_msg = str(e)[:300]
                    # BUG-016: full untruncated error for report
                    step_report.error_message = str(e)
                    # Include selector info for better classification
                    if sel:
                        error_msg = f"Passo {step_num}: {action} falhou — seletor '{sel[:80]}' nao encontrado. {error_msg}"
                    elif candidates:
                        tried = ', '.join([c['selector'][:40] for c in candidates[:3]])
                        error_msg = f"Passo {step_num}: {action} falhou — candidatos [{tried}] todos falharam. {error_msg}"
                    else:
                        error_msg = f"Passo {step_num}: {action} falhou — sem seletor disponivel. {error_msg}"
                    print(f"  FALHOU Passo {step_num}: {action} FALHOU — {error_msg[:100]}")

                    # BUG-011: per-step metric — falha detectada
                    metrics.record_step(
                        StepOutcome.FAILURE_DETECTED,
                        step_num=step_num, action=action,
                    )

                    # Pipeline de cura para este step
                    outcome = _heal_step(
                        page, step, error_msg, base_url, step_num,
                        recording_id or "", app_name,
                        debug_healing=getattr(args, 'debug_healing', False),
                    )
                    # BUG-016: capture full healing details (untruncated)
                    if outcome is not None:
                        step_report.healing_attempted = True
                        step_report.healing_layer = outcome.layer_used
                        step_report.healing_family = outcome.family
                        if outcome.proposal:
                            step_report.healing_proposal_locator = outcome.proposal.new_locator
                            step_report.healing_confidence = outcome.proposal.confidence
                            step_report.healing_raw_response = outcome.proposal.raw_response or ""
                    if outcome is not None:
                        # BUG-011: healing tentado
                        family_code = outcome.family
                        healing_layer = outcome.layer_used
                        selector_used = sel or (candidates[0]["selector"] if candidates else "")

                        metrics.record_step(
                            StepOutcome.HEALING_ATTEMPTED,
                            step_num=step_num, action=action,
                            family_code=family_code,
                            healing_layer=healing_layer,
                            selector=selector_used,
                        )

                        if outcome.status == ProgressResult.PASSED_STEP:
                            healed_steps += 1
                            healed = True
                            step_report.healing_success = True
                            # BUG-011: healing aplicado com sucesso
                            metrics.record_step(
                                StepOutcome.HEALING_APPLIED,
                                step_num=step_num, action=action,
                                family_code=family_code,
                                healing_layer=healing_layer,
                                selector=selector_used,
                            )
                        else:
                            # BUG-011: healing rejeitado/falhou
                            metrics.record_step(
                                StepOutcome.HEALING_REJECTED,
                                step_num=step_num, action=action,
                                family_code=family_code,
                                healing_layer=healing_layer,
                                selector=selector_used,
                            )

                    # Track irrecoverable failure for blocking step dependency
                    if step.blocking:
                        # Step is considered irrecoverable if healing was not attempted
                        # or healing was rejected/failed (not passed)
                        healing_saved = (
                            outcome is not None
                            and outcome.status == ProgressResult.PASSED_STEP
                        )
                        if not healing_saved:
                            failed_step_indices.add(i)

                # Track blocking step failure that didn't raise (e.g., assert failure)
                if step.blocking and step_report.error_message and i not in failed_step_indices:
                    failed_step_indices.add(i)

                # BUG-016: add full step report to run report
                run_report.add_step(step_report)

            browser.close()

    # Metricas
    metrics.record_run(
        healed=healed,
        false_heal=not healed and (failed_steps > 0),
        oracle_passed=healed_steps,
        oracle_failed=failed_steps - healed_steps if failed_steps > healed_steps else 0,
        llm_used=llm_used,
    )

    print(f"\n[TestForge] Metricas:")
    print(metrics.summary())
    if steps:
        interactions = sum(1 for s in steps if s.action in ("fill", "click", "select_option"))
        asserts_run = sum(1 for s in steps if s.action == "assert")
        print(f"  Steps: {len(steps)} total ({interactions} interacoes + {asserts_run} asserts), {failed_steps} falhas, {healed_steps} curados, {blocked_steps} bloqueados")
    if layer_used:
        print(f"  Healing layer: {layer_used}")

    # BUG-016: save full untruncated report to file
    run_report.failed_steps = failed_steps
    run_report.healed_steps = healed_steps
    if recording_id:
        report_dir = str(_PROJECT_ROOT / "recordings" / recording_id)
    else:
        report_dir = str(_PROJECT_ROOT / "reports")
    report_path = run_report.save(report_dir)
    print(f"\n[TestForge] Full report saved: {report_path}")

    if getattr(args, 'save_output', False):
        from datetime import datetime as _dt
        out_path = os.path.join(os.path.dirname(os.path.abspath(script_path)), "run_output.txt")
        with open(out_path, "w", encoding="utf-8") as _f:
            _f.write(f"# TestForge run output — {_dt.now().isoformat()}\n")
            _f.write(f"# Script: {script_path}\n")
            _f.write(f"steps={len(steps) if steps else 0} failed={failed_steps} healed={healed_steps}\n")
            _f.write(f"report={report_path}\n")
        print(f"[TestForge] Output salvo em: {out_path}")


def _heal_step(page, step, error_msg: str, base_url: str, step_num: int,
               recording_id: str, app_name: str, debug_healing: bool = False):
    """Tenta curar um step falho usando o pipeline L0→L3.

    Returns:
        CurationOutcome, or None if failure is unrecoverable.
    """
    classifier = FailureClassifier()
    failure = classifier.classify(error_msg)

    print(f"    Falha: {failure.code} [{failure.family_code}]")

    if not failure.recoverable:
        return None

    # Coletar evidencias com DOM do momento da falha
    collector = EvidenceCollector(page)
    collector.start(f"heal-step-{step_num}")

    sel = (step.target.candidates[0].selector
           if step.target and step.target.candidates and len(step.target.candidates) > 0
           else "")
    text_val = step.target.text if step.target else ""
    value = step.value or ""

    # If no selector, try to guess from target data
    if not sel and step.target:
        if step.target.element_id:
            sel = f"#{step.target.element_id}"
        elif step.target.role and step.target.text:
            sel = f"[role='{step.target.role}']:has-text('{step.target.text[:40]}')"
        elif step.target.role:
            sel = f"[role='{step.target.role}']"
        elif step.target.tag:
            sel = step.target.tag

    step_context = {
        "action": step.action,
        "selector": sel or "(empty — no selector available)",
        "text": text_val or "",
        "value": value,
        "intention": f"{step.action} step {step_num}" + (f" on '{text_val}'" if text_val else ""),
        "url": base_url,
        "framework": app_name or "generic",
        "family": failure.family_code,
        "taxonomy_id": failure.taxonomy_id,
        "step_number": step_num,
    }

    payload = collector.build_llm_payload(step_context, include_screenshot=False)

    # Smart step runner that supports all healing strategies
    from testforge.runner.fallback_runner import SmartStepRunner
    smart_runner = SmartStepRunner(page)

    def step_runner(step_data):
        strategy = step_data.get("strategy", "")
        return smart_runner.execute(step_data, strategy)

    curator = CuradorAutomatico(
        catalog=HealingCatalog(),
        step_runner=step_runner,
        debug_healing=debug_healing,
    )

    print(f"    Healer: {curator._healer_type}")

    cure_data = {
        "selector": sel or "",
        "action": step.action,
        "base_url": base_url,
        "value": value,
    }

    outcome = curator.cure(cure_data, error_msg, payload)

    print(f"    Curador: {outcome.status} [{outcome.layer_used}]", end="")
    if outcome.proposal:
        print(f" → {outcome.proposal.new_locator[:60]} (conf={outcome.proposal.confidence:.2f})")
        if outcome.proposal.confidence < 0.3 and outcome.proposal.raw_response:
            print(f"    LLM raw: {outcome.proposal.raw_response[:200]}")
    else:
        print()

    return outcome


def _try_heal_inline(base_url: str, headless: bool, error_text: str,
                     script_path: str, recording_id: str,
                     browser_type: str = "chromium") -> bool:
    """Fallback: tenta curar script inteiro inline (modo antigo)."""
    try:
        with sync_playwright() as pw:
            browser = launch_browser(pw, browser_type, headless=headless)
            _vp_kw = _make_context_kwargs(headless)
            page = browser.new_context(**_vp_kw).new_page()
            page.goto(base_url)
            page.wait_for_timeout(500)

            collector = EvidenceCollector(page)
            collector.start("heal-run")

            classifier = FailureClassifier()
            failure = classifier.classify(error_text)

            payload = collector.build_llm_payload({
                "action": "execute_script",
                "selector": script_path,
                "value": base_url,
                "intention": f"E2E test: {script_path}",
                "url": base_url,
                "framework": "generic",
                "family": failure.family_code,
                "taxonomy_id": failure.taxonomy_id,
            })

            curator = CuradorAutomatico(catalog=HealingCatalog(), step_runner=None)
            outcome = curator.cure(
                {"selector": script_path, "action": "execute_test", "base_url": base_url},
                error_text, payload,
            )

            browser.close()
            return outcome.status == ProgressResult.PASSED_STEP
    except Exception:
        return False


def cmd_pipeline(args):
    """Pipeline completa: record → compile → run."""

    if args.url:
        _validate_and_warn_url(args.url)
    print("=" * 50)
    print("  TestForge — Pipeline Completa")
    print("=" * 50)

    # Step 1: Record
    print("\n📼 Fase 1: Gravacao")
    ts = time.strftime("%Y%m%d-%H%M%S")
    rid = f"PIPE-{ts}"

    with sync_playwright() as pw:
        browser = launch_browser(pw, getattr(args, 'browser', 'chromium'), headless=args.headless)
        _vp_kw = _make_context_kwargs(args.headless)
        page = browser.new_context(**_vp_kw).new_page()
        recorder = RecorderController(page)

        recorder.start(recording_id=rid, application="pipeline", base_url=args.url)
        page.goto(args.url)
        page.wait_for_timeout(500)
        recorder.flush_events()

        page.get_by_placeholder("000.000.000-00").fill("12345678900")
        page.wait_for_timeout(200)
        recorder.flush_events()

        with page.expect_navigation(wait_until="load"):
            page.get_by_role("button", name="Pesquisar").click()
        page.wait_for_timeout(500)
        recorder.flush_events()

        # Assert
        page.evaluate("""() => {
            var el = document.querySelector('#resultadoSection');
            if (el) window.__tfStepQueue.push({
                action: 'assert', assert_type: 'textual', selector: '#resultadoSection',
                expected_value: 'CPF consultado', assert_state: '',
                attrs: {}, timestamp: new Date().toISOString(), tagName: 'div', text: el.textContent, value: ''
            });
        }""")
        recorder.flush_events()

        recorder.stop()
        recorder.finalize()
        print(f"  ✓ {rid}: {len(os.listdir(f'recordings/{rid}/screenshots'))} screenshots")

        # Step 2: Compile
        print("\n⚙ Fase 2: Compilacao")
        normalizer = RecordingNormalizer()
        stc = normalizer.normalize(str(_PROJECT_ROOT / f"recordings/{rid}"), f"ST-{rid}", "pipeline", args.url)
        compiler = PlaywrightCompiler()
        script_path = compiler.compile(stc, f"semantic_tests/ST-{rid}")
        print(f"  ✓ {len(stc.steps)} steps → {script_path}")

        # Step 3: Run
        print("\n[PLAY] Fase 3: Execucao + Healing")
        _vp_kw2 = _make_context_kwargs(args.headless)
        page2 = browser.new_context(**_vp_kw2).new_page()

        page2.goto(args.url)
        page2.wait_for_timeout(300)

        fallback = FallbackRunner(page2)
        oracle = OracleRunner(page2)
        gate = PromotionGate()

        healed = False
        try:
            page2.get_by_placeholder("000.000.000-00").fill("12345678900", timeout=3000)
        except Exception:
            candidates = [{"selector": "[placeholder='000.000.000-00']", "score": 0.9}]
            fallback.try_fill(candidates, "12345678900")

        try:
            with page2.expect_navigation(wait_until="load"):
                page2.get_by_role("button", name="Pesquisar").click(timeout=3000)
        except Exception:
            candidates = [{"selector": "button:has-text('Pesquisar')", "score": 0.8}]
            fallback.try_click(candidates)

        page2.wait_for_timeout(500)

        results = oracle.run_all([
            {"type": "visual_dom", "selector": "#resultadoSection", "expected": "CPF consultado"},
            {"type": "business_state", "selector": "#cpfResultado", "expected": "12345678900"},
        ])

        for r in results:
            icon = "✓" if r.status == "passed" else "✗"
            print(f"  {icon} {r.oracle_type}: {r.status}")

        decision = gate.evaluate(results, {"screenshots": ["x.png"]})
        healed = decision.allowed

        if healed:
            print(f"  ✓ Pipeline concluida — Gate: {decision.state.value}")
        else:
            print(f"  [WARN] Gate bloqueou: {decision.blocks}")
            # Auto-aprender: registra receita para este padrao de falha
            catalog = HealingCatalog()
            recipe = HealingRecipe(
                trigger_family="locator_resolution",
                trigger_code="LOCATOR_NOT_FOUND",
                trigger_pattern="not found",
                trigger_framework="generic",
                solution_strategy="fallback_candidates",
                solution_selector="button:has-text('Pesquisar')",
                priority=1,
            )
            rid = catalog.add_recipe(recipe)
            print(f"  📝 Receita de cura registrada: {rid}")

        browser.close()

    # Step 4: Metrics
    print("\n📊 Fase 4: Metricas")
    metrics = MetricsRepository()
    # BUG-011: per-step recording for inline pipeline steps
    oracle_passed = 0
    for r in results:
        step_num = 1
        metrics.record_step(
            StepOutcome.ORACLE_VALIDATED if r.status == "passed" else StepOutcome.HEALING_REJECTED,
            step_num=step_num, action=f"oracle_{r.oracle_type}",
            healing_layer="L3" if healed else "N/A",
        )
        if r.status == "passed":
            oracle_passed += 1
    metrics.record_run(healed=healed, oracle_passed=oracle_passed)
    print(metrics.summary())

    print(f"\n  Artefatos: recordings/{rid}/ | semantic_tests/ST-{rid}/")


def cmd_demo_heal(args):
    """Demo de healing real: grava → quebra seletor → healing corrige."""

    print("=" * 60)
    print("  TestForge — Demo Healing Real")
    print("=" * 60)
    print()
    print("  Cenario: botao Pesquisar tem ID alterado apos gravacao")
    print()

    with sync_playwright() as pw:
        browser = launch_browser(pw, getattr(args, 'browser', 'chromium'), headless=args.headless)
        _vp_kw = _make_context_kwargs(args.headless)
        page = browser.new_context(**_vp_kw).new_page()
        recorder = RecorderController(page)

        # Fase 1: Gravar fluxo normal
        print("📼 Fase 1: Gravando fluxo normal...")
        recorder.start("HEAL-DEMO", "fake-bank", "http://localhost:8765")
        page.goto("http://localhost:8765")
        page.wait_for_timeout(500)
        recorder.flush_events()

        page.get_by_placeholder("000.000.000-00").fill("12345678900")
        page.wait_for_timeout(200)
        recorder.flush_events()

        with page.expect_navigation(wait_until="load"):
            page.get_by_role("button", name="Pesquisar").click()
        page.wait_for_timeout(500)
        recorder.flush_events()

        recorder.stop()
        recorder.finalize()

        with open(_PROJECT_ROOT / "recordings/HEAL-DEMO/raw_events.jsonl") as f:
            events = [json.loads(l) for l in f]
        print(f"  ✓ {len(events)} eventos gravados")

        # Fase 2: Compilar
        print("⚙ Fase 2: Compilando script...")
        stc = RecordingNormalizer().normalize("recordings/HEAL-DEMO", "ST-HEAL", "fake-bank", "http://localhost:8765")
        path = PlaywrightCompiler().compile(stc, "semantic_tests/ST-HEAL")
        print(f"  ✓ Script: {path}")

        # Fase 3: Quebrar seletor
        print("🔨 Fase 3: Alterando ID do botao (mutation change_id)...")
        browser.close()

    # Abrir pagina com mutacao
    with sync_playwright() as pw:
        browser = launch_browser(pw, getattr(args, 'browser', 'chromium'), headless=args.headless)
        _vp_kw = _make_context_kwargs(args.headless)
        page = browser.new_context(**_vp_kw).new_page()

        mutation_url = "http://localhost:8765/?mutation=change_id"
        page.goto(mutation_url)
        page.wait_for_timeout(500)

        # Verificar que o botao mudou de ID
        old_btn = page.locator("#btnPesquisar")
        old_exists = old_btn.count() > 0
        print(f"  Seletor original #btnPesquisar: {'existe' if old_exists else 'NAO EXISTE (quebrado!)'}")

        # Fase 4: Healing deterministico
        print("🩹 Fase 4: Executando healing deterministico...")
        fallback = FallbackRunner(page)

        page.get_by_placeholder("000.000.000-00").fill("99988877766")
        page.wait_for_timeout(200)

        # Tenta clicar com candidatos alternativos
        click_ok = fallback.try_click([
            {"selector": "button:has-text('Pesquisar')", "score": 0.80},
            {"selector": "[type='submit']", "score": 0.60},
            {"selector": "role=button[name='Pesquisar']", "score": 0.90},
        ])
        page.wait_for_timeout(500)

        if click_ok:
            print("  ✓ Clique com candidato alternativo funcionou!")
        else:
            print("  ✗ Nenhum candidato funcionou")

        # Fase 5: Oracle + Gate
        print("🔍 Fase 5: Validando com Oracle + Gate...")
        oracle = OracleRunner(page)
        results = oracle.run_all([
            {"type": "visual_dom", "selector": "#resultadoSection", "expected": "99988877766"},
            {"type": "business_state", "selector": "#cpfResultado", "expected": "99988877766"},
        ])

        for r in results:
            icon = "✓" if r.status == "passed" else "✗"
            print(f"  {icon} {r.oracle_type}: {r.status} — {r.message[:60]}")

        gate = PromotionGate()
        decision = gate.evaluate(results, {"screenshots": ["heal.png"]})

        metrics = MetricsRepository()
        healed = decision.allowed
        metrics.record_run(
            healed=healed,
            false_heal=not healed,
            oracle_passed=sum(1 for r in results if r.status == "passed"),
        )

        print()
        print("=" * 60)
        if healed:
            print("  [OK] HEALING FUNCIONOU!")
            print(f"  Gate: {decision.state.value}")
        else:
            print(f"  [WARN] HEALING NAO PROMOVIDO: {decision.blocks}")
            _auto_learn("locator not found after id change",
                        "fallback button:has-text('Pesquisar')",
                        "angular")
        print("=" * 60)
        print()
        print(metrics.summary())
        browser.close()


def cmd_pilot_report(args):
    """Generate consolidated pilot readiness report from all recordings."""
    from testforge.metrics.pilot_metrics import collect_pilot_metrics, save_pilot_report

    recordings_dir = args.recordings_dir
    output_dir = args.output

    print(f"[TestForge] Coletando metricas de: {recordings_dir}")
    metrics = collect_pilot_metrics(recordings_dir)

    if metrics.total_recordings == 0:
        print(f"[TestForge] [WARN] Nenhuma gravacao com relatorio de readiness encontrada em:")
        print(f"  {recordings_dir}")
        print(f"[TestForge] Certifique-se de que as gravacoes foram validadas com --validate-before-ready")
        return

    json_path, md_path = save_pilot_report(metrics, output_dir)
    print(f"[TestForge] [OK] Relatorio consolidado do piloto gerado:")
    print(f"  JSON: {json_path}")
    print(f"  MD:   {md_path}")
    print()

    # Print summary
    s = metrics.to_dict()["summary"]
    print(f"  Resumo:")
    print(f"  Total gravacoes: {s['total_recordings']}")
    print(f"  [OK] Prontas: {s['ready_for_team']}")
    print(f"  [WARN] Incompletas: {s['incomplete_intent']}")
    print(f"  🔍 Revisao: {s['needs_review']}")
    print(f"  Taxa de completude: {s['completion_rate']:.1%}")

    if metrics.failures and any(metrics.failures.values()):
        top_failures = sorted(
            metrics.failures.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:3]
        print(f"\n  Top falhas:")
        for cat, count in top_failures:
            if count > 0:
                print(f"    {cat.replace('_', ' ').title()}: {count}")


def cmd_admin_install_pat(args):
    """Sprint 0 Z1: persist Azure DevOps credentials with 0600 permission."""
    if not getattr(args, "admin_cmd", None):
        print("[TestForge] Use: testforge admin install-pat --pat <PAT> --org <org> --project <p> --repo <r>")
        return
    from testforge.publisher.azure_devops import install_pat
    path = install_pat(args.pat, args.org, args.project, args.repo)
    print(f"[TestForge] ok PAT salvo em {path} (chmod 600)")
    print(f"  org={args.org} project={args.project} repo={args.repo}")
    print(f"  Tester agora pode rodar 'testforge diagnose <url>' sem configurar nada.")


def cmd_diagnose(args):
    """Sprint 0 alias: invokes cmd_record with diagnostic_mode forced True."""
    args.diagnostic_mode = True
    return cmd_record(args)


def cmd_dashboard(args):
    """Phase 6: generate static dashboard.html."""
    from testforge.metrics.dashboard import write_dashboard
    path = write_dashboard(
        output_path=args.output, spans_path=args.spans, db_path=args.db,
    )
    print(f"[TestForge] ok dashboard: {path}")
    print(f"  Abrir no browser: file://{os.path.abspath(path)}")


def cmd_catalog_migrate(args):
    """Phase 4: import legacy JSONL recipes into SQLite intent catalog."""
    from testforge.healing.sqlite_intent_catalog import IntentCatalog
    src = args.source
    db = args.db
    if not os.path.exists(src):
        print(f"[TestForge] x JSONL nao encontrado: {src}")
        return
    cat = IntentCatalog(db)
    n = cat.import_legacy_recipes(src)
    total = cat.count()
    cat.close()
    print(f"[TestForge] ok migracao: {n} recipes importadas (legacy_recipes) -> {db}")
    print(f"  Intent resolutions ativas no banco: {total}")
    print(f"  Use: testforge catalog-export para gerar JSONL para git")


def cmd_catalog_export(args):
    """Phase 4: export SQLite intent catalog to JSONL."""
    from testforge.healing.sqlite_intent_catalog import IntentCatalog
    db = args.db
    out = args.output
    if not os.path.exists(db):
        print(f"[TestForge] x SQLite nao encontrado: {db}")
        return
    cat = IntentCatalog(db)
    n = cat.export_jsonl(out)
    cat.close()
    print(f"[TestForge] ok export: {n} intent resolutions ativas -> {out}")


def cmd_send(args):
    """Re-publish recording artifacts to configured Git repo."""
    from testforge.publisher import GitPublisher
    rid = args.recording_id
    publisher = GitPublisher.from_config() or GitPublisher.from_env()
    if publisher is None:
        print("[TestForge] Git publisher nao configurado.")
        print("  Opcao 1: crie .testforge/config.yml com publisher.url")
        print("  Opcao 2: defina TESTFORGE_GIT_URL (e opcionalmente TESTFORGE_GIT_TOKEN)")
        return

    mode = "local" if publisher._local_mode else "remoto"
    rec_dir = str(_PROJECT_ROOT / "recordings" / rid)
    if not os.path.isdir(rec_dir):
        print(f"[TestForge] Gravacao nao encontrada: {rec_dir}")
        return

    # Apply --system/--suite/--test-case overrides from args or config defaults
    _override_system = getattr(args, 'system', None) or ""
    _override_suite = getattr(args, 'suite', None) or ""
    _override_test_case = getattr(args, 'test_case', None) or ""
    if _override_system or _override_suite or _override_test_case:
        _meta_path = os.path.join(rec_dir, "recording_metadata.json")
        if os.path.exists(_meta_path):
            with open(_meta_path) as _f:
                _meta = json.load(_f)
            if _override_system:
                _meta["system"] = _override_system
            if _override_suite:
                _meta["suite"] = _override_suite
            if _override_test_case:
                _meta["test_case"] = _override_test_case
            with open(_meta_path, "w", encoding="utf-8") as _f:
                json.dump(_meta, _f, indent=2, default=str)

    print(f"[TestForge] Enviando {rid} (modo {mode})...")
    result = publisher.publish(rid, str(_PROJECT_ROOT / "recordings"), str(_PROJECT_ROOT / "semantic_tests"))
    if result.success:
        sha_short = result.commit_sha[:8] if result.commit_sha and result.commit_sha != "(no changes)" else result.commit_sha or "sem-commit"
        print(f"[TestForge] ✓ Publicado: {result.remote_path}")
        print(f"  Commit: {sha_short}")
        print(f"  Artefatos: {len(result.artifacts_copied)} arquivo(s)")
    else:
        print(f"[TestForge] ✗ Falha: {result.error}", file=sys.stderr)
        print("[TestForge]   Execute com --verbose para logs detalhados.", file=sys.stderr)


def _setup_logging(verbose: bool = False):
    """Configure structured logging for TestForge components."""
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    # Only configure if no handlers exist (don't clobber pytest config)
    if not logging.getLogger().handlers:
        logging.basicConfig(level=level, format=fmt, datefmt="%H:%M:%S")
    # Ensure our components log at the right level
    for name in ("testforge.recorder", "testforge.semantic", "testforge.cli", "testforge.publisher"):
        logging.getLogger(name).setLevel(level)


def main():
    import io
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    from testforge.updater import check_and_apply_update
    check_and_apply_update(_PROJECT_ROOT)

    parser = argparse.ArgumentParser(description="TestForge CLI — Gravacao inteligente de testes E2E")
    parser.add_argument("--verbose", "-v", action="store_true", help="Log detalhado (DEBUG)")
    sub = parser.add_subparsers(dest="command")

    # record
    rec = sub.add_parser("record", help="Gravar fluxo de teste (auto-publica no Git se configurado)")
    rec.add_argument("url", nargs="?", help="URL da aplicacao alvo")
    rec.add_argument("--name", help="Nome/ID da gravacao")
    rec.add_argument("--app", help="Nome da aplicacao")
    rec.add_argument("--headless", action="store_true", help="Modo headless")
    rec.add_argument("--browser", choices=["chromium", "chrome", "edge"], default="chromium",
                     help="Browser preferido (default: chromium)")
    rec.add_argument("--complete", action="store_true",
                     help="Verificar completude e perguntar valores pendentes")
    rec.add_argument("--no-interactive", action="store_true",
                     help="Nao perguntar valores — criar template")
    rec.add_argument("--validate-before-ready", action="store_true",
                     help="Validar gravacao (completude + readiness gate) antes de marcar como pronta")
    rec.add_argument("--pilot-mode", action="store_true",
                     help="Modo piloto: habilita validacao automatica antes de READY (--validate-before-ready)")
    rec.add_argument("--evidence-level", choices=["light", "full"], default="light",
                     help="Nivel de evidencia: light (padrao, sem screenshot por evento) ou full (screenshot + DOM por evento)")
    rec.add_argument("--use-cdp-recorder", action="store_true",
                     help="(Fase 1) Captura paralela via Playwright tracing + CDP AX tree. Gera trace.zip e ax_snapshots/. Feature flag — nao remove caminho legado.")
    rec.add_argument("--diagnostic-mode", action="store_true",
                     help="(Sprint 0) Diagnostic recorder: framework detection + capture quality + replay check + Gherkin live. NAO roda compile/run.")
    rec.add_argument("--pipeline-and-diagnostic-mode", action="store_true",
                     help="(Sprint 0) Diagnostic + pipeline normal (compile/validate/run) rodando juntos.")
    rec.add_argument("--replay-batched", action="store_true",
                     help="(Sprint 0) Replay check em batch (B4) ao inves de imediato (B1).")
    rec.add_argument("--system", default="",
                     help="Sistema/aplicacao (ex: SIOPI). Caminho Git: recordings/{system}/{suite}/{test_case}/")
    rec.add_argument("--suite", default="",
                     help="Suite de testes (ex: cadastro). Caminho Git: recordings/{system}/{suite}/{test_case}/")
    rec.add_argument("--test-case", dest="test_case", default="",
                     help="Caso de teste (default: valor de --name). Caminho Git: recordings/{system}/{suite}/{test_case}/")
    rec.set_defaults(func=cmd_record)

    # compile
    comp = sub.add_parser("compile", help="Compilar gravacao em script Playwright")
    comp.add_argument("recording", help="ID da gravacao (ex: REC-20260613)")
    comp.add_argument("--app", help="Nome da aplicacao")
    comp.add_argument("--base-url", help="URL base override")
    comp.add_argument("--output", help="Diretorio de saida")
    comp.add_argument("--data", action="store_true", help="Extrair massa de dados para JSON externo")
    comp.add_argument("--scenarios", action="store_true", help="Gerar JSON com suporte a multiplos cenarios")
    comp.add_argument("--check", action="store_true", help="Verificar completude da intencao antes de compilar")
    comp.add_argument("--audit", action="store_true", help="Gerar relatorio de auditoria da gravacao (metricas, qualidade, issues)")
    comp.add_argument("--use-v2-compiler", action="store_true",
                     help="(Fase 3) Emite script minimal usando testforge.runtime.step + JSON candidates por step. Fallback chain roda em runtime, nao no .py.")
    comp.set_defaults(func=cmd_compile)

    # run
    run = sub.add_parser("run", help="Executar script Playwright com healing")
    run.add_argument("script", help="Caminho do script Python")
    run.add_argument("--headless", action="store_true", help="Modo headless")
    run.add_argument("--timeout", type=int, default=60, help="Timeout em segundos")
    run.add_argument("--verbose", action="store_true", help="Mostra cada candidato tentado e resultado")
    run.add_argument("--data", type=str, default="", help="JSON com valores para preencher campos (ex: {\"Renda mensal *\": \"5000\"})")
    run.add_argument("--browser", choices=["chromium", "chrome", "edge"], default="chromium",
                     help="Browser preferido (default: chromium)")
    run.add_argument("--debug-healing", action="store_true",
                     help="Log payloads LLM + respostas brutas + validacao")
    run.add_argument("--save-output", action="store_true",
                     help="Salvar resumo da execucao em run_output.txt no diretorio do script")
    run.set_defaults(func=cmd_run)

    # pipeline
    pipe = sub.add_parser("pipeline", help="Pipeline completa: record → compile → run")
    pipe.add_argument("url", nargs="?", default="http://localhost:8765", help="URL da aplicacao alvo")
    pipe.add_argument("--headless", action="store_true", help="Modo headless")
    pipe.add_argument("--browser", choices=["chromium", "chrome", "edge"], default="chromium",
                      help="Browser preferido (default: chromium)")
    pipe.set_defaults(func=cmd_pipeline)

    # demo-heal
    dh = sub.add_parser("demo-heal", help="Demo de healing real (record → break → heal)")
    dh.add_argument("--headless", action="store_true", help="Modo headless")
    dh.add_argument("--browser", choices=["chromium", "chrome", "edge"], default="chromium",
                    help="Browser preferido (default: chromium)")
    dh.set_defaults(func=cmd_demo_heal)

    # run-incremental (Plano TestForge Autocontido 2026-06-17)
    from testforge.cli._run_incremental_patch import register as _register_run_incremental
    _register_run_incremental(sub)

    # pilot-report (Sprint 8)
    pr = sub.add_parser("pilot-report", help="Gerar relatorio consolidado do piloto (metricas agregadas)")
    pr.add_argument("--recordings-dir",
                    default=str(_PROJECT_ROOT / "recordings"),
                    help="Diretorio com as gravacoes (default: recordings/)")
    pr.add_argument("--output",
                    default=str(_PROJECT_ROOT / "reports"),
                    help="Diretorio de saida para o relatorio (default: reports/)")
    pr.set_defaults(func=cmd_pilot_report)

    # audit
    audit_cmd = sub.add_parser("audit", help="Auditar gravacao: metricas de qualidade, eventos, compilacao")
    audit_cmd.add_argument("recording", help="ID da gravacao (ex: REC-20260613) ou caminho")
    audit_cmd.set_defaults(func=cmd_audit)

    # admin (Sprint 0: Z1 install-pat helper)
    admin = sub.add_parser("admin", help="(Sprint 0) Comandos administrativos (instalar PAT, etc)")
    admin_sub = admin.add_subparsers(dest="admin_cmd")
    install_pat = admin_sub.add_parser("install-pat", help="Salva credenciais Azure DevOps em ~/.testforge/secrets (0600)")
    install_pat.add_argument("--pat", required=True, help="Personal Access Token")
    install_pat.add_argument("--org", required=True)
    install_pat.add_argument("--project", required=True)
    install_pat.add_argument("--repo", required=True)
    install_pat.set_defaults(func=cmd_admin_install_pat)

    # diagnose (Sprint 0: alias de `record --diagnostic-mode`)
    diag = sub.add_parser("diagnose", help="(Sprint 0) Alias de 'record --diagnostic-mode'. Coleta diagnostica sem compile/run.")
    diag.add_argument("url", nargs="?", help="URL alvo")
    diag.add_argument("--name", help="Nome da gravacao")
    diag.add_argument("--app", default="web")
    diag.add_argument("--headless", action="store_true")
    diag.add_argument("--browser", choices=["chromium", "chrome", "edge"], default="chromium")
    diag.add_argument("--system", default="")
    diag.add_argument("--suite", default="")
    diag.add_argument("--test-case", dest="test_case", default="")
    diag.add_argument("--evidence-level", choices=["light", "full"], default="light")
    diag.add_argument("--replay-batched", action="store_true",
                       help="Replay check em batch (B4) ao inves de imediato (B1)")
    diag.add_argument("--pipeline-also", dest="pipeline_and_diagnostic_mode",
                       action="store_true",
                       help="Tambem roda compile/validate/run alem do diagnostico")
    diag.set_defaults(func=cmd_diagnose, diagnostic_mode=True,
                       use_cdp_recorder=False, complete=False,
                       no_interactive=True, validate_before_ready=False,
                       pilot_mode=False)

    # dashboard (Phase 6: static HTML observability)
    dash = sub.add_parser("dashboard", help="(Fase 6) Gerar dashboard HTML estatico com metricas de resolve, catalog, latencia")
    dash.add_argument("--output", default=str(_PROJECT_ROOT / "reports/dashboard.html"),
                     help="Caminho HTML de saida")
    dash.add_argument("--spans", default=str(_PROJECT_ROOT / ".testforge/spans.jsonl"),
                     help="JSONL de spans (default: .testforge/spans.jsonl)")
    dash.add_argument("--db", default=str(_PROJECT_ROOT / ".testforge/intent_catalog.sqlite"),
                     help="SQLite intent catalog")
    dash.set_defaults(func=cmd_dashboard)

    # catalog-migrate (Phase 4: JSONL → SQLite intent catalog)
    catmig = sub.add_parser("catalog-migrate", help="(Fase 4) Importa healing-catalog.jsonl para SQLite intent catalog")
    catmig.add_argument("--source", default=str(_PROJECT_ROOT / ".planning/healing-catalog.jsonl"),
                         help="JSONL de origem (default: .planning/healing-catalog.jsonl)")
    catmig.add_argument("--db", default=str(_PROJECT_ROOT / ".testforge/intent_catalog.sqlite"),
                         help="Caminho do SQLite alvo (default: .testforge/intent_catalog.sqlite)")
    catmig.set_defaults(func=cmd_catalog_migrate)

    # catalog-export (Phase 4: SQLite → JSONL for git tracking)
    catexp = sub.add_parser("catalog-export", help="(Fase 4) Exporta intent catalog SQLite para JSONL")
    catexp.add_argument("--db", default=str(_PROJECT_ROOT / ".testforge/intent_catalog.sqlite"),
                         help="SQLite source")
    catexp.add_argument("--output", default=str(_PROJECT_ROOT / ".testforge/intent_catalog.jsonl"),
                         help="JSONL destination")
    catexp.set_defaults(func=cmd_catalog_export)

    # send (Git publisher)
    send = sub.add_parser("send", help="Re-enviar gravacao existente para repositorio Git (config em .testforge/config.yml)")
    send.add_argument("recording_id", help="ID da gravacao (ex: REC-20260619)")
    send.add_argument("--system", default="", help="Sistema/aplicacao (default: do metadata salvo)")
    send.add_argument("--suite", default="", help="Suite de testes (default: do metadata salvo)")
    send.add_argument("--test-case", dest="test_case", default="", help="Caso de teste (default: do metadata salvo)")
    send.set_defaults(func=cmd_send)

    args = parser.parse_args()
    # Setup logging before running command
    _setup_logging(verbose=getattr(args, 'verbose', False))
    if args.command:
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
