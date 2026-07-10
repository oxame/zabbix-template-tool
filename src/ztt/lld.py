"""Operations on Zabbix low-level discovery rules."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from shutil import copy2
from typing import Any

from ztt.template import TemplateFormatError, ZabbixTemplate
from ztt.writer import write_document


@dataclass(slots=True, frozen=True)
class DiscoveryRuleInfo:
    """Display information for one discovery rule."""

    index: int
    name: str
    key: str
    uuid: str
    item_prototypes: int
    trigger_prototypes: int
    graph_prototypes: int
    overrides: int


@dataclass(slots=True, frozen=True)
class MoveResult:
    """Result of an LLD move operation."""

    moved: tuple[DiscoveryRuleInfo, ...]
    source_remaining: int
    destination_total: int
    dry_run: bool


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def list_discovery_rules(template: ZabbixTemplate) -> list[DiscoveryRuleInfo]:
    """Return normalized information about all discovery rules."""
    result: list[DiscoveryRuleInfo] = []
    for index, rule in enumerate(_as_list(template.template.get("discovery_rules")), start=1):
        if not isinstance(rule, dict):
            continue
        result.append(
            DiscoveryRuleInfo(
                index=index,
                name=str(rule.get("name", "unnamed")),
                key=str(rule.get("key", "")),
                uuid=str(rule.get("uuid", "")),
                item_prototypes=len(_as_list(rule.get("item_prototypes"))),
                trigger_prototypes=len(_as_list(rule.get("trigger_prototypes"))),
                graph_prototypes=len(_as_list(rule.get("graph_prototypes"))),
                overrides=len(_as_list(rule.get("overrides"))),
            )
        )
    return result


def _rule_identity(rule: dict[str, Any]) -> tuple[str, str]:
    return str(rule.get("uuid", "")), str(rule.get("key", ""))


def move_discovery_rules(
    source: ZabbixTemplate,
    destination: ZabbixTemplate,
    *,
    selectors: list[str] | None = None,
    move_all: bool = False,
    dry_run: bool = True,
    backup: bool = True,
) -> MoveResult:
    """Move selected LLD rules while preserving each complete nested rule block.

    Selectors match a rule UUID, technical key, or exact display name.
    """
    if source.path.resolve() == destination.path.resolve():
        raise TemplateFormatError("Source and destination must be different files.")
    if not move_all and not selectors:
        raise TemplateFormatError("Provide at least one --select value or use --all.")

    source_rules = _as_list(source.template.get("discovery_rules"))
    destination_rules = _as_list(destination.template.get("discovery_rules"))
    selectors_set = set(selectors or [])

    selected: list[dict[str, Any]] = []
    retained: list[Any] = []
    for rule in source_rules:
        if not isinstance(rule, dict):
            retained.append(rule)
            continue
        matches = move_all or bool(
            selectors_set.intersection(
                {
                    str(rule.get("uuid", "")),
                    str(rule.get("key", "")),
                    str(rule.get("name", "")),
                }
            )
        )
        (selected if matches else retained).append(rule)

    if not selected:
        raise TemplateFormatError("No discovery rule matched the requested selector(s).")

    existing = {_rule_identity(rule) for rule in destination_rules if isinstance(rule, dict)}
    duplicates = [rule for rule in selected if _rule_identity(rule) in existing]
    if duplicates:
        labels = ", ".join(str(rule.get("name", rule.get("key", "unnamed"))) for rule in duplicates)
        raise TemplateFormatError(f"Destination already contains matching LLD rule(s): {labels}")

    infos_by_identity = {
        (info.uuid, info.key): info for info in list_discovery_rules(source)
    }
    moved_infos = tuple(
        infos_by_identity.get(
            _rule_identity(rule),
            DiscoveryRuleInfo(0, str(rule.get("name", "unnamed")), str(rule.get("key", "")), str(rule.get("uuid", "")), 0, 0, 0, 0),
        )
        for rule in selected
    )

    if not dry_run:
        if backup:
            copy2(source.path, source.path.with_suffix(source.path.suffix + ".bak"))
            copy2(destination.path, destination.path.with_suffix(destination.path.suffix + ".bak"))

        if retained:
            source.template["discovery_rules"] = retained
        else:
            source.template.pop("discovery_rules", None)
        destination.template["discovery_rules"] = [*destination_rules, *selected]

        write_document(source.path, source.document)
        write_document(destination.path, destination.document)

    return MoveResult(
        moved=moved_infos,
        source_remaining=len(retained),
        destination_total=len(destination_rules) + len(selected),
        dry_run=dry_run,
    )
