from __future__ import annotations

import json
import logging
import os
import urllib.request
from dataclasses import dataclass
from typing import Optional

from testforge.core.models.report import Report

logger = logging.getLogger("testforge.notification.teams")


@dataclass
class TeamsConfig:
    webhook_url: str = ""

    @staticmethod
    def from_env() -> TeamsConfig:
        return TeamsConfig(
            webhook_url=os.environ.get("TF_NOTIFY_TEAMS_WEBHOOK", ""),
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.webhook_url)


class TeamsNotifier:
    def __init__(self, config: Optional[TeamsConfig] = None):
        self.config = config or TeamsConfig.from_env()

    def send_report(self, report: Report) -> bool:
        if not self.config.is_configured:
            logger.warning("Notificação não enviada: Teams não configurado")
            return False

        icon = "✅" if report.status == "passed" else "⚠️" if report.status == "partial" else "❌"
        color_map = {"passed": "00cc66", "partial": "ffaa00", "failed": "e94560"}
        theme_color = color_map.get(report.status, "0078d4")

        title = f"{icon} TestForge - {report.test_name}: {report.status}"
        text = self._build_text(report)

        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": theme_color,
            "title": title,
            "text": text,
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.config.webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=10)
            logger.info("Mensagem enviada para o Teams")
            return True
        except Exception as e:
            logger.warning("Notificação não enviada: erro no Teams: %s", e)
            return False

    @staticmethod
    def _build_text(report: Report) -> str:
        icon = "✅" if report.status == "passed" else "⚠️" if report.status == "partial" else "❌"
        parts = [
            f"**{report.summary.executive}**",
            f"",
            f"| | |",
            f"|---|---|",
            f"|**Teste**|{report.test_name}|",
            f"|**Status**|{icon} {report.status}|",
            f"|**Duração**|{report.duration_ms}ms|",
            f"|**Modo**|{report.mode}|",
            f"",
            f"**Passos:**",
        ]
        for i, step in enumerate(report.steps):
            icon_s = "🟢" if step.status == "passed" else "🔴" if step.status == "failed" else "⏭️"
            name = step.intention or step.name
            parts.append(f"- {icon_s} [{i+1}] {name} {step.duration_ms}ms")
            if step.error_message:
                parts.append(f"  ⚠️ {step.error_message}")

        return "\n".join(parts)
