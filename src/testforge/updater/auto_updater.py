"""TestForge auto-updater — git pull on startup when configured in testforge_update.yml."""
import logging
import subprocess
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_CONFIG_FILE = "testforge_update.yml"


def _load_config(project_root: Path) -> dict:
    config_path = project_root / _CONFIG_FILE
    if not config_path.exists():
        return {"enabled": False}
    try:
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as exc:
        logger.warning("auto-updater: failed to read %s: %s", _CONFIG_FILE, exc)
        return {"enabled": False}


def check_and_apply_update(project_root: Path) -> bool:
    """Pull latest changes from git if auto-update is enabled. Returns True if updated."""
    config = _load_config(project_root)
    if not config.get("enabled"):
        return False

    remote = config.get("remote", "origin")
    branch = config.get("branch", "main")
    quiet = config.get("quiet", False)

    try:
        result = subprocess.run(
            ["git", "pull", remote, branch],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.warning("auto-updater: git pull failed: %s", result.stderr.strip())
            return False

        already_up_to_date = "Already up to date" in result.stdout
        if not quiet:
            if not already_up_to_date:
                print(f"[TestForge] Updated from {remote}/{branch}")
        return not already_up_to_date
    except FileNotFoundError:
        logger.warning("auto-updater: git not found in PATH")
        return False
    except subprocess.TimeoutExpired:
        logger.warning("auto-updater: git pull timed out")
        return False
    except Exception as exc:
        logger.warning("auto-updater: unexpected error: %s", exc)
        return False
