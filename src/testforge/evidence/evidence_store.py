"""TestForge — Evidence Store (JSONL-based)."""
import json
import os
import glob
from typing import Optional


class EvidenceStore:
    """Armazena e consulta evidencias em JSONL + filesystem."""

    def __init__(self, evidence_root: str = "evidence"):
        self._root = evidence_root

    def list_runs(self) -> list[str]:
        """Lista todos os run_ids."""
        if not os.path.isdir(self._root):
            return []
        return [d for d in os.listdir(self._root)
                if os.path.isdir(os.path.join(self._root, d))]

    def get_manifest(self, run_id: str) -> Optional[dict]:
        path = os.path.join(self._root, run_id, "manifest.json")
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return None

    def get_steps(self, run_id: str) -> list[dict]:
        path = os.path.join(self._root, run_id, "steps.jsonl")
        if not os.path.exists(path):
            return []
        steps = []
        with open(path) as f:
            for line in f:
                steps.append(json.loads(line))
        return steps

    def get_network_log(self, run_id: str) -> list[dict]:
        path = os.path.join(self._root, run_id, "network_log.json")
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return []

    def get_sensitive_alerts(self, run_id: str) -> list[dict]:
        path = os.path.join(self._root, run_id, "sensitive_data_alert.json")
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
                return data.get("alerts", [])
        return []

    def get_screenshots(self, run_id: str) -> list[str]:
        pattern = os.path.join(self._root, run_id, "screenshots", "*.png")
        return sorted(glob.glob(pattern))

    def list_pending_reviews(self) -> list[dict]:
        """Lista runs com alertas de dados sensiveis pendentes."""
        pending = []
        for run_id in self.list_runs():
            alerts = self.get_sensitive_alerts(run_id)
            if alerts:
                manifest = self.get_manifest(run_id) or {}
                pending.append({
                    "run_id": run_id,
                    "alert_count": len(alerts),
                    "started_at": manifest.get("started_at"),
                })
        return pending
