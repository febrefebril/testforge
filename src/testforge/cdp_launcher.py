"""TestForge - Edge/Chrome CDP auto-launcher para ambiente Windows/CAIXA."""
from __future__ import annotations
import os
import platform
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

DEFAULT_CDP_PORT = 9222

EDGE_PATHS_WINDOWS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge Beta\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge Beta\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge Dev\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge Dev\Application\msedge.exe",
]

CHROME_PATHS_WINDOWS = [
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome Beta\Application\chrome.exe",
    r"C:\Program Files\Google\Chrome Beta\Application\chrome.exe",
]


def is_windows() -> bool:
    return platform.system() == "Windows"


def _find_edge():
    if not is_windows():
        return None
    for p in EDGE_PATHS_WINDOWS:
        if Path(p).exists():
            return p
    return None


def _find_chrome():
    if not is_windows():
        return None
    for p in CHROME_PATHS_WINDOWS:
        if Path(p).exists():
            return p
    return None


def find_corporate_browser(preferred="auto"):
    pref = (preferred or "auto").lower().strip()
    if pref == "edge":
        p = _find_edge()
        if p: return ("edge", p)
        print("[TestForge] AVISO: Edge nao encontrado, tentando Chrome", file=sys.stderr)
        p = _find_chrome()
        return ("chrome", p) if p else None
    if pref == "chrome":
        p = _find_chrome()
        if p: return ("chrome", p)
        print("[TestForge] AVISO: Chrome nao encontrado, tentando Edge", file=sys.stderr)
        p = _find_edge()
        return ("edge", p) if p else None
    # auto
    p = _find_edge()
    if p: return ("edge", p)
    p = _find_chrome()
    return ("chrome", p) if p else None


def is_cdp_alive(port=DEFAULT_CDP_PORT, timeout=1.0):
    try:
        with urllib.request.urlopen(f"http://localhost:{port}/json/version", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def wait_for_cdp(port=DEFAULT_CDP_PORT, max_wait=15.0):
    start = time.time()
    while time.time() - start < max_wait:
        if is_cdp_alive(port):
            return True
        time.sleep(0.5)
    return False


def get_profile_dir(browser_name):
    p = Path(tempfile.gettempdir()) / f"testforge-{browser_name}-cdp"
    p.mkdir(parents=True, exist_ok=True)
    return p


def launch_browser_cdp_background(port=DEFAULT_CDP_PORT, start_url="about:blank",
                                   preferred_browser="auto", quiet=False):
    if not is_windows():
        return (False, "Modo --windows-caixa so funciona em Windows")
    if is_cdp_alive(port):
        return (True, f"CDP ja rodando porta {port}")
    browser = find_corporate_browser(preferred=preferred_browser)
    if browser is None:
        return (False, "Edge/Chrome nao encontrado em Program Files")
    name, path = browser
    profile = get_profile_dir(name)
    args = [path, f"--remote-debugging-port={port}", f"--user-data-dir={profile}",
            "--no-first-run", "--no-default-browser-check",
            "--disable-features=msEdgeSignIn", start_url]
    if not quiet:
        print(f"[TestForge] Abrindo {name.upper()} corporativo (porta CDP {port})")
        print(f"[TestForge]   Executavel: {path}")
        print(f"[TestForge]   Profile: {profile}")
    try:
        if is_windows():
            DETACHED = 0x00000008
            NEW_GROUP = 0x00000200
            subprocess.Popen(args, creationflags=DETACHED | NEW_GROUP,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           stdin=subprocess.DEVNULL, close_fds=True)
        else:
            subprocess.Popen(args, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
                           start_new_session=True)
    except Exception as e:
        return (False, f"Falha ao iniciar {name}: {e}")
    if not quiet:
        print("[TestForge]   Aguardando CDP...")
    if wait_for_cdp(port, max_wait=15.0):
        return (True, f"{name.upper()} CDP ativo porta {port}")
    return (False, f"{name} iniciado mas CDP nao respondeu em 15s")


def ensure_cdp_ready(port=DEFAULT_CDP_PORT, preferred_browser="auto", quiet=False):
    cdp_url = f"http://localhost:{port}"
    if is_cdp_alive(port):
        os.environ["TESTFORGE_USE_CDP"] = cdp_url
        if not quiet:
            print(f"[TestForge] CDP ja rodando em {cdp_url}")
        return (True, cdp_url)
    ok, msg = launch_browser_cdp_background(port=port, preferred_browser=preferred_browser, quiet=quiet)
    if ok:
        os.environ["TESTFORGE_USE_CDP"] = cdp_url
        if not quiet:
            print(f"[TestForge] {msg}")
            print(f"[TestForge] TESTFORGE_USE_CDP={cdp_url}")
        return (True, cdp_url)
    return (False, msg)


def get_preferred_browser(args):
    cli_arg = getattr(args, "cdp_browser", None)
    if cli_arg:
        return cli_arg.lower().strip()
    env_var = os.environ.get("TESTFORGE_CDP_BROWSER", "").lower().strip()
    if env_var in ("edge", "chrome", "auto"):
        return env_var
    return "auto"


def is_windows_caixa_mode(args):
    flag = getattr(args, "windows_caixa", False)
    env = os.environ.get("TESTFORGE_WINDOWS_CAIXA", "").strip().lower() in ("1", "true", "yes")
    return flag or env
