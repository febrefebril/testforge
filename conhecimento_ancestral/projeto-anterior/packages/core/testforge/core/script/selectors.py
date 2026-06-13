from __future__ import annotations

_NO_TEXT_TAGS = frozenset({"input", "select", "textarea", "img", "br", "hr", "wbr"})


class SelectorStrategy:
    def __init__(self, css: str, strategy: str, fallback_index: int = 0):
        self.css = css
        self.strategy = strategy
        self.fallback_index = fallback_index

    def __repr__(self) -> str:
        return f'("{self.css}", "{self.strategy}")'


def _tag_can_have_text(tag: str) -> bool:
    return tag not in _NO_TEXT_TAGS


def generate_strategies(
    selector: str,
    tag_name: str,
    text: str = "",
    value: str = "",
    attrs: dict | None = None,
) -> list[SelectorStrategy]:
    strategies: list[SelectorStrategy] = []
    tag = tag_name.lower() if tag_name else ""
    a = attrs or {}

    data_testid = a.get("dataTestid", "") or ""
    if not data_testid and selector and selector.startswith("[data-testid"):
        data_testid_val = selector.split("=", 1)[1].strip('"]')
        data_testid = data_testid_val

    if data_testid:
        strategies.append(SelectorStrategy(
            css=f'[data-testid="{data_testid}"]',
            strategy="data-testid",
            fallback_index=0,
        ))

    element_id = a.get("id", "") or ""
    if not element_id and selector and selector.startswith("#"):
        element_id = selector.lstrip("#")

    if element_id:
        strategies.append(SelectorStrategy(
            css=f"#{element_id}",
            strategy="id",
            fallback_index=len(strategies),
        ))

    name_attr = a.get("name", "") or ""
    if name_attr:
        strategies.append(SelectorStrategy(
            css=f'{tag}[name="{name_attr}"]' if tag else f'[name="{name_attr}"]',
            strategy="name",
            fallback_index=len(strategies),
        ))

    aria_label = a.get("ariaLabel", "") or ""
    if aria_label:
        strategies.append(SelectorStrategy(
            css=f'{tag}[aria-label="{aria_label}"]' if tag else f'[aria-label="{aria_label}"]',
            strategy="aria-label",
            fallback_index=len(strategies),
        ))

    placeholder = a.get("placeholder", "") or ""
    if placeholder:
        strategies.append(SelectorStrategy(
            css=f'{tag}[placeholder="{placeholder}"]' if tag else f'[placeholder="{placeholder}"]',
            strategy="placeholder",
            fallback_index=len(strategies),
        ))

    label_text = a.get("labelText", "") or ""
    if label_text:
        safe = label_text.replace('"', '\\"').strip()
        if tag and _tag_can_have_text(tag):
            strategies.append(SelectorStrategy(
                css=f'{tag}:has-text("{safe}")',
                strategy="label-text",
                fallback_index=len(strategies),
            ))
        else:
            for prefix in ("label", "span", "div"):
                strategies.append(SelectorStrategy(
                    css=f'{prefix}:has-text("{safe}")',
                    strategy=f"label-text-{prefix}",
                    fallback_index=len(strategies),
                ))

    role_attr = a.get("role", "") or ""
    if role_attr and text:
        safe_text = text.replace('"', '\\"').strip()
        css_val = f'[role="{role_attr}"]:has-text("{safe_text}")'
        if tag and _tag_can_have_text(tag):
            css_val = f'{tag}[role="{role_attr}"]:has-text("{safe_text}")'
        strategies.append(SelectorStrategy(
            css=css_val,
            strategy="role+text",
            fallback_index=len(strategies),
        ))

    if text and tag and _tag_can_have_text(tag):
        safe_text = text.replace('"', '\\"').strip()
        strategies.append(SelectorStrategy(
            css=f'{tag}:has-text("{safe_text}")',
            strategy="text-contains",
            fallback_index=len(strategies),
        ))

    href = a.get("href", "") or ""
    if href and tag == "a" and href not in ("#", "", "javascript:void(0)"):
        strategies.append(SelectorStrategy(
            css=f'a[href="{href}"]',
            strategy="href",
            fallback_index=len(strategies),
        ))

    alt_text = a.get("alt", "") or ""
    if alt_text and tag == "img":
        strategies.append(SelectorStrategy(
            css=f'img[alt="{alt_text}"]',
            strategy="alt",
            fallback_index=len(strategies),
        ))

    classes = a.get("classes", "") or ""
    if classes and tag:
        cls = ".".join(c for c in classes.split() if c and not c.startswith("tf-"))
        if cls:
            strategies.append(SelectorStrategy(
                css=f"{tag}.{cls}",
                strategy="class",
                fallback_index=len(strategies),
            ))

    if not strategies and selector:
        strategies.append(SelectorStrategy(
            css=selector,
            strategy="captured",
            fallback_index=0,
        ))

    return strategies


def format_fallback_comment(strategies: list[SelectorStrategy]) -> str:
    parts = []
    for s in strategies:
        parts.append(f"  fallback {s.fallback_index}: {s.strategy} -> {s.css}")
    return "\n".join(parts)
