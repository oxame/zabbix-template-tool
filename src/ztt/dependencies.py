"""Dependency analysis for Zabbix template objects."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from ztt.template import ZabbixTemplate

_MACRO_PATTERN = re.compile(r"\{\$[A-Z0-9_.:-]+\}", re.IGNORECASE)


@dataclass(slots=True, frozen=True)
class Dependency:
    """A dependency referenced by a Zabbix object."""

    kind: str
    reference: str
    present: bool
    location: str


@dataclass(slots=True, frozen=True)
class RuleDependencyReport:
    """Dependencies detected for one discovery rule."""

    rule_name: str
    rule_key: str
    dependencies: tuple[Dependency, ...]

    @property
    def missing(self) -> tuple[Dependency, ...]:
        return tuple(dependency for dependency in self.dependencies if not dependency.present)


def _walk(value: Any, location: str = "rule") -> list[tuple[str, Any]]:
    result: list[tuple[str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_location = f"{location}.{key}"
            result.append((child_location, child))
            result.extend(_walk(child, child_location))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_location = f"{location}[{index}]"
            result.extend(_walk(child, child_location))
    return result


def _template_macros(template: ZabbixTemplate) -> set[str]:
    macros = template.template.get("macros", [])
    if not isinstance(macros, list):
        return set()
    return {
        str(macro.get("macro"))
        for macro in macros
        if isinstance(macro, dict) and macro.get("macro")
    }


def _template_value_maps(template: ZabbixTemplate) -> set[str]:
    export = template.document.get("zabbix_export", {})
    value_maps = export.get("value_maps", []) if isinstance(export, dict) else []
    if not isinstance(value_maps, list):
        return set()
    return {
        str(value_map.get("name"))
        for value_map in value_maps
        if isinstance(value_map, dict) and value_map.get("name")
    }


def _template_item_keys(template: ZabbixTemplate) -> set[str]:
    items = template.template.get("items", [])
    if not isinstance(items, list):
        return set()
    return {
        str(item.get("key"))
        for item in items
        if isinstance(item, dict) and item.get("key")
    }


def analyze_lld_dependencies(template: ZabbixTemplate) -> list[RuleDependencyReport]:
    """Analyze macros, value maps and master items referenced by LLD rules."""
    macros = _template_macros(template)
    value_maps = _template_value_maps(template)
    item_keys = _template_item_keys(template)
    rules = template.template.get("discovery_rules", [])
    if not isinstance(rules, list):
        return []

    reports: list[RuleDependencyReport] = []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        found: dict[tuple[str, str], Dependency] = {}
        for location, value in _walk(rule):
            if isinstance(value, str):
                for macro in _MACRO_PATTERN.findall(value):
                    found[("macro", macro)] = Dependency(
                        kind="macro",
                        reference=macro,
                        present=macro in macros,
                        location=location,
                    )
            if location.endswith(".value_map") and isinstance(value, dict):
                name = value.get("name")
                if name:
                    reference = str(name)
                    found[("value_map", reference)] = Dependency(
                        kind="value_map",
                        reference=reference,
                        present=reference in value_maps,
                        location=location,
                    )
            if location.endswith(".master_item") and isinstance(value, dict):
                key = value.get("key")
                if key:
                    reference = str(key)
                    found[("master_item", reference)] = Dependency(
                        kind="master_item",
                        reference=reference,
                        present=reference in item_keys,
                        location=location,
                    )

        reports.append(
            RuleDependencyReport(
                rule_name=str(rule.get("name", "unnamed")),
                rule_key=str(rule.get("key", "")),
                dependencies=tuple(found.values()),
            )
        )
    return reports
