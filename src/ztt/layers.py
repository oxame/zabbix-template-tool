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


def _widget_layer(widget: Any) -> str:
    """Return the owning layer for a dashboard widget."""
    if not isinstance(widget, dict):
        return "base"
    for field in widget.get("fields", []):
        if isinstance(field, dict) and field.get("type") == "GRAPH_PROTOTYPE":
            return "system"
    return "base"


def _split_dashboards(dashboards: list[Any]) -> tuple[list[Any], list[Any]]:
    """Split mixed dashboards so every widget references objects in one layer."""
    base_dashboards: list[Any] = []
    system_dashboards: list[Any] = []

    for dashboard in dashboards:
        if not isinstance(dashboard, dict):
            continue
        base_dashboard = deepcopy(dashboard)
        system_dashboard = deepcopy(dashboard)
        base_pages: list[Any] = []
        system_pages: list[Any] = []

        for page in dashboard.get("pages", []):
            if not isinstance(page, dict):
                continue
            base_page = deepcopy(page)
            system_page = deepcopy(page)
            widgets = page.get("widgets", [])
            if not isinstance(widgets, list):
                widgets = []
            base_widgets = [deepcopy(w) for w in widgets if _widget_layer(w) == "base"]
            system_widgets = [deepcopy(w) for w in widgets if _widget_layer(w) == "system"]
            if base_widgets:
                base_page["widgets"] = base_widgets
                base_pages.append(base_page)
            if system_widgets:
                system_page["widgets"] = system_widgets
                system_pages.append(system_page)

        if base_pages:
            base_dashboard["pages"] = base_pages
            base_dashboards.append(base_dashboard)
        if system_pages:
            system_dashboard["pages"] = system_pages
            system_dashboards.append(system_dashboard)

    return base_dashboards, system_dashboards


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


def create_base_system_layers(
    source: ZabbixTemplate,
    output_dir: Path,
    *,
    prefix: str | None = None,
    overwrite: bool = False,
) -> LayerCreationResult:
    """Create coherent BASE and SYSTEM exports without modifying the source.

    BASE owns collection items, macros, value maps, standalone triggers, graphs,
    and dashboard widgets that use them. SYSTEM owns LLD rules, their required
    value maps, graph-prototype dashboard widgets, and inherits BASE.
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
    base_export = base_document["zabbix_export"]
    system_export = system_document["zabbix_export"]
    base_template = base_export["templates"][0]
    system_template = system_export["templates"][0]

    discovery_rules = base_template.pop("discovery_rules", [])
    if not isinstance(discovery_rules, list):
        raise TemplateFormatError("'discovery_rules' must be a list when present.")

    dashboards = base_template.pop("dashboards", [])
    if not isinstance(dashboards, list):
        raise TemplateFormatError("'dashboards' must be a list when present.")
    base_dashboards, system_dashboards = _split_dashboards(dashboards)

    required_valuemap_names = _collect_valuemap_names(discovery_rules)
    required_valuemaps = _select_valuemaps(
        system_template.get("valuemaps", []),
        required_valuemap_names,
    )

    base_template["template"] = base_technical
    base_template["name"] = base_visible
    if base_dashboards:
        base_template["dashboards"] = base_dashboards

    system_template["template"] = system_technical
    system_template["name"] = system_visible
    system_template["discovery_rules"] = discovery_rules
    system_template["templates"] = [{"name": base_technical}]
    if system_dashboards:
        system_template["dashboards"] = system_dashboards
    else:
        system_template.pop("dashboards", None)
    if required_valuemaps:
        system_template["valuemaps"] = required_valuemaps
    else:
        system_template.pop("valuemaps", None)

    for key in ("items", "triggers", "graphs", "macros"):
        system_template.pop(key, None)

    system_export.pop("triggers", None)
    system_export.pop("graphs", None)

    _rewrite_template_references(base_document, original_technical, base_technical)
    _rewrite_template_references(system_document, original_technical, system_technical)

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
