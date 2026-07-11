"""Generate layered Zabbix templates from one existing export."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from ztt.business import _clone_filesystem_rule, _clone_service_rule
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


def _normalise_tags(tags: dict[str, str] | None) -> list[dict[str, str]]:
    if not tags:
        return []
    return [{"tag": tag, "value": value} for tag, value in tags.items() if tag]


def _business_macros(
    filesystem_matches: str | None,
    filesystem_not_matches: str | None,
    service_matches: str | None,
    service_not_matches: str | None,
) -> list[dict[str, str]]:
    values = (
        ("{$BUSINESS.FS.MATCHES}", filesystem_matches),
        ("{$BUSINESS.FS.NOT_MATCHES}", filesystem_not_matches),
        ("{$BUSINESS.SERVICE.MATCHES}", service_matches),
        ("{$BUSINESS.SERVICE.NOT_MATCHES}", service_not_matches),
    )
    return [{"macro": macro, "value": value} for macro, value in values if value is not None]


def _is_service_rule(rule: dict[str, Any]) -> bool:
    key = str(rule.get("key", "")).lower()
    name = str(rule.get("name", "")).lower()
    return "service.discovery" in key or "service" in name


def _service_master_item(rule: dict[str, Any]) -> dict[str, Any]:
    """Convert a native service discovery rule into a reusable raw item."""
    allowed = {
        "name",
        "type",
        "key",
        "delay",
        "history",
        "value_type",
        "description",
        "preprocessing",
        "timeout",
        "tags",
    }
    item = {key: deepcopy(value) for key, value in rule.items() if key in allowed}
    item["uuid"] = _new_uuid()
    item["name"] = f"{rule.get('name', 'Windows services discovery')} raw data"
    item["key"] = str(rule.get("key", "service.discovery"))
    item["value_type"] = "TEXT"
    item.setdefault("history", "0")
    return item


def _dependent_service_rule(rule: dict[str, Any]) -> dict[str, Any]:
    clone = deepcopy(rule)
    raw_key = str(rule.get("key", "service.discovery"))
    clone["type"] = "DEPENDENT"
    clone["key"] = "ztt.system.service.discovery"
    clone["master_item"] = {"key": raw_key}
    clone.pop("delay", None)
    return clone


def _prepare_shared_services(
    discovery_rules: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    masters: list[dict[str, Any]] = []
    prepared: list[dict[str, Any]] = []
    for rule in discovery_rules:
        if _is_service_rule(rule) and not isinstance(rule.get("master_item"), dict):
            masters.append(_service_master_item(rule))
            prepared.append(_dependent_service_rule(rule))
        else:
            prepared.append(rule)
    return masters, prepared


def create_layered_templates(
    source: ZabbixTemplate,
    output_dir: Path,
    *,
    prefix: str | None = None,
    overwrite: bool = False,
    business_name: str = "BUSINESS",
    system_tags: dict[str, str] | None = None,
    business_tags: dict[str, str] | None = None,
    filesystem_matches: str | None = None,
    filesystem_not_matches: str | None = None,
    service_matches: str | None = None,
    service_not_matches: str | None = None,
) -> LayerCreationResult:
    """Create BASE, SYSTEM and a configurable BUSINESS template."""
    output_dir.mkdir(parents=True, exist_ok=True)

    original_technical = str(source.template.get("template", "TEMPLATE"))
    original_visible = str(source.template.get("name", original_technical))
    root_name = _slug(prefix or original_technical)
    business_suffix = _slug(business_name or "BUSINESS")
    namespace = business_suffix.lower()

    base_technical = f"{root_name}_BASE"
    system_technical = f"{root_name}_SYSTEM"
    business_technical = f"{root_name}_{business_suffix}"
    base_visible = f"{original_visible} BASE"
    system_visible = f"{original_visible} SYSTEM"
    business_visible = f"{original_visible} {business_name or 'BUSINESS'}"

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
    discovery_rules = [rule for rule in discovery_rules if isinstance(rule, dict)]
    service_masters, discovery_rules = _prepare_shared_services(discovery_rules)
    if service_masters:
        base_template.setdefault("items", []).extend(service_masters)

    dashboards = base_template.pop("dashboards", [])
    if not isinstance(dashboards, list):
        raise TemplateFormatError("'dashboards' must be a list when present.")

    required_valuemaps = _select_valuemaps(
        system_template.get("valuemaps", []),
        _collect_valuemap_names(discovery_rules),
    )

    base_template["template"] = base_technical
    base_template["name"] = base_visible

    system_template["template"] = system_technical
    system_template["name"] = system_visible
    system_template["discovery_rules"] = discovery_rules
    system_template["templates"] = [{"name": base_technical}]
    tags = _normalise_tags(system_tags)
    if tags:
        system_template["tags"] = tags
    else:
        system_template.pop("tags", None)
    if required_valuemaps:
        system_template["valuemaps"] = required_valuemaps
    else:
        system_template.pop("valuemaps", None)
    _remove_template_objects(system_template, ("items", "triggers", "graphs", "macros", "dashboards"))

    business_template["template"] = business_technical
    business_template["name"] = business_visible
    business_template["templates"] = [{"name": system_technical}]
    business_template.pop("tags", None)
    business_template.pop("macros", None)
    tags = _normalise_tags(business_tags)
    macros = _business_macros(
        filesystem_matches,
        filesystem_not_matches,
        service_matches,
        service_not_matches,
    )
    if tags:
        business_template["tags"] = tags
    if macros:
        business_template["macros"] = macros

    business_rules: list[dict[str, Any]] = []
    for rule in discovery_rules:
        key = str(rule.get("key", ""))
        name = str(rule.get("name", "")).lower()
        if filesystem_matches is not None and ("vfs.fs" in key or "filesystem" in name):
            business_rules.append(_clone_filesystem_rule(rule, namespace))
        elif service_matches is not None and _is_service_rule(rule):
            clone = _clone_service_rule(rule, namespace)
            if clone is not None:
                business_rules.append(clone)

    _remove_template_objects(
        business_template,
        ("items", "triggers", "graphs", "valuemaps", "dashboards"),
    )
    if business_rules:
        business_template["discovery_rules"] = business_rules
    else:
        business_template.pop("discovery_rules", None)

    for export in (system_export, business_export):
        export.pop("triggers", None)
        export.pop("graphs", None)

    _rewrite_template_references(base_document, original_technical, base_technical)
    _rewrite_template_references(system_document, original_technical, system_technical)
    _rewrite_template_references(business_document, original_technical, business_technical)
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
