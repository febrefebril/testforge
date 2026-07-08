from __future__ import annotations

from testforge.core.models.step import RecordedStep


class StepBuilder:
    def build(
        self,
        action: str,
        selector: str,
        tag_name: str = "",
        value: str = "",
        text: str = "",
        url: str = "",
        page_title: str = "",
        page_technology: str = "",
        dom_snapshot: str = "",
        fallbacks: list[str] | None = None,
    ) -> RecordedStep:
        import uuid
        from datetime import datetime, timezone

        return RecordedStep(
            step_id=f"step_{uuid.uuid4().hex[:12]}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=action,
            selector_used=selector,
            fallbacks=fallbacks or [],
            tag_name=tag_name,
            text=text,
            value=value,
            url=url,
            page_title=page_title,
            page_technology=page_technology,
            dom_snapshot=dom_snapshot,
        )
