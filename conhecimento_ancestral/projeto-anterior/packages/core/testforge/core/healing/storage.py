from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from testforge.core.healing.models import FAMILIES, TAXONOMIES, HealingEntry, HealingRecipe, migrate_family, migrate_taxonomy

DEFAULT_DB_PATH = "./healing-catalog.jsonl"
FAILURE_COUNTS_FILE_SUFFIX = ".meta.json"


def _load_json_safe(line: str) -> Optional[dict]:
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None


class HealingCatalog:
    def __init__(self, path: str = DEFAULT_DB_PATH) -> None:
        self._path = Path(path)
        self._failure_counts: dict[str, int] = {}
        self._load_failure_counts()

    def _meta_path(self) -> Path:
        return self._path.parent / (self._path.name + FAILURE_COUNTS_FILE_SUFFIX)

    def _load_failure_counts(self) -> None:
        meta = self._meta_path()
        if meta.exists():
            try:
                data = json.loads(meta.read_text(encoding="utf-8"))
                self._failure_counts = data.get("failure_counts", {})
            except (json.JSONDecodeError, OSError):
                self._failure_counts = {}

    def _save_failure_counts(self) -> None:
        meta = self._meta_path()
        try:
            meta.parent.mkdir(parents=True, exist_ok=True)
            meta.write_text(
                json.dumps({"failure_counts": self._failure_counts}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass

    def get_failure_count(self, taxonomy_id: str) -> int:
        return self._failure_counts.get(taxonomy_id, 0)

    def increment_failure_count(self, taxonomy_id: str) -> int:
        current = self._failure_counts.get(taxonomy_id, 0)
        self._failure_counts[taxonomy_id] = current + 1
        self._save_failure_counts()
        return self._failure_counts[taxonomy_id]

    def reset_failure_count(self, taxonomy_id: str) -> None:
        if taxonomy_id in self._failure_counts:
            del self._failure_counts[taxonomy_id]
            self._save_failure_counts()

    def add(self, entry: HealingEntry) -> str:
        entry.family = migrate_family(entry.family)
        entry.taxonomy = migrate_taxonomy(entry.taxonomy)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(entry.to_dict(), ensure_ascii=False)
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        return entry.id

    def _iter_entries(self):
        if not self._path.exists():
            return
        with open(self._path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = _load_json_safe(line)
                if data is None:
                    continue
                yield HealingEntry.from_dict(data)

    def list(
        self,
        system: Optional[str] = None,
        family: Optional[str] = None,
        taxonomy: Optional[str] = None,
        fix_type: Optional[str] = None,
        limit: int = 50,
    ) -> list[HealingEntry]:
        results: list[HealingEntry] = []
        for entry in self._iter_entries():
            if system and system.lower() != entry.system.lower():
                continue
            if family and entry.family != family:
                continue
            if taxonomy and entry.taxonomy != taxonomy:
                continue
            if fix_type and entry.fix_type != fix_type:
                continue
            results.append(entry)
            if len(results) >= limit:
                break
        return results

    def get(self, entry_id: str) -> Optional[HealingEntry]:
        for entry in self._iter_entries():
            if entry.id == entry_id:
                return entry
        return None

    def delete(self, entry_id: str) -> bool:
        if not self._path.exists():
            return False
        lines = self._path.read_text(encoding="utf-8").splitlines()
        new_lines: list[str] = []
        found = False
        for line in lines:
            if not line.strip():
                continue
            data = _load_json_safe(line)
            if data is None:
                new_lines.append(line)
                continue
            if data.get("id") == entry_id:
                found = True
            else:
                new_lines.append(line)
        if not found:
            return False
        self._path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        return True

    def update(self, entry_id: str, **kwargs) -> bool:
        if not self._path.exists():
            return False
        lines = self._path.read_text(encoding="utf-8").splitlines()
        found = False
        new_lines: list[str] = []
        for line in lines:
            if not line.strip():
                continue
            data = _load_json_safe(line)
            if data is None:
                new_lines.append(line)
                continue
            if data.get("id") == entry_id:
                data.update(kwargs)
                found = True
            new_lines.append(json.dumps(data, ensure_ascii=False))
        if not found:
            return False
        self._path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        return True

    def match(self, family: str, symptom: str) -> Optional[HealingEntry]:
        if not symptom:
            return None
        symptom_lower = symptom.lower().strip()
        for entry in self._iter_entries():
            if entry.family != family:
                continue
            entry_symptom = entry.symptom.lower().strip()
            if entry_symptom == symptom_lower or symptom_lower in entry_symptom:
                return entry
        return None

    def _backup(self) -> None:
        if not self._path.exists():
            return
        bak_path = self._path.parent / f"{self._path.name}.bak"
        shutil.copy2(str(self._path), str(bak_path))

    def _audit(
        self,
        operation: str,
        entry_ids: list[str],
        details: str = "",
    ) -> None:
        audit_path = self._path.parent / "healing-audit.log"
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": operation,
            "entry_ids": entry_ids,
            "user": os.environ.get("USER", "unknown"),
            "details": details,
        }
        with open(audit_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def find_duplicates(self) -> list[list[HealingEntry]]:
        groups: dict[str, list[HealingEntry]] = {}
        for entry in self._iter_entries():
            sys_norm = entry.system.lower().strip()
            sym_norm = re.sub(r'\s+', ' ', entry.symptom.lower().strip())
            key = f"{sys_norm}|{sym_norm}"
            groups.setdefault(key, []).append(entry)
        return [g for g in groups.values() if len(g) > 1]

    def systems(self) -> list[str]:
        seen: set[str] = set()
        for entry in self._iter_entries():
            if entry.system:
                seen.add(entry.system)
        return sorted(seen)

    # ─── Recipe methods ───────────────────────────────────────────────
    def add_recipe(self, recipe: HealingRecipe) -> str:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps({"__type": "recipe", **recipe.to_dict()}, ensure_ascii=False)
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        return recipe.id

    def _iter_recipes(self):
        if not self._path.exists():
            return
        with open(self._path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = _load_json_safe(line)
                if data is None or data.get("__type") != "recipe":
                    continue
                yield HealingRecipe.from_dict(data)

    def match_recipes(
        self,
        action: str = "",
        framework: str = "",
        symptom: str = "",
        selector: str = "",
        prev_action: str = "",
        min_priority: int = 0,
    ) -> list[HealingRecipe]:
        action_lower = action.lower().strip()
        framework_lower = framework.lower().strip()
        matched: list[HealingRecipe] = []
        for recipe in self._iter_recipes():
            if recipe.priority < min_priority:
                continue
            if action_lower and recipe.trigger_action and recipe.trigger_action != action_lower:
                continue
            if framework_lower and recipe.trigger_framework:
                rfw = recipe.trigger_framework.lower()
                if rfw != 'generic' and rfw != framework_lower:
                    continue
            if symptom:
                sym_lower = symptom.lower()
                r_sym = recipe.trigger_symptom.lower()
                if r_sym and sym_lower not in r_sym and r_sym not in sym_lower:
                    continue
            if selector and recipe.trigger_selector_pattern:
                import re
                try:
                    if not re.search(recipe.trigger_selector_pattern, selector):
                        continue
                except re.error:
                    pass
            if prev_action and recipe.trigger_prev_action:
                if recipe.trigger_prev_action != prev_action:
                    continue
            matched.append(recipe)
        matched.sort(key=lambda r: r.priority, reverse=True)
        return matched

    def update_recipe(self, recipe_id: str, **kwargs) -> bool:
        if not self._path.exists():
            return False
        lines = self._path.read_text(encoding="utf-8").splitlines()
        found = False
        new_lines: list[str] = []
        for line in lines:
            if not line.strip():
                continue
            data = _load_json_safe(line)
            if data is None:
                new_lines.append(line)
                continue
            if data.get("__type") == "recipe" and data.get("id") == recipe_id:
                data.update(kwargs)
                found = True
            new_lines.append(json.dumps(data, ensure_ascii=False))
        if not found:
            return False
        self._path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        return True

    def increment_recipe_success(self, recipe_id: str) -> int:
        recipe = self.get_recipe(recipe_id)
        if not recipe:
            return 0
        count = recipe.success_count + 1
        self.update_recipe(recipe_id, success_count=count, last_used_at=datetime.now(timezone.utc).isoformat())
        return count

    def increment_recipe_fail(self, recipe_id: str) -> int:
        recipe = self.get_recipe(recipe_id)
        if not recipe:
            return 0
        count = recipe.fail_count + 1
        self.update_recipe(recipe_id, fail_count=count)
        return count

    def get_recipe(self, recipe_id: str) -> HealingRecipe | None:
        for recipe in self._iter_recipes():
            if recipe.id == recipe_id:
                return recipe
        return None

    def list_recipes(self, limit: int = 50) -> list[HealingRecipe]:
        return list(self._iter_recipes())[:limit]

    def delete_recipe(self, recipe_id: str) -> bool:
        if not self._path.exists():
            return False
        lines = self._path.read_text(encoding="utf-8").splitlines()
        new_lines: list[str] = []
        found = False
        for line in lines:
            if not line.strip():
                continue
            data = _load_json_safe(line)
            if data is None:
                new_lines.append(line)
                continue
            if data.get("__type") == "recipe" and data.get("id") == recipe_id:
                found = True
            else:
                new_lines.append(line)
        if not found:
            return False
        self._path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        return True

    def auto_register(
        self,
        system: str,
        step_data: dict,
        symptom: str,
        root_cause: str,
        fix: str,
        family: str = "",
        taxonomy: str = "",
        fix_type: str = "llm_auto",
        files_changed: Optional[list[str]] = None,
        url: str = "",
    ) -> str:
        attrs = step_data.get("attrs", {}) or {}
        entry = HealingEntry(
            system=system,
            symptom=symptom,
            root_cause=root_cause,
            fix=fix,
            family=migrate_family(family),
            taxonomy=migrate_taxonomy(taxonomy),
            fix_type=fix_type,
            files_changed=files_changed or [],
            url=url or step_data.get("url", ""),
            action=step_data.get("action", ""),
            selector=step_data.get("selector", ""),
            tag=step_data.get("tag_name", ""),
            input_type=attrs.get("type", ""),
        )
        return self.add(entry)
