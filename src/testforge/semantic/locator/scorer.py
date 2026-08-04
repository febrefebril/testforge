
"""Phase 2: Per-attribute stability scoring.

Este módulo centraliza as regras de estabilidade dos atributos usados
para gerar candidatos de locator no TestForge.

Objetivo:
- Manter o compiler simples.
- Fazer o LocatorExtractor ranquear melhor os candidatos.
- Priorizar locators acessíveis e estáveis, conforme boas práticas do Playwright:
  - get_by_test_id
  - get_by_role(..., name=...)
  - get_by_label
  - get_by_placeholder
  - locators semânticos
- Penalizar locators frágeis:
  - role sem nome
  - texto genérico isolado
  - id dinâmico
  - CSS estrutural
  - nth-child
  - XPath

Observação:
Este scorer mede estabilidade do atributo/candidato.
Ele não garante unicidade do elemento em runtime. A unicidade deve ser validada
pelo resolver/healer ou por metadados de captura quando disponíveis.
"""

from __future__ import annotations

import re
from typing import Any


# IDs gerados por frameworks/bibliotecas que tendem a mudar entre execuções.
_AUTO_ID_PREFIXES = (
    "mat-",
    "mat-input-",
    "mat-mdc-",
    "ng-",
    "ember",
    "react-",
    "css-",
    "jss",
    "mui-",
    "cdk-",
    "radix-",
)

_AUTO_ID_PATTERNS = (
    re.compile(r"^mat-input-\d+$", re.I),
    re.compile(r"^mat-mdc-[a-z-]+-\d+$", re.I),
    re.compile(r"^cdk-[a-z-]+-\d+$", re.I),
    re.compile(r"^ember\d+$", re.I),
    re.compile(r"^react-[a-z0-9_-]+$", re.I),
    re.compile(r"^css-[a-z0-9_-]+$", re.I),
    re.compile(r"^jss\d+$", re.I),
)


# Textos genéricos são perigosos quando usados isoladamente via get_by_text().
# Eles podem continuar bons quando combinados com role/accessibility name:
# get_by_role("button", name="Entrar") é bom,
# get_by_text("Entrar") sozinho é fraco.
_GENERIC_TEXT = {
    "ok",
    "cancel",
    "cancelar",
    "voltar",
    "salvar",
    "enviar",
    "fechar",
    "selecione",
    "selecionar",
    "buscar",
    "pesquisar",
    "limpar",
    "confirmar",
    "continuar",
    "avançar",
    "avancar",
    "próximo",
    "proximo",
    "anterior",
    "entrar",
    "login",
    "logout",
    "sim",
    "não",
    "nao",
    "aceitar",
    "rejeitar",
    "editar",
    "excluir",
    "adicionar",
    "remover",
    "filtrar",
    "ordenar",
    "atualizar",
    "download",
    "upload",
    "imprimir",
}


# Roles interativos tendem a ser ambíguos quando usados sem nome acessível.
_INTERACTIVE_ROLES = {
    "button",
    "link",
    "textbox",
    "combobox",
    "checkbox",
    "radio",
    "menuitem",
    "tab",
    "option",
    "switch",
    "slider",
    "spinbutton",
}


# Roles estruturais são estáveis, mas normalmente não devem ser usados para ação direta
# sem outro atributo de desambiguação.
_STRUCTURAL_ROLES = {
    "main",
    "navigation",
    "banner",
    "contentinfo",
    "region",
    "form",
    "dialog",
    "alertdialog",
    "table",
    "row",
    "cell",
    "heading",
}


def _as_str(value: Any) -> str:
    """Converte um valor para string limpa."""
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _first_non_empty(*values: Any) -> str:
    """Retorna o primeiro valor não vazio, convertido para string limpa."""
    for value in values:
        cleaned = _as_str(value)
        if cleaned:
            return cleaned
    return ""


