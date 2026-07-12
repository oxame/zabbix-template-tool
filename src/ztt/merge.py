"""Merge Zabbix YAML templates with conflict detection and dry-run support."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from ztt.template import TemplateFormatError, ZabbixTemplate
from ztt.validation import ensure_valid_template
from ztt.writer import write_document

ConflictMode = Literal["error", "keep-first", "keep-last"]


@dataclass(slots=True, frozen=True)
class MergeConflict:
    section: str
    identity: str
    source: Path


@dataclass(slots=True, frozen=True)
class MergeResult:
    output_file: Path
    dry_run: bool
    source_count: int
    added: dict[str, int]
    conflicts: tuple[MergeConflict, ...]


_SECTIONS = (
    "items",
    "discovery_rules",
    "triggers",
    "graphs",
    "macros",
    "valuemaps",
    "tags",
    "templates",
)


def _identity(section: str, obj: dict[str, Any]) -> str:
    if section in {"items", "discovery_rules"}:
        value = obj.get("key")
    elif section == "macros":
        value = obj.get("macro")
    elif section in {"valuemaps", "graphs", "templates"}:
        value = obj.get("name")
    elif section == "tags":
        value = f"{obj.get('tag', '')}={obj.get('value', '')}"
    elif section == "triggers":
        value = obj.get("expression") or obj.get("name")
    else:
        value = obj.get("uuid") or obj.get("name")
    if not isinstance(value, str) or not value:
        raise TemplateFormatError(f"Cannot identify object in section '{section}': {obj!r}")
    return value


def _regenerate_uuids(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "uuid" and isinstance(child, str):
                value[key] = uuid4().hex
            else:
                _regenerate_uuids(child)
    elif isinstance(value, list):
        for child in value:
            _regenerate_uuids(child)


def _rewrite_template_references(value: Any, source_name: str, target_name: str) -> None:
    """Rewrite object references that must point to the merged template.

    Zabbix graph prototypes store the owning template in an exact ``host`` field,
    while trigger expressions use ``/TEMPLATE/key`` paths. Linked parent
    templates are intentionally left unchanged.
    """
    if source_name == target_name:
        return
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "host" and child == source_name:
                value[key] = target_name
            elif isinstance(child, str):
                value[key] = child.replace(f"/{source_name}/", f"/{target_name}/")
            else:
                _rewrite_template_references(child, source_name, target_name)
    elif isinstance(value, list):
        for child in value:
            _rewrite_template_references(child, source_name, target_name)


def merge_templates(
    sources: list[ZabbixTemplate],
    output_file: Path,
    *,
    conflict_mode: ConflictMode = "error",
    apply: bool = False,
    overwrite: bool = False,
    template_name: str | None = None,
) -> MergeResult:
    """Merge template objects into a copy of the first source template."""
    if len(sources) < 2:
        raise ValueError("At least two source templates are required.")
    if conflict_mode not in {"error", "keep-first", "keep-last"}:
        raise ValueError(f"Unsupported conflict mode: {conflict_mode}")
    if output_file.exists() and apply and not overwrite:
        raise FileExistsError(f"Output file already exists: {output_file}")

    document = deepcopy(sources[0].document)
    target = document["zabbix_export"]["templates"][0]
    first_source_name = str(sources[0].template.get("template", ""))
    target_name = template_name or first_source_name
    if template_name:
        target["template"] = template_name
        target["name"] = template_name
    _rewrite_template_references(document, first_source_name, target_name)

    indexes: dict[str, dict[str, int]] = {}
    added = {section: 0 for section in _SECTIONS}
    conflicts: list[MergeConflict] = []

    for section in _SECTIONS:
        existing = target.get(section, [])
        if existing is None:
            existing = []
        if not isinstance(existing, list):
            raise TemplateFormatError(f"'{section}' must be a list when present.")
        target[section] = existing
        indexes[section] = {
            _identity(section, obj): index
            for index, obj in enumerate(existing)
            if isinstance(obj, dict)
        }

    for source in sources[1:]:
        source_name = str(source.template.get("template", ""))
        for section in _SECTIONS:
            objects = source.template.get(section, [])
            if objects is None:
                continue
            if not isinstance(objects, list):
                raise TemplateFormatError(f"'{section}' must be a list when present.")
            for obj in objects:
                if not isinstance(obj, dict):
                    continue
                identity = _identity(section, obj)
                current_index = indexes[section].get(identity)
                if current_index is not None:
                    conflicts.append(MergeConflict(section, identity, source.path))
                    if conflict_mode == "error":
                        continue
                    if conflict_mode == "keep-first":
                        continue
                    replacement = deepcopy(obj)
                    _rewrite_template_references(replacement, source_name, target_name)
                    _regenerate_uuids(replacement)
                    target[section][current_index] = replacement
                    continue

                clone = deepcopy(obj)
                _rewrite_template_references(clone, source_name, target_name)
                _regenerate_uuids(clone)
                indexes[section][identity] = len(target[section])
                target[section].append(clone)
                added[section] += 1

    for section in _SECTIONS:
        if not target[section]:
            target.pop(section, None)

    if conflicts and conflict_mode == "error" and apply:
        summary = ", ".join(f"{c.section}:{c.identity}" for c in conflicts[:10])
        raise ValueError(f"Merge conflicts detected: {summary}")

    _regenerate_uuids(document)
    generated = ZabbixTemplate.from_document(output_file, document)
    ensure_valid_template(generated)

    if apply:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        write_document(output_file, document)

    return MergeResult(
        output_file=output_file,
        dry_run=not apply,
        source_count=len(sources),
        added=added,
        conflicts=tuple(conflicts),
    )
