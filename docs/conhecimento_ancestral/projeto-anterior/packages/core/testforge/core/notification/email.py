from __future__ import annotations

import logging
import os
import smtplib
import ssl
from dataclasses import dataclass, field
from email.mime.text import MIMEText
from typing import Optional

from testforge.core.models.report import Report

logger = logging.getLogger("testforge.notification.email")


@dataclass
class EmailConfig:
    smtp_host: str = ""
    smtp_port: int = 587
    user: str = ""
    password: str = ""
    from_addr: str = ""
    to_addr: str = ""

    @staticmethod
    def from_env() -> EmailConfig:
        return EmailConfig(
            smtp_host=os.environ.get("TF_NOTIFY_EMAIL_SMTP_HOST", ""),
            smtp_port=int(os.environ.get("TF_NOTIFY_EMAIL_SMTP_PORT", "587")),
            user=os.environ.get("TF_NOTIFY_EMAIL_USER", ""),
            password=os.environ.get("TF_NOTIFY_EMAIL_PASS", ""),
            from_addr=os.environ.get("TF_NOTIFY_EMAIL_FROM", ""),
            to_addr=os.environ.get("TF_NOTIFY_EMAIL_TO", ""),
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.smtp_host and self.from_addr and self.to_addr)


class EmailNotifier:
    def __init__(self, config: Optional[EmailConfig] = None):
        self.config = config or EmailConfig.from_env()

    def send_report(self, report: Report) -> bool:
        if not self.config.is_configured:
            logger.warning("Notificação não enviada: e-mail não configurado")
            return False

        icon = "✅" if report.status == "passed" else "⚠️" if report.status == "partial" else "❌"
        subject = f"{icon} TestForge - {report.test_name}: {report.status}"

        body = self._build_body(report)

        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = self.config.from_addr
        msg["To"] = self.config.to_addr

        try:
            ctx = ssl.create_default_context()
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port, timeout=10) as server:
                server.starttls(context=ctx)
                if self.config.user:
                    server.login(self.config.user, self.config.password)
                server.send_message(msg)
            logger.info("E-mail enviado para %s", self.config.to_addr)
            return True
        except Exception as e:
            logger.warning("Notificação não enviada: erro de e-mail: %s", e)
            return False

    @staticmethod
    def _build_body(report: Report) -> str:
        icon = "✅" if report.status == "passed" else "⚠️" if report.status == "partial" else "❌"
        lines = [
            f"TestForge - Resultado da Execução",
            f"{'=' * 50}",
            f"",
            f"Teste:   {report.test_name}",
            f"Data:    {report.started_at}",
            f"Status:  {icon} {report.status.upper()}",
            f"Duração: {report.duration_ms}ms",
            f"Modo:    {report.mode}",
            f"",
            f"📊 {report.summary.executive}",
            f"",
            f"Passos:",
        ]
        for i, step in enumerate(report.steps):
            icon_s = "✅" if step.status == "passed" else "❌" if step.status == "failed" else "⏭️"
            name = step.intention or step.name
            lines.append(f"  {icon_s} [{i+1}] {name}: {step.status} ({step.duration_ms}ms)")
            if step.error_message:
                lines.append(f"       ⚠️  {step.error_message}")
            if step.screenshot_path:
                lines.append(f"       \U0001f4f8 Screenshot: {step.screenshot_path}")

        if report.report_dir:
            lines.extend(["", f"Artefatos: {report.report_dir}"])
        if report.trace_path:
            lines.extend(["", f"Trace: {report.trace_path}"])

        return "\n".join(lines)
