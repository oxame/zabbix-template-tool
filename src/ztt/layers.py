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
    business_file: Path
    base_template: str
    system_template: str
    business_template: str
    discovery_rules: int
    dashboards: int


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


def _rewrite_template_references(value: Any, old: str, new: str) -> None:
    """Rewrite host references and expression paths to a generated template."""
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "host" and child == old:
                value[key] = new
            elif isinstance(child, str):
                value[key] = child.replace(f"/{old}/", f"/{new}/")
            else:
                _rewrite_template_references(child, old, new)
    elif isinstance(value, list):
        for child in value:
            _rewrite_template_references(child, old, new)


def _collect_valuemap_names(value: Any) -> set[str]:
    """Collect value-map names referenced anywhere in a discovery-rule subtree."""
    names: set[str] = set()
    if isinstance(value, dict):
        valuemap = value.get("valuemap")
        if isinstance(valuemap, dict):
            name = valuemap.get("name")
            if isinstance(name, str) and name:
                names.add(name)
        for child in value.values():
            names.update(_collect_valuemap_names(child))
    elif isinstance(value, list):
        for child in value:
            names.update(_collect_valuemap_names(child))
    return names


def _select_valuemaps(valuemaps: Any, names: set[str]) -> list[Any]:
    """Return only the value maps required by objects moved to SYSTEM."""
    if not names:
        return []
    if not isinstance(valuemaps, list):
        raise TemplateFormatError("'valuemaps' must be a list when present.")
    return [
        deepcopy(valuemap)
        for valuemap in valuemaps
        if isinstance(valuemap, dict) and valuemap.get("name") in names
    ]


def _remove_template_objects(template: dict[str, Any], keys: tuple[str, ...]) -> None:
    for key in keys:
        template.pop(key, None)


def create_layered_templates(
    source: ZabbixTemplate,
    output_dir: Path,
    *,
    prefix: str | None = None,
    overwrite: bool = False,
) -> LayerCreationResult:
    """Create coherent BASE, SYSTEM and BUSINESS exports.

    BASE owns collection items, macros, value maps, standalone triggers and
    graphs. SYSTEM owns LLD rules and the value maps required by prototypes.
    BUSINESS currently contains only the link to SYSTEM. Dashboards are counted
    but deliberately skipped until their cross-template references can be
    validated reliably. Every generated template gets independent UUIDs and the
    source file is never modified.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    original_technical = str(source.template.get("template", "TEMPLATE"))
    original_visible = str(source.template.get("name", original_technical))
    root_name = _slug(prefix or original_technical)

    base_technical = f"{root_name}_BASE"
    system_technical = f"{root_name}_SYSTEM"
    business_technical = f"{root_name}_BUSINESS"
    base_visible = f"{original_visible} BASE"
    system_visible = f"{original_visible} SYSTEM"
    business_visible = f"{original_visible} BUSINESS"

    base_file = output_dir / f"{base_technical}.yaml"
    system_file = output_dir / f"{system_technical}.yaml"
    business_file = output_dir / f"{business_technical}.yaml"
    for path in (base_file, system_file, business_file):
        if path.exists() and not overwrite:
            raise FileExistsError(f"Output file already exists: {path}")

    base_document = deepcopy(source.document)
    system_document = deepcopy(source.document)
    business_document = deepcopy(source.document)

    base_export = base_document["zabbix_export"]
    system_export = system_document["zabbix_export"]
    business_export = business_document["zabbix_export"]
    base_template = base_export["templates"][0]
    system_template = system_export["templates"][0]
    business_template = business_export["templates"][0]

    discovery_rules = base_template.pop("discovery_rules", [])
    if not isinstance(discovery_rules, list):
        raise TemplateFormatError("'discovery_rules' must be a list when present.")

    dashboards = base_template.pop("dashboards", [])
    if not isinstance(dashboards, list):
        raise TemplateFormatError("'dashboards' must be a list when present.")

    required_valuemap_names = _collect_valuemap_names(discovery_rules)
    required_valuemaps = _select_valuemaps(
        system_template.get("valuemaps", []),
        required_valuemap_names,
    )

    base_template["template"] = base_technical
    base_template["name"] = base_visible

    system_template["template"] = system_technical
    system_template["name"] = system_visible
    system_template["discovery_rules"] = discovery_rules
    system_template["templates"] = [{"name": base_technical}]
    if required_valuemaps:
        system_template["valuemaps"] = required_valuemaps
    else:
        system_template.pop("valuemaps", None)
    _remove_template_objects(
        system_template,
        ("items", "triggers", "graphs", "macros", "dashboards"),
    )

    business_template["template"] = business_technical
    business_template["name"] = business_visible
    business_template["templates"] = [{"name": system_technical}]
    _remove_template_objects(
        business_template,
        (
            "items",
            "discovery_rules",
            "triggers",
            "graphs",
            "macros",
            "valuemaps",
            "dashboards",
        ),
    )

    for export in (system_export, business_export):
        export.pop("triggers", None)
        export.pop("graphs", None)

    _rewrite_template_references(base_document, original_technical, base_technical)
    _rewrite_template_references(system_document, original_technical, system_technical)

    _regenerate_uuids(base_document)
    _regenerate_uuids(system_document)
    _regenerate_uuids(business_document)

    write_document(base_file, base_document)
    write_document(system_file, system_document)
    write_document(business_file, business_document)

    return LayerCreationResult(
        base_file=base_file,
        system_file=system_file,
        business_file=business_file,
        base_template=base_technical,
        system_template=system_technical,
        business_template=business_technical,
        discovery_rules=len(discovery_rules),
        dashboards=len(dashboards),
    )


def create_base_system_layers(
    source: ZabbixTemplate,
    output_dir: Path,
    *,
    prefix: str | None = None,
    overwrite: bool = False,
) -> LayerCreationResult:
    """Backward-compatible alias for the three-layer generator."""
    return create_layered_templates(
        source,
        output_dir,
        prefix=prefix,
        overwrite=overwrite,
    )
