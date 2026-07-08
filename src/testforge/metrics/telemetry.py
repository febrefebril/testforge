"""Fase 6: tracer sem dependencias compativel com formato de atributos OpenTelemetry.

Escreve spans como JSONL em `.testforge/spans.jsonl`. Cada span carrega
campos compativeis com OTel (name, trace_id, span_id, parent_span_id, start
+ end + duration, attributes dict). Quando um exportador OTel real for
desejado depois, um unico adaptador pode reproduzir este stream JSONL.

Usado por:
- runtime.resolver.LocatorResolver  -> span name "resolve"
- runtime.step.*                    -> span name "step.<action>"

Tracer e local ao processo. `get_tracer()` retorna o singleton; testes
podem chamar `reset_tracer()` entre casos.
"""
from __future__ import annotations

import json
import logging
import os
import secrets
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from threading import Lock
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_SPANS_PATH = ".testforge/spans.jsonl"


def _new_trace_id() -> str:
    return secrets.token_hex(16)


def _new_span_id() -> str:
    return secrets.token_hex(8)


class Span:
    """Um span aberto. Mutavel ate `end()`."""

    __slots__ = (
        "name", "trace_id", "span_id", "parent_span_id",
        "start_time", "_start_perf", "attributes",
        "status", "end_time", "duration_ms", "_tracer",
    )

    def __init__(
        self,
        name: str,
        trace_id: str,
        span_id: str,
        parent_span_id: Optional[str],
        tracer: "Tracer",
    ) -> None:
        self.name = name
        self.trace_id = trace_id
        self.span_id = span_id
        self.parent_span_id = parent_span_id
        self.start_time = datetime.now(timezone.utc).isoformat()
        self._start_perf = time.perf_counter()
        self.attributes: dict[str, object] = {}
        self.status = "ok"
        self.end_time: Optional[str] = None
        self.duration_ms: float = 0.0
        self._tracer = tracer

    def set_attribute(self, key: str, value) -> None:
        self.attributes[key] = value

    def set_status(self, status: str) -> None:
        self.status = status

    def end(self) -> None:
        self.duration_ms = (time.perf_counter() - self._start_perf) * 1000
        self.end_time = datetime.now(timezone.utc).isoformat()
        self._tracer._write(self.to_dict())

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": round(self.duration_ms, 3),
            "status": self.status,
            "attributes": self.attributes,
        }


class Tracer:
    """Escritor de spans JSONL local ao processo."""

    def __init__(self, spans_path: str = DEFAULT_SPANS_PATH,
                 enabled: bool = True) -> None:
        self._spans_path = spans_path
        self._enabled = enabled
        self._lock = Lock()
        self._stack: list[Span] = []
        if enabled:
            os.makedirs(os.path.dirname(spans_path) or ".", exist_ok=True)

    @contextmanager
    def start_span(self, name: str):
        if not self._enabled:
            yield _NoopSpan()
            return
        parent = self._stack[-1] if self._stack else None
        trace_id = parent.trace_id if parent else _new_trace_id()
        span = Span(
            name=name, trace_id=trace_id, span_id=_new_span_id(),
            parent_span_id=parent.span_id if parent else None,
            tracer=self,
        )
        self._stack.append(span)
        try:
            yield span
        except Exception as exc:
            span.set_status("error")
            span.set_attribute("error.message", str(exc)[:200])
            raise
        finally:
            self._stack.pop()
            span.end()

    def _write(self, payload: dict) -> None:
        if not self._enabled:
            return
        line = json.dumps(payload, ensure_ascii=False, default=str)
        with self._lock:
            with open(self._spans_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")

    @property
    def spans_path(self) -> str:
        return self._spans_path

    @property
    def enabled(self) -> bool:
        return self._enabled

    def disable(self) -> None:
        self._enabled = False


class _NoopSpan:
    def set_attribute(self, *_a, **_k): pass
    def set_status(self, *_a): pass


_tracer: Optional[Tracer] = None
_tracer_lock = Lock()


def get_tracer(spans_path: str = DEFAULT_SPANS_PATH) -> Tracer:
    global _tracer
    with _tracer_lock:
        if _tracer is None:
            enabled = os.environ.get("TESTFORGE_TRACING", "1") != "0"
            _tracer = Tracer(spans_path=spans_path, enabled=enabled)
        return _tracer


def reset_tracer() -> None:
    """Limpa o singleton (apenas testes)."""
    global _tracer
    with _tracer_lock:
        _tracer = None
