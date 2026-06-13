"""TestForge — Healing Recipe + Catalog.

Sistema de aprendizado: quando um bug e encontrado e corrigido,
a receita e armazenada para aplicacao automatica futura.
"""
import json
import os
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class HealingRecipe:
    recipe_id: str = ""
    trigger_family: str = ""           # locator_resolution, actionability, etc
    trigger_code: str = ""             # LOCATOR_NOT_FOUND, etc
    trigger_pattern: str = ""          # regex ou substring do erro
    trigger_framework: str = ""        # angular, react, primefaces, generic
    solution_strategy: str = ""        # fallback_candidates, wait_retry, js_setter
    solution_selector: str = ""        # seletor alternativo
    solution_js: str = ""              # codigo JS para injetar
    priority: int = 0
    usage_count: int = 0
    success_count: int = 0
    last_used: str = ""
    status: str = "active"             # active, stale, deprecated
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "recipe_id": self.recipe_id,
            "trigger_family": self.trigger_family,
            "trigger_code": self.trigger_code,
            "trigger_pattern": self.trigger_pattern,
            "trigger_framework": self.trigger_framework,
            "solution_strategy": self.solution_strategy,
            "solution_selector": self.solution_selector,
            "solution_js": self.solution_js,
            "priority": self.priority,
            "usage_count": self.usage_count,
            "success_count": self.success_count,
            "last_used": self.last_used,
            "status": self.status,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "HealingRecipe":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class HealingCatalog:
    """Catalogo JSONL de receitas de healing."""

    def __init__(self, catalog_path: str = ".planning/healing-catalog.jsonl"):
        self._path = catalog_path

    def add_recipe(self, recipe: HealingRecipe) -> str:
        if not recipe.recipe_id:
            recipe.recipe_id = hashlib.sha256(
                f"{recipe.trigger_code}:{recipe.trigger_pattern}:{recipe.solution_strategy}".encode()
            ).hexdigest()[:12]
        with open(self._path, "a") as f:
            f.write(json.dumps(recipe.to_dict(), default=str) + "\n")
        return recipe.recipe_id

    def match_recipes(self, error_message: str, framework: str = "",
                      family: str = "", max_results: int = 5) -> list[HealingRecipe]:
        """Busca receitas que casam com o erro."""
        if not os.path.exists(self._path):
            return []
        matches = []
        with open(self._path) as f:
            for line in f:
                r = HealingRecipe.from_dict(json.loads(line))
                if r.status != "active":
                    continue
                score = 0
                if r.trigger_pattern and r.trigger_pattern.lower() in error_message.lower():
                    score += 3
                if r.trigger_code and r.trigger_code.lower() in error_message.lower():
                    score += 2
                if r.trigger_framework and r.trigger_framework == framework:
                    score += 2
                if r.trigger_family and r.trigger_family == family:
                    score += 1
                if score > 0:
                    r.priority = score
                    matches.append(r)
        matches.sort(key=lambda r: r.priority, reverse=True)
        return matches[:max_results]

    def record_success(self, recipe_id: str):
        self._update(recipe_id, success=True)

    def record_usage(self, recipe_id: str):
        self._update(recipe_id)

    def _update(self, recipe_id: str, success: bool = False):
        if not os.path.exists(self._path):
            return
        updated = []
        with open(self._path) as f:
            for line in f:
                r = json.loads(line)
                if r.get("recipe_id") == recipe_id:
                    r["usage_count"] = r.get("usage_count", 0) + 1
                    if success:
                        r["success_count"] = r.get("success_count", 0) + 1
                    r["last_used"] = datetime.now(timezone.utc).isoformat()
                updated.append(r)
        with open(self._path, "w") as f:
            for r in updated:
                f.write(json.dumps(r, default=str) + "\n")

    def seed_defaults(self):
        """Pre-popula catalogo com receitas conhecidas."""
        defaults = [
            HealingRecipe(
                trigger_family="locator_resolution",
                trigger_code="LOCATOR_NOT_FOUND",
                trigger_pattern="locator resolved to",
                trigger_framework="angular",
                solution_strategy="fallback_text",
                solution_selector="text={}",
                priority=10,
            ),
            HealingRecipe(
                trigger_family="actionability",
                trigger_code="ACTIONABILITY_OBSCURED",
                trigger_pattern="intercept",
                trigger_framework="generic",
                solution_strategy="force_click",
                solution_js="el.click()",
                priority=5,
            ),
            HealingRecipe(
                trigger_family="locator_resolution",
                trigger_code="ID_NOT_FOUND",
                trigger_pattern="not found",
                trigger_framework="angular",
                solution_strategy="fallback_aria",
                solution_selector="[aria-label='{}']",
                priority=8,
            ),
            HealingRecipe(
                trigger_family="synchronization",
                trigger_code="TIMEOUT",
                trigger_pattern="timeout",
                trigger_framework="angular",
                solution_strategy="wait_stable",
                solution_js="await page.waitForLoadState('networkidle')",
                priority=3,
            ),
        ]
        for d in defaults:
            self.add_recipe(d)
        return len(defaults)
