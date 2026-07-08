from __future__ import annotations

from typing import ClassVar


class TestForgeError(Exception):
    code: ClassVar[str] = "UNKNOWN"
    exit_code: ClassVar[int] = 1
    user_message: ClassVar[str] = "Ocorreu um erro inesperado."

    def __init__(self, message: str = "", recoverable: bool = False):
        self.message = message or self.user_message
        self.recoverable = recoverable
        super().__init__(self.message)


class RetryableError(TestForgeError):
    exit_code = 1


class WebSocketDisconnectedError(RetryableError):
    code = "WS_DISCONNECTED"
    user_message = "Conexão instável. Tentando reconectar..."


class CurationRetryableError(RetryableError):
    code = "CURATION_RETRY"
    user_message = "Curadoria interrompida. Tentando novamente..."


class LLMUnavailableError(RetryableError):
    code = "LLM_UNAVAILABLE"
    user_message = "LLM indisponível no momento. Tentando novamente..."


class FatalError(TestForgeError):
    exit_code = 2


class BrowserError(FatalError):
    code = "BROWSER_ERROR"
    user_message = "Não foi possível abrir o navegador. Verifique se está instalado."


class ConfigError(FatalError):
    code = "CONFIG_ERROR"
    user_message = "Configuração inválida. Verifique os parâmetros."


class GitMergeConflictError(FatalError):
    code = "GIT_MERGE_CONFLICT"
    user_message = "Conflito de merge detectado. Diff salvo localmente."


class RecordingTimeoutError(FatalError):
    code = "RECORDING_TIMEOUT"
    user_message = "Gravação atingiu o tempo máximo. Script parcial gerado."


class WarningError(TestForgeError):
    exit_code = 0


class AssertMismatchWarning(WarningError):
    code = "ASSERT_MISMATCH"
    user_message = "Assert não correspondeu ao valor esperado."


class CurationSkippedWarning(WarningError):
    code = "CURATION_SKIPPED"
    user_message = "Curadoria automática indisponível. Teste original preservado."