def _as_bool(value: Any) -> bool:
    """Converte valores comuns para boolean."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y", "sim"}
    return bool(value)


def _normalize_role(value: Any) -> str:
    """Normaliza role para comparação."""
    return _as_str(value).lower()


def _is_auto_id(value: str) -> bool:
    """Identifica IDs dinâmicos/gerados por frameworks."""
    value = _as_str(value)
    if not value:
        return False

    lower = value.lower()

    if any(lower.startswith(prefix) for prefix in _AUTO_ID_PREFIXES):
        return True

    return any(pattern.search(value) for pattern in _AUTO_ID_PATTERNS)


def _is_generic_text(value: str) -> bool:
    """Identifica texto genérico ou pouco discriminativo."""
    clean = _as_str(value).lower()

    if not clean:
        return True

    if clean in _GENERIC_TEXT:
        return True

    if len(clean) <= 1:
        return True

    if clean.isdigit():
        return True

    # Textos muito longos tendem a ser frágeis por variação de conteúdo.
    if len(clean) > 60:
        return True

    return False


def _has_data_attribute(target_data: dict) -> bool:
    """Detecta presença de atributos data-* úteis."""
    attrs = target_data.get("attributes") or {}

    if isinstance(attrs, dict):
        for key, value in attrs.items():
            if str(key).lower().startswith("data-") and _as_str(value):
                return True

    for key, value in target_data.items():
        key_lower = str(key).lower()
        if key_lower.startswith("data-") and _as_str(value):
            return True

    return False


def _score_role(role: str, accessible_name: str) -> float:
    """Calcula estabilidade do role considerando se há nome acessível."""
    role = _normalize_role(role)
    accessible_name = _as_str(accessible_name)

    if not role:
        return 0.0

    # Melhor caso: role + nome acessível.
    # Ex.: get_by_role("button", name="Entrar")
    if accessible_name:
        return 0.95

    # Role interativo sem nome é fonte comum de strict mode violation.
    # Ex.: get_by_role("button") quando há Entrar, Voltar e Exibir senha.
    if role in _INTERACTIVE_ROLES:
        if role in {"button", "link"}:
            return 0.25
        if role in {"textbox", "combobox"}:
            return 0.35
        return 0.30

    # Roles estruturais podem ser úteis para escopo, mas não para ação direta.
    if role in _STRUCTURAL_ROLES:
        return 0.50

    # Fallback histórico para role sem nome.
    return 0.45


def _score_text(text: str) -> float:
    """Calcula estabilidade de texto visível isolado."""
    text = _as_str(text)

    if not text:
        return 0.0

    if _is_generic_text(text):
        return 0.10

    if len(text) > 40:
        return 0.35

    return 0.55


def _score_placeholder(placeholder: str) -> float:
    """Calcula estabilidade de placeholder."""
    placeholder = _as_str(placeholder)

    if not placeholder:
        return 0.0

    lower = placeholder.lower()

    # Placeholders de máscara costumam aparecer em vários campos.
    generic_masks = {
        "dd/mm/aaaa",
        "dd/mm/yyyy",
        "00/00/0000",
        "000.000.000-00",
        "00.000.000/0000-00",
        "00000-000",
        "r$0,00",
        "r$ 0,00",
        "0,00",
    }

    if lower in generic_masks:
        return 0.35

    return 0.70


def _score_id(element_id: str, element_id_dynamic: bool = False) -> float:
    """Calcula estabilidade do ID."""
    element_id = _as_str(element_id)

    if not element_id:
        return 0.0

    if element_id_dynamic or _is_auto_id(element_id):
        return 0.10

    return 0.80


def _score_name(name: str) -> float:
    """Calcula estabilidade do atributo name."""
    name = _as_str(name)

    if not name:
        return 0.0

    # Nomes muito genéricos podem aparecer em múltiplos campos.
    if name.lower() in {"input", "field", "value", "search", "query"}:
        return 0.40

    return 0.75


def _score_accessibility(
    *,
    role: str,
    accessible_name: str,
    label: str,
    aria_label: str,
    material_field_label: str,
    form_control_name: str,
) -> float:
    """Score agregado de acessibilidade/semântica.

    Este valor não substitui os atributos individuais.
    Ele ajuda o extractor/runtime a saber se há bons sinais acessíveis.
    """
    scores: list[float] = []

    if role and accessible_name:
        scores.append(0.95)

    if label:
        scores.append(0.92)

    if material_field_label:
        scores.append(0.93)

    if form_control_name:
        scores.append(0.90)

    if accessible_name:
        scores.append(0.90)

    if aria_label:
        scores.append(0.85)

    if not scores:
        return 0.0

    return max(scores)


def attribute_stability(target_data: dict) -> dict[str, float]:
    """Retorna mapa de estabilidade por atributo para um target.

    O retorno é intencionalmente um dict simples para manter compatibilidade
    com o LocatorExtractor e com o modelo LocatorCandidate.attribute_stability.

    Campos esperados em target_data podem vir de fontes diferentes:
    - overlay JS
    - CDP recorder
    - AX tree
    - normalizador legado

    Por isso a função aceita variações de nome:
    - id / element_id
    - aria-label / aria_label
    - test_id / testid / data-testid
    - innerText / inner_text / text
    """

    if not target_data:
        return {}

    role = _first_non_empty(
        target_data.get("role"),
        target_data.get("computed_role"),
    )

    accessible_name = _first_non_empty(
        target_data.get("accessible_name"),
        target_data.get("accessibility_name"),
        target_data.get("computed_name"),
        target_data.get("name_from_ax"),
    )

    label = _first_non_empty(
        target_data.get("label"),
        target_data.get("label_text"),
    )

    aria_label = _first_non_empty(
        target_data.get("aria-label"),
        target_data.get("aria_label"),
    )

    placeholder = _first_non_empty(
        target_data.get("placeholder"),
    )

    test_id = _first_non_empty(
        target_data.get("test_id"),
        target_data.get("testid"),
        target_data.get("data-testid"),
        target_data.get("data_testid"),
        target_data.get("data-cy"),
        target_data.get("data_cy"),
    )

    name = _first_non_empty(
        target_data.get("name"),
    )

    element_id = _first_non_empty(
        target_data.get("id"),
        target_data.get("element_id"),
    )

    text = _first_non_empty(
        target_data.get("text"),
        target_data.get("inner_text"),
        target_data.get("innerText"),
        target_data.get("text_content"),
        target_data.get("textContent"),
    )

    material_field_label = _first_non_empty(
        target_data.get("material_field_label"),
        target_data.get("mat_label"),
        target_data.get("mat-label"),
    )

    form_control_name = _first_non_empty(
        target_data.get("form_control_name"),
        target_data.get("formControlName"),
        target_data.get("formcontrolname"),
    )

    css_path = _first_non_empty(
        target_data.get("css_path"),
        target_data.get("cssPath"),
    )

    nth_child = _first_non_empty(
        target_data.get("nth_child"),
        target_data.get("nthChild"),
    )

    xpath = _first_non_empty(
        target_data.get("xpath"),
    )

    element_id_dynamic = _as_bool(
        target_data.get("element_id_dynamic")
        or target_data.get("id_dynamic")
        or target_data.get("dynamic_id")
    )

    stability: dict[str, float] = {}

    # 1. Atributos intencionais / semânticos fortes
    if test_id:
        stability["test_id"] = 0.95

    if role:
        stability["role"] = _score_role(role, accessible_name)

    if role and accessible_name:
        stability["role_with_accessible_name"] = 0.95

    if accessible_name:
        stability["accessible_name"] = 0.90

    if label:
        stability["label"] = 0.92

    if material_field_label:
        stability["material_field_label"] = 0.93

    if form_control_name:
        stability["form_control_name"] = 0.90

    if aria_label:
        stability["aria_label"] = 0.85

    # 2. Atributos HTML úteis, mas menos fortes que acessibilidade
    if placeholder:
        stability["placeholder"] = _score_placeholder(placeholder)

    if name:
        stability["name"] = _score_name(name)

    if element_id:
        stability["id"] = _score_id(
            element_id,
            element_id_dynamic=element_id_dynamic,
        )

    if _has_data_attribute(target_data):
        stability["data_attr"] = 0.70

    # 3. Texto visível: útil, porém menos estável e frequentemente ambíguo
    if text:
        stability["text"] = _score_text(text)

    # 4. Estratégias frágeis / último recurso
    if css_path:
        stability["css_path"] = 0.40

    if nth_child:
        stability["nth_child"] = 0.25

    if xpath:
        stability["xpath"] = 0.15

    # 5. Score agregado de acessibilidade
    accessibility_score = _score_accessibility(
        role=role,
        accessible_name=accessible_name,
        label=label,
        aria_label=aria_label,
        material_field_label=material_field_label,
        form_control_name=form_control_name,
    )

    if accessibility_score:
        stability["accessibility_score"] = accessibility_score

    return stability

