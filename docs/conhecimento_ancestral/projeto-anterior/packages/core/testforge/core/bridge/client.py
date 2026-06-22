from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class BridgeClient:
    def __init__(self, host: str = "localhost", port: int = 9199):
        self.host = host
        self.port = port
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._connected = False
        self._handlers: dict[str, list[Callable]] = {}

    async def connect(self) -> bool:
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=5.0,
            )
            self._connected = True
            logger.info(f"Bridge conectado em {self.host}:{self.port}")
            return True
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
            logger.warning(f"Bridge não disponível ({e}). Modo offline.")
            self._connected = False
            return False

    async def send(self, msg_type: str, payload: dict[str, Any] | None = None) -> None:
        if not self._connected or not self._writer:
            return
        msg = {
            "type": msg_type,
            "id": f"msg_{id(self)}",
            "timestamp": "",
            "payload": payload or {},
        }
        data = json.dumps(msg) + "\n"
        try:
            self._writer.write(data.encode())
            await self._writer.drain()
        except Exception as e:
            logger.warning(f"Erro ao enviar mensagem para bridge: {e}")
            self._connected = False

    def on(self, msg_type: str, handler: Callable) -> None:
        if msg_type not in self._handlers:
            self._handlers[msg_type] = []
        self._handlers[msg_type].append(handler)

    async def close(self) -> None:
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
        self._connected = False
