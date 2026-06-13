from __future__ import annotations


def get_launch_args() -> dict:
    return {
        "args": [
            "--no-first-run",
            "--disable-background-networking",
            "--disable-sync",
            "--disable-translate",
            "--disable-default-apps",
            "--disable-notifications",
            "--no-default-browser-check",
            "--disable-client-side-phishing-detection",
            "--disable-component-update",
            "--no-pings",
            "--mute-audio",
            "--disable-blink-features=AutomationControlled",
        ],
    }


def get_context_options() -> dict:
    return {
        "viewport": {"width": 1280, "height": 720},
        "locale": "pt-BR",
        "permissions": [],
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "extra_http_headers": {
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        },
    }


ANTI_DETECTION_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['pt-BR', 'pt', 'en'] });
"""
