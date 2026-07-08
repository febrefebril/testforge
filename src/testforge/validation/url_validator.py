"""Validação de URL — avisa sobre e comerciais sem aspas e URLs truncadas.

Problema: shell interpreta & como operador de background. Usuário executa:
  tf record http://example.com/page?arg=1&other=2
Shell divide em &, CLI recebe apenas http://example.com/page?arg=1

Este validador detecta os sintomas comuns de uma URL sem aspas.
"""

from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs
import re


@dataclass
class UrlWarning:
    """Aviso de validacao para URL que pode estar malformada devido ao processamento do shell."""

    message: str
    is_critical: bool = False
    url: str = ""


class UrlValidator:
    """Valida URLs para problemas comuns de truncagem de shell."""

    # URL deve corresponder a isto para ser considerada uma URL http/https valida
    _URL_RE = re.compile(r"^https?://", re.IGNORECASE)

    def validate(self, url: str) -> list[UrlWarning]:
        """Valida uma URL e retorna lista de avisos.

        Args:
            url: String de URL para validar.

        Returns:
            Lista de objetos UrlWarning. Lista vazia significa sem avisos.
        """
        warnings: list[UrlWarning] = []

        if not url or not url.strip():
            warnings.append(UrlWarning("URL vazia", is_critical=True, url=url))
            return warnings

        url = url.strip()

        # Detecta E comercial direto na URL — quase certamente input shell sem aspas.
        # O shell ja teria removido tudo apos & entao isso so
        # dispara quando o E comercial aparece no fragmento restante.
        if "&" in url:
            warnings.append(
                UrlWarning(
                    "URL contem caractere '&'. "
                    "Se usar shell, envolva URL em aspas para evitar truncagem "
                    "no E comercial (operador de background do shell). "
                    f"URL atual pode estar incompleta ou truncada: {url}",
                    is_critical=True,
                    url=url,
                )
            )

        # Detecta URLs truncadas — sintomas de divisao por E comercial do shell.
        truncation_warnings = self._detect_truncation(url)
        warnings.extend(truncation_warnings)

        # Validate URL scheme.
        if not self._URL_RE.match(url):
            warnings.append(
                UrlWarning(
                    f"URL nao comeca com http:// ou https://: {url}",
                    is_critical=False,
                    url=url,
                )
            )

        return warnings

    def _detect_truncation(self, url: str) -> list[UrlWarning]:
        """Detecta sintomas de URL truncada por processamento de E comercial do shell."""
        warnings: list[UrlWarning] = []

        try:
            parsed = urlparse(url)
        except Exception:
            return warnings

        # Sintoma 1: query string termina com = (nome de parametro sem valor).
        if parsed.query and parsed.query.endswith("="):
            warnings.append(
                UrlWarning(
                    "Query string da URL termina com '=' — possivel truncagem. "
                    "O shell removeu tudo apos um '&' sem aspas? "
                    f"Query: ?{parsed.query}",
                    is_critical=True,
                    url=url,
                )
            )

        # Sintoma 2: query string tem nomes de parametro sem valores.
        if parsed.query:
            params = parse_qs(parsed.query, keep_blank_values=True)
            for name, values in params.items():
                if not values or all(v == "" for v in values):
                    warnings.append(
                        UrlWarning(
                            f"Parametro de query '{name}' sem valor — "
                            "possivel truncagem apos divisao por E comercial do shell.",
                            is_critical=True,
                            url=url,
                        )
                    )

        # Sintoma 3: URL termina com ? (query string comecou mas foi truncada).
        if url.rstrip().endswith("?"):
            warnings.append(
                UrlWarning(
                    "URL termina com '?' — query string parece truncada. "
                    "Envolva URL em aspas ao usar shell.",
                    is_critical=True,
                    url=url,
                )
            )

        # Sintoma 4: URL termina com = (atribuicao de parametro truncada).
        if url.rstrip().endswith("="):
            warnings.append(
                UrlWarning(
                    "URL termina com '=' — valor de parametro parece truncado. "
                    "Envolva URL em aspas ao usar shell.",
                    is_critical=True,
                    url=url,
                )
            )

        return warnings

    def is_valid(self, url: str) -> bool:
        """Verifica se URL passa na validacao sem avisos criticos."""
        warnings = self.validate(url)
        return not any(w.is_critical for w in warnings)


def validate_url(url: str) -> list[UrlWarning]:
    """Funcao de conveniencia para validar uma URL e retornar avisos.

    Args:
        url: String de URL para validar.

    Returns:
        Lista de objetos UrlWarning. Lista vazia significa sem avisos.
    """
    return UrlValidator().validate(url)
