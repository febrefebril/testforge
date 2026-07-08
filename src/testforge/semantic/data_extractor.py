"""TestForge — Extrator de Dados de Teste.

Extrai valores de preenchimento de raw_events.jsonl de gravação em fixtures JSON externas.
Gera test_data.json com campos nomeados, detecção de dados sensíveis, e suporte multi-cenário.
"""
import json
import os
import re
from typing import Optional


# Sensitive field patterns (label or placeholder matches)
SENSITIVE_PATTERNS = [
    r"(?i)cpf",
    r"(?i)senha|password",
    r"(?i)cartao|card|credit",
    r"(?i)email|e-mail",
    r"(?i)telefone|phone|celular",
    r"(?i)cep",
    r"(?i)rg|identidade",
    r"(?i)conta|agencia",
    r"(?i)token|chave|key",
]


def _is_sensitive(name: str) -> bool:
    """Verifica se um nome de campo corresponde a padrões de dados sensíveis."""
    for pattern in SENSITIVE_PATTERNS:
        if re.search(pattern, name):
            return True
    return False


def _best_field_name(event: dict, idx: int) -> str:
    """Gera melhor nome de campo a partir de atributos de alvo do evento.

    Prioridade: label > placeholder > element_id > generico 'field_N'.
    """
    target = event.get("target", {}) or {}

    label = (target.get("label") or "").strip()
    if label and len(label) <= 40:
        # Sanitize: lowercase, replace spaces/accents with underscore
        name = re.sub(r"[^a-zA-Z0-9_]", "_", label.lower())
        name = re.sub(r"_+", "_", name).strip("_")
        if name:
            return name

    placeholder = (target.get("placeholder") or "").strip()
    if placeholder and len(placeholder) <= 40:
        name = re.sub(r"[^a-zA-Z0-9_]", "_", placeholder.lower())
        name = re.sub(r"_+", "_", name).strip("_")
        if name:
            return name

    element_id = (target.get("element_id") or "").strip()
    if element_id and len(element_id) <= 40:
        name = re.sub(r"[^a-zA-Z0-9_]", "_", element_id.lower())
        name = re.sub(r"_+", "_", name).strip("_")
        if name:
            return name

    return f"field_{idx}"


def extract_test_data(recording_dir: str, scenarios: bool = False) -> dict:
    """Extrai valores de preenchimento da gravacao em dados de teste estruturados.

    Argumentos:
        recording_dir: Caminho para diretorio de gravacao (contem raw_events.jsonl).
        scenarios: Se True, envolve dados em {"default": {...}} para suporte multi-cenario.

    Retorna:
        Dict com chaves "fields" e "sensitive_alerts".
    """
    jsonl_path = os.path.join(recording_dir, "raw_events.jsonl")
    if not os.path.exists(jsonl_path):
        return {"fields": {}, "sensitive_alerts": []}

    fields = {}
    sensitive_alerts = []
    fill_idx = 0

    with open(jsonl_path) as f:
        for line in f:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            if event.get("type") != "fill":
                continue

            fill_idx += 1
            value = event.get("value") or ""
            name = _best_field_name(event, fill_idx)

            # Deduplicate: skip if same value already exists for this name
            if name in fields and fields[name] == value:
                continue

            # Ensure unique field names for different values
            base_name = name
            counter = 1
            while name in fields and fields[name] != value:
                name = f"{base_name}_{counter}"
                counter += 1

            fields[name] = value

            # Check for sensitive data
            if _is_sensitive(name):
                sensitive_alerts.append({
                    "field": name,
                    "reason": "Matches sensitive data pattern (CPF, password, etc.)",
                    "policy": "alert_only",
                    "masking_applied": False,
                })

    result = {
        "fields": fields,
        "sensitive_alerts": sensitive_alerts,
    }

    if scenarios:
        result = {
            "scenarios": {
                "default": fields,
            },
            "sensitive_alerts": sensitive_alerts,
        }

    return result


def generate_test_data_file(
    recording_dir: str,
    output_path: Optional[str] = None,
    scenarios: bool = False,
) -> str:
    """Gera test_data.json a partir da gravacao.

    Argumentos:
        recording_dir: Caminho para diretorio de gravacao.
        output_path: Caminho do arquivo de saida. Padrao: recording_dir/test_data.json.
        scenarios: Se True, gera formato multi-cenario.

    Retorna:
        Caminho para arquivo gerado.
    """
    data = extract_test_data(recording_dir, scenarios=scenarios)

    if output_path is None:
        output_path = os.path.join(recording_dir, "test_data.json")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Exibe alertas de dados sensiveis
    for alert in data.get("sensitive_alerts", []):
        print(f"  [AVISO] Sensivel: {alert['field']} — {alert['reason']}")

    return output_path


def add_scenario(data: dict, scenario_name: str, fields: dict) -> dict:
    """Adiciona novo cenario a dados de teste existentes."""
    if "scenarios" not in data:
        data["scenarios"] = {"default": data.get("fields", {})}
        if "fields" in data:
            del data["fields"]
    data["scenarios"][scenario_name] = fields
    return data
