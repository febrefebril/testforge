from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Iterable


@dataclass
class SensitiveDataAlert:
    enabled: bool = True
    masking_applied: bool = False
    possible_sensitive_data_detected: bool = False
    detected_categories: list[str] | None = None
    policy: str = "alert_only"


class SensitiveDataAlertOnlyDetector:
    """Detector simples para alertar possível presença de dados sensíveis.

    Importante:
    - Não mascara.
    - Não remove.
    - Não altera evidências.
    - Apenas retorna metadados de alerta para o Evidence Package.
    """

    PATTERNS = {
        "cpf_pattern": re.compile(r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)"),
        "cnpj_pattern": re.compile(r"(?<!\d)\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}(?!\d)"),
        "long_numeric_identifier": re.compile(r"(?<!\d)\d{8,}(?!\d)"),
    }

    def scan_texts(self, texts: Iterable[str]) -> dict:
        categories = set()
        for text in texts:
            if not text:
                continue
            for category, pattern in self.PATTERNS.items():
                if pattern.search(text):
                    categories.add(category)

        alert = SensitiveDataAlert(
            possible_sensitive_data_detected=bool(categories),
            detected_categories=sorted(categories),
        )
        return asdict(alert)
