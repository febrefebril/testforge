"""TestForge Doctor — diagnostico do ambiente de instalacao.

Nao depende de rede. Nao abre navegador em modo headed. Cada verificacao
retorna um resultado estruturado com severidade e dica de correcao, para que
o instalador, a GUI e o CLI usem exatamente a mesma fonte de verdade.
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

FATAL = "fatal"
WARN = "warn"
INFO = "info"


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str = ""
    hint: str = ""
    severity: str = FATAL
    data: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Navegadores do sistema
#
# Politica do ambiente corporativo: os bundles do Playwright NAO podem ser
# baixados. Sempre se usa o navegador ja instalado no sistema operacional,
# via `channel` do Playwright (msedge / chrome). O doctor precisa dizer QUAL
# canal existe e como fixa-lo, nunca mandar rodar `playwright install`.
# --------------------------------------------------------------------------- #

_WINDOWS_CANDIDATES = (
    ("msedge", r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
    ("msedge", r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
    ("chrome", r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
    ("chrome", r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
    ("chrome", r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
)

_POSIX_CANDIDATES = (
    ("msedge", "microsoft-edge"),
    ("msedge", "microsoft-edge-stable"),
    ("chrome", "google-chrome"),
    ("chrome", "google-chrome-stable"),
    ("chromium", "chromium"),
    ("chromium", "chromium-browser"),
)

_MACOS_CANDIDATES = (
    ("msedge", "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
    ("chrome", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
)


def detect_system_browsers() -> list[tuple[str, str]]:
    """Retorna [(channel, caminho)] dos navegadores instalados no sistema."""
    found: list[tuple[str, str]] = []
    seen: set[str] = set()

    def add(channel: str, path: str) -> None:
        if channel in seen:
            return
        seen.add(channel)
        found.append((channel, path))

    if os.name == "nt":
        for channel, template in _WINDOWS_CANDIDATES:
            expanded = os.path.expandvars(template)
            if "%" not in expanded and Path(expanded).is_file():
                add(channel, expanded)
    elif sys.platform == "darwin":
        for channel, path in _MACOS_CANDIDATES:
            if Path(path).is_file():
                add(channel, path)
    for channel, executable in _POSIX_CANDIDATES:
        resolved = shutil.which(executable)
        if resolved:
            add(channel, resolved)
    return found


def preferred_channel() -> str:
    """Canal recomendado: respeita TESTFORGE_BROWSER, senao usa o primeiro achado."""
    override = os.getenv("TESTFORGE_BROWSER", "").strip().lower()
    if override in {"edge", "msedge"}:
        return "msedge"
    if override in {"chrome", "chromium"}:
        return override
    detected = detect_system_browsers()
    return detected[0][0] if detected else ""


def _run(command: list[str], timeout: int = 10) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception as exc:
        return 1, str(exc)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def _check_python() -> Check:
    ok = sys.version_info >= (3, 10)
    return Check(
        name="python",
        ok=ok,
        detail=sys.version.split()[0],
        hint="" if ok else "Instale Python 3.10 ou superior e recrie o .venv.",
        severity=FATAL,
    )


def _check_tkinter() -> Check:
    ok = importlib.util.find_spec("tkinter") is not None
    return Check(
        name="tkinter",
        ok=ok,
        detail="disponivel" if ok else "ausente",
        hint="" if ok else "Reinstale o Python marcando a opcao tcl/tk. A GUI nao abre sem tkinter.",
        severity=FATAL,
    )


def _check_git() -> Check:
    path = shutil.which("git")
    if not path:
        return Check(
            name="git",
            ok=False,
            detail="nao encontrado no PATH",
            hint="Git e necessario para auto-update e publicacao. Sem ele use o fallback de pacote local.",
            severity=WARN,
        )
    _rc, out = _run([path, "--version"], timeout=5)
    return Check(name="git", ok=True, detail=out.strip().splitlines()[0] if out.strip() else path)


def _check_project(root: Path) -> Check:
    ok = (root / "pyproject.toml").is_file() and (root / "src" / "testforge").is_dir()
    return Check(
        name="project",
        ok=ok,
        detail=str(root),
        hint="" if ok else "Execute o doctor a partir da raiz do repositorio TestForge.",
        severity=FATAL,
    )


def _check_package() -> Check:
    spec = importlib.util.find_spec("testforge")
    if spec is None:
        return Check(
            name="testforge_instalado",
            ok=False,
            detail="pacote nao importavel",
            hint="Rode: .venv\\Scripts\\python.exe -m pip install -e .[dev]",
            severity=FATAL,
        )
    try:
        from testforge.version import get_version

        version = get_version()
    except Exception as exc:
        version = "desconhecida (" + str(exc) + ")"
    return Check(name="testforge_instalado", ok=True, detail=version)


def _check_playwright_package() -> Check:
    ok = importlib.util.find_spec("playwright") is not None
    return Check(
        name="playwright_pacote",
        ok=ok,
        detail="disponivel" if ok else "ausente",
        hint="" if ok else "Rode: .venv\\Scripts\\python.exe -m pip install playwright",
        severity=FATAL,
    )


def _check_system_browser() -> Check:
    detected = detect_system_browsers()
    if not detected:
        return Check(
            name="navegador_do_sistema",
            ok=False,
            detail="nenhum Edge/Chrome encontrado",
            hint=(
                "O TestForge usa o navegador ja instalado (canal msedge/chrome). "
                "Solicite a instalacao do Microsoft Edge pelo catalogo corporativo."
            ),
            severity=FATAL,
        )
    listing = ", ".join(channel + " (" + path + ")" for channel, path in detected)
    return Check(
        name="navegador_do_sistema",
        ok=True,
        detail=listing,
        severity=INFO,
        data={"detected": [{"channel": c, "path": p} for c, p in detected]},
    )


def _check_browser_preference() -> Check:
    override = os.getenv("TESTFORGE_BROWSER", "").strip()
    channel = preferred_channel()
    if not channel:
        return Check(
            name="browser_preferido",
            ok=False,
            detail="indefinido",
            hint="Sem navegador do sistema nao ha canal a preferir.",
            severity=FATAL,
        )
    detail = channel + (" (via TESTFORGE_BROWSER=" + override + ")" if override else " (detectado)")
    return Check(
        name="browser_preferido",
        ok=True,
        detail=detail,
        hint=(
            ""
            if override
            else "Opcional: fixe com TESTFORGE_BROWSER=edge para evitar tentativa de bundle inexistente."
        ),
        severity=INFO,
    )


def _check_browser_launch() -> Check:
    """Abre o navegador de verdade, em headless, pelo canal do sistema.

    Nunca sugere `playwright install`: o download de bundle e bloqueado neste
    ambiente e a instrucao so geraria retrabalho.
    """
    if importlib.util.find_spec("playwright") is None:
        return Check(
            name="browser_launch",
            ok=False,
            detail="playwright ausente",
            hint="Instale o pacote Python playwright (nao os bundles de navegador).",
            severity=FATAL,
        )
    channel = preferred_channel()
    order: list[tuple[str, dict]] = []
    if channel and channel != "chromium":
        order.append((channel, {"channel": channel}))
    for extra in ("msedge", "chrome"):
        if extra != channel:
            order.append((extra, {"channel": extra}))
    order.append(("chromium (bundle)", {}))

    attempts: list[str] = []
    working = ""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            for label, kwargs in order:
                try:
                    browser = pw.chromium.launch(headless=True, **kwargs)
                    browser.close()
                    working = label
                    attempts.append(label + "=ok")
                    break
                except Exception as exc:
                    attempts.append(label + "=falhou (" + str(exc).splitlines()[0][:100] + ")")
    except Exception as exc:
        attempts.append("sync_playwright=falhou (" + str(exc).splitlines()[0][:100] + ")")
    return Check(
        name="browser_launch",
        ok=bool(working),
        detail=("navegador utilizavel: " + working) if working else " | ".join(attempts),
        hint=(
            ""
            if working
            else "Nenhum canal abriu. Verifique se o Edge esta instalado e se a politica "
            "corporativa permite abri-lo em modo automatizado. Alternativa: TESTFORGE_USE_CDP."
        ),
        severity=FATAL,
        data={"attempts": attempts, "working": working},
    )


def _check_git_profiles(root: Path) -> Check:
    config = root / "testforge_git.yml"
    if not config.is_file():
        return Check(
            name="testforge_git_yml",
            ok=False,
            detail="ausente",
            hint="Copie testforge_git.example.yml para testforge_git.yml e preencha os perfis update e publication.",
            severity=WARN,
        )
    try:
        from testforge.config.git_profiles import load_git_profiles

        profiles = load_git_profiles(root)
    except Exception as exc:
        return Check(
            name="testforge_git_yml",
            ok=False,
            detail=str(exc),
            hint="Corrija testforge_git.yml. Credencial nunca deve aparecer dentro da URL.",
            severity=FATAL,
        )
    detail = (
        "update=" + ("on" if profiles.update.enabled else "off")
        + " branch=" + (profiles.update.branch or "-")
        + " | publication=" + ("on" if profiles.publication.enabled else "off")
        + " branch=" + (profiles.publication.branch or "-")
    )
    return Check(name="testforge_git_yml", ok=True, detail=detail, severity=INFO)


def _check_legacy_config(root: Path) -> Check:
    legacy = [name for name in ("testforge_update.yml", ".testforge/config.yml") if (root / name).exists()]
    return Check(
        name="config_legada",
        ok=not legacy,
        detail=", ".join(legacy) if legacy else "nenhuma",
        hint="Migre para testforge_git.yml e remova os arquivos legados." if legacy else "",
        severity=WARN,
    )


def _check_workspace_writable(root: Path) -> Check:
    target = root / "recordings"
    try:
        target.mkdir(parents=True, exist_ok=True)
        probe = target / ".tf_write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except Exception as exc:
        return Check(
            name="workspace_gravavel",
            ok=False,
            detail=str(exc),
            hint="A pasta do projeto precisa ser gravavel pelo usuario.",
            severity=FATAL,
        )
    return Check(name="workspace_gravavel", ok=True, detail=str(target))


def _check_encoding() -> Check:
    enc = (sys.stdout.encoding or "").lower()
    ok = "utf" in enc
    return Check(
        name="console_utf8",
        ok=ok,
        detail=enc or "desconhecido",
        hint="" if ok else "Defina PYTHONUTF8=1 para evitar erro de acentuacao em logs e relatorios.",
        severity=WARN,
    )


def run_doctor(root: Path, *, deep: bool = False) -> list[Check]:
    """Executa as verificacoes. deep=True tenta abrir um navegador headless."""
    root = Path(root).resolve()
    checks: list[Check] = [
        _check_python(),
        _check_tkinter(),
        _check_git(),
        _check_project(root),
        _check_package(),
        _check_playwright_package(),
        _check_system_browser(),
        _check_browser_preference(),
        _check_git_profiles(root),
        _check_legacy_config(root),
        _check_workspace_writable(root),
        _check_encoding(),
    ]
    if deep:
        checks.append(_check_browser_launch())
    return checks


def has_blocker(checks: list[Check]) -> bool:
    return any(check.severity == FATAL and not check.ok for check in checks)


def format_report(checks: list[Check]) -> str:
    lines = ["TestForge Doctor", "=" * 60]
    width = max(len(check.name) for check in checks)
    for check in checks:
        if check.ok:
            mark = "[OK]  "
        elif check.severity == FATAL:
            mark = "[ERRO]"
        else:
            mark = "[AVISO]"
        lines.append(mark + " " + check.name.ljust(width) + "  " + check.detail)
        if check.hint and not check.ok:
            lines.append("       -> " + check.hint)
    lines.append("=" * 60)
    if has_blocker(checks):
        lines.append("RESULTADO: BLOQUEADO. Corrija os itens marcados como ERRO antes de gravar.")
    else:
        lines.append("RESULTADO: ambiente apto para gravar.")
    return "\n".join(lines)
