"""Generate layered Zabbix templates from one existing export."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from ztt.template import TemplateFormatError, ZabbixTemplate
from ztt.writer import write_document


@dataclass(slots=True, frozen=True)
class LayerCreationResult:
    """Files and template names created by a layer generation operation."""

    base_file: Path
    system_file: Path
    base_template: str
    system_template: str
    discovery_rules: int


def _slug(value: str) -> str:
    cleaned = "_".join(value.strip().split())
    return cleaned.replace("/", "_").replace("\\", "_")


def _new_uuid() -> str:
    return uuid4().hex


def _regenerate_uuids(value: Any) -> None:
    """Replace every Zabbix UUID recursively in a generated document."""
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "uuid" and isinstance(child, str):
                value[key] = _new_uuid()
            else:
                _regenerate_uuids(child)
    elif isinstance(value, list):
        for child in value:
            _regenerate_uuids(child)


def create_base_system_layers(
    source: ZabbixTemplate,
    output_dir: Path,
    *,
    prefix: str | None = None,
    overwrite: bool = False,
) -> LayerCreationResult:
    """Create BASE and SYSTEM exports without modifying the source file.

    BASE keeps collection items, macros and shared objects. SYSTEM receives the
    complete discovery rule blocks and is linked to BASE. Every UUID is renewed
    so generated layers can be imported alongside the original template.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    original_technical = str(source.template.get("template", "TEMPLATE"))
    original_visible = str(source.template.get("name", original_technical))
    root_name = _slug(prefix or original_technical)

    base_technical = f"{root_name}_BASE"
    system_technical = f"{root_name}_SYSTEM"
    base_visible = f"{original_visible} BASE"
    system_visible = f"{original_visible} SYSTEM"

    base_file = output_dir / f"{base_technical}.yaml"
    system_file = output_dir / f"{system_technical}.yaml"
    for path in (base_file, system_file):
        if path.exists() and not overwrite:
            raise FileExistsError(f"Output file already exists: {path}")

    base_document = deepcopy(source.document)
    system_document = deepcopy(source.document)
    base_template = base_document["zabbix_export"]["templates"][0]
    system_template = system_document["zabbix_export"]["templates"][0]

    discovery_rules = base_template.pop("discovery_rules", [])
    if not isinstance(discovery_rules, list):
        raise TemplateFormatError("'discovery_rules' must be a list when present.")

    base_template["template"] = base_technical
    base_template["name"] = base_visible

    system_template["template"] = system_technical
    system_template["name"] = system_visible
    system_template["discovery_rules"] = discovery_rules
    system_template["templates"] = [{"name": base_technical}]

    for key in ("items", "triggers", "graphs", "dashboards", "macros"):
        system_template.pop(key, None)

    _regenerate_uuids(base_document)
    _regenerate_uuids(system_document)

    write_document(base_file, base_document)
    write_document(system_file, system_document)

    return LayerCreationResult(
        base_file=base_file,
        system_file=system_file,
        base_template=base_technical,
        system_template=system_technical,
        discovery_rules=len(discovery_rules),
    )
