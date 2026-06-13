from __future__ import annotations

import logging
from typing import Optional

from testforge.core.models.report import Report
from testforge.core.notification.email import EmailNotifier, EmailConfig
from testforge.core.notification.teams import TeamsNotifier, TeamsConfig

logger = logging.getLogger("testforge.notification")


def notify_all(
    report: Report,
    email_config: Optional[EmailConfig] = None,
    teams_config: Optional[TeamsConfig] = None,
) -> dict[str, bool]:
    results: dict[str, bool] = {}

    email = EmailNotifier(config=email_config)
    results["email"] = email.send_report(report)

    teams = TeamsNotifier(config=teams_config)
    results["teams"] = teams.send_report(report)

    return results
