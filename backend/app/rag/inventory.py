"""Technology inventory loader for the RAG knowledge layer.

Loads ``app/rag/data/technology_inventory.yaml`` — the seed knowledge artifact
that maps every technology DevArchAI can analyze to its canonical rule IDs,
applicable file types, external scanners, and ownership precedence.

Used for:

- rule-id -> technology reverse lookups (rule_id_first retrieval)
- technology -> known rule-id expansion (so a query for a technology can
  enumerate everything DevArchAI knows about it)
- cross-cutting rule categories
- external scanner references

The parsed inventory is cached (lru_cache); the YAML is the single source of
truth and is regenerated from backend source.
"""

from __future__ import annotations

import functools
from pathlib import Path

import yaml

from app.config import settings


class TechnologyInventory:
    """Parsed view of the technology inventory YAML."""

    def __init__(self, data: dict) -> None:
        self._data = data
        self._technologies = {t["id"]: t for t in data.get("technologies", [])}
        self._rule_to_tech: dict[str, list[str]] = {}
        for tech in data.get("technologies", []):
            for rule_id in tech.get("rule_ids", []):
                self._rule_to_tech.setdefault(rule_id, []).append(tech["id"])

    @property
    def version(self) -> str:
        return str(self._data.get("inventory_version", ""))

    @property
    def generated_at(self) -> str:
        return str(self._data.get("generated_at", ""))

    def technologies(self) -> list[str]:
        return list(self._technologies)

    def get_technology(self, tech_id: str) -> dict | None:
        return self._technologies.get(tech_id)

    def is_known_technology(self, tech_id: str) -> bool:
        return tech_id in self._technologies

    def rule_ids_for(self, tech_id: str) -> list[str]:
        tech = self._technologies.get(tech_id)
        if not tech:
            return []
        return list(tech.get("rule_ids", []))

    def technology_for_rule_id(self, rule_id: str) -> list[str]:
        """Return the technologies a rule_id belongs to (reverse lookup)."""
        return list(self._rule_to_tech.get(rule_id, []))

    def external_scanners(self) -> list[dict]:
        return list(self._data.get("external_scanners", []))

    def scanner_names(self) -> list[str]:
        return [s["name"] for s in self.external_scanners()]

    def cross_cutting(self) -> list[dict]:
        return list(self._data.get("cross_cutting", []))

    def cross_cutting_rule_ids(self) -> list[str]:
        ids: list[str] = []
        for cat in self.cross_cutting():
            ids.extend(cat.get("rule_ids", []))
        return ids

    def all_rule_ids(self) -> list[str]:
        ids: list[str] = []
        for tech in self._data.get("technologies", []):
            ids.extend(tech.get("rule_ids", []))
        ids.extend(self.cross_cutting_rule_ids())
        return ids

    def categories_for_technology(self, tech_id: str) -> list[str]:
        tech = self._technologies.get(tech_id)
        if not tech:
            return []
        return list(tech.get("categories", []))

    def file_types_for(self, tech_id: str) -> list[str]:
        tech = self._technologies.get(tech_id)
        if not tech:
            return []
        return list(tech.get("file_types", []))

    def external_scanners_for(self, tech_id: str) -> list[str]:
        tech = self._technologies.get(tech_id)
        if not tech:
            return []
        return list(tech.get("external_scanners", []))


@functools.lru_cache(maxsize=1)
def load_inventory(path: str | None = None) -> TechnologyInventory:
    """Load (and cache) the technology inventory."""
    path = path or settings.RAG_INVENTORY_PATH
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return TechnologyInventory(data)


def get_inventory() -> TechnologyInventory:
    """Get the cached technology inventory singleton."""
    return load_inventory()


def invalidate_inventory_cache() -> None:
    """Clear the cached inventory (used when the YAML is regenerated)."""
    load_inventory.cache_clear()
