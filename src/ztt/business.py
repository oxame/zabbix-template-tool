"""Generate additional BUSINESS templates from an existing SYSTEM template."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from ztt.template import TemplateFormatError, ZabbixTemplate
from ztt.validation import ensure_valid_template
from ztt.writer import write_document


@dataclass(slots=True, frozen=True)
class BusinessCreationResult:
    file: Path
    template: str
    filesystem_rules: int
    service_rules: int
    skipped_service_rules: int


def _slug(value: str) -> str:
    cleaned = "_".join(value.strip().split())
    return cleaned.replace("/", "_").replace("\\", "_")


def _key_slug(value: str) -> str:
    return _slug(value).lower()


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


def _rewrite_strings(value: Any, replacements: dict[str, str]) -> None:
    ordered = sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True)
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(child, str):
                updated = child
                for old, new in ordered:
                    updated = updated.replace(old, new)
                value[key] = updated
            else:
                _rewrite_strings(child, replacements)
    elif isinstance(value, list):
        for child in value:
            _rewrite_strings(child, replacements)


def _rewrite_template_hosts(value: Any, old_host: str, new_host: str) -> None:
    """Rewrite explicit Zabbix object host references.

    Trigger expressions contain the template name between slashes and are handled
    by ``_rewrite_strings``. Graph prototypes instead store the template name in
    a dedicated ``host`` field, which must point to the BUSINESS template that
    owns the namespaced item prototypes.
    """

    if isinstance(value, dict):
        for key, child in value.items():
            if key == "host" and child == old_host:
                value[key] = new_host
            else:
                _rewrite_template_hosts(child, old_host, new_host)
    elif isinstance(value, list):
        for child in value:
            _rewrite_template_hosts(child, old_host, new_host)


def _required_valuemap_names(discovery_rules: list[dict[str, Any]]) -> set[str]:
    """Return value maps referenced directly by cloned item prototypes."""

    names: set[str] = set()
    for rule in discovery_rules:
        prototypes = rule.get("item_prototypes", [])
        if not isinstance(prototypes, list):
            continue
        for prototype in prototypes:
            if not isinstance(prototype, dict):
                continue
            valuemap = prototype.get("valuemap")
            if not isinstance(valuemap, dict):
                continue
            name = valuemap.get("name")
            if isinstance(name, str) and name:
                names.add(name)
    return names


def _select_required_valuemaps(
    source_valuemaps: Any,
    discovery_rules: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Copy only value maps referenced by the selected BUSINESS prototypes."""

    required_names = _required_valuemap_names(discovery_rules)
    if not required_names:
        return []
    if not isinstance(source_valuemaps, list):
        raise TemplateFormatError("'valuemaps' must be a list when present.")

    available = {
        entry.get("name"): entry
        for entry in source_valuemaps
        if isinstance(entry, dict) and isinstance(entry.get("name"), str)
    }
    missing = sorted(required_names - set(available))
    if missing:
        raise TemplateFormatError(
            "Required value map(s) not found in SYSTEM template: " + ", ".join(missing)
        )
    return [deepcopy(available[name]) for name in sorted(required_names)]


def _normalise_tags(tags: dict[str, str] | None) -> list[dict[str, str]]:
    if not tags:
        return []
    return [{"tag": key, "value": value} for key, value in tags.items() if key]


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


def _find_filter_macro(rule: dict[str, Any], candidates: tuple[str, ...]) -> str | None:
    filter_data = rule.get("filter")
    if not isinstance(filter_data, dict):
        return None
    for condition in filter_data.get("conditions", []):
        if not isinstance(condition, dict):
            continue
        macro = condition.get("macro")
        if isinstance(macro, str) and macro in candidates:
            return macro
    return None


def _set_business_filter(
    rule: dict[str, Any],
    lld_macro: str,
    matches_macro: str,
    not_matches_macro: str,
) -> None:
    rule["filter"] = {
        "evaltype": "AND",
        "conditions": [
            {"macro": lld_macro, "value": matches_macro},
            {"macro": lld_macro, "value": not_matches_macro, "operator": "NOT_MATCHES_REGEX"},
        ],
    }


def _namespace_graph_prototype_names(rule: dict[str, Any], namespace: str) -> None:
    """Give cloned graph prototypes names unique to their BUSINESS layer."""

    graph_prototypes = rule.get("graph_prototypes", [])
    if not isinstance(graph_prototypes, list):
        return

    suffix = f" - BUSINESS {namespace}"
    for graph in graph_prototypes:
        if not isinstance(graph, dict):
            continue
        name = graph.get("name")
        if isinstance(name, str) and name and not name.endswith(suffix):
            graph["name"] = f"{name}{suffix}"


def _namespace_item_prototype_keys(rule: dict[str, Any], namespace: str) -> None:
    """Give every cloned item prototype a unique BUSINESS key."""

    replacements: dict[str, str] = {}
    prototypes = rule.get("item_prototypes", [])
    if not isinstance(prototypes, list):
        return

    prefix = f"ztt.business.{namespace}."
    for prototype in prototypes:
        if not isinstance(prototype, dict):
            continue
        old_key = prototype.get("key")
        if not isinstance(old_key, str) or not old_key:
            continue
        replacements[old_key] = old_key if old_key.startswith(prefix) else f"{prefix}{old_key}"

    if replacements:
        _rewrite_strings(rule, replacements)


def _clone_filesystem_rule(rule: dict[str, Any], namespace: str) -> dict[str, Any]:
    clone = deepcopy(rule)
    old_key = str(clone.get("key", "vfs.fs.discovery"))
    new_key = f"ztt.business.{namespace}.fs.discovery"
    clone["name"] = f"{clone.get('name', 'Filesystem discovery')} - BUSINESS {namespace}"
    clone["key"] = new_key
    lld_macro = _find_filter_macro(clone, ("{#FSNAME}", "{#FSLABEL}")) or "{#FSNAME}"
    _set_business_filter(
        clone,
        lld_macro,
        "{$BUSINESS.FS.MATCHES}",
        "{$BUSINESS.FS.NOT_MATCHES}",
    )
    _namespace_item_prototype_keys(clone, namespace)
    _namespace_graph_prototype_names(clone, namespace)
    _rewrite_strings(clone, {old_key: new_key})
    return clone


def _clone_service_rule(rule: dict[str, Any], namespace: str) -> dict[str, Any] | None:
    if not isinstance(rule.get("master_item"), dict):
        return None
    clone = deepcopy(rule)
    old_key = str(clone.get("key", "service.discovery"))
    new_key = f"ztt.business.{namespace}.service.discovery"
    clone["name"] = f"{clone.get('name', 'Service discovery')} - BUSINESS {namespace}"
    clone["key"] = new_key
    lld_macro = _find_filter_macro(
        clone,
        ("{#SERVICE.NAME}", "{#SERVICE.DISPLAYNAME}"),
    ) or "{#SERVICE.NAME}"
    _set_business_filter(
        clone,
        lld_macro,
        "{$BUSINESS.SERVICE.MATCHES}",
        "{$BUSINESS.SERVICE.NOT_MATCHES}",
    )
    _namespace_item_prototype_keys(clone, namespace)
    _namespace_graph_prototype_names(clone, namespace)
    _rewrite_strings(clone, {old_key: new_key})
    return clone


def create_business_template(
    system: ZabbixTemplate,
    output_dir: Path,
    *,
    business_name: str,
    overwrite: bool = False,
    include_filesystems: bool = False,
    include_services: bool = False,
    business_tags: dict[str, str] | None = None,
    filesystem_matches: str | None = None,
    filesystem_not_matches: str | None = None,
    service_matches: str | None = None,
    service_not_matches: str | None = None,
) -> BusinessCreationResult:
    """Create one additional BUSINESS template without regenerating BASE/SYSTEM."""

    output_dir.mkdir(parents=True, exist_ok=True)
    system_name = str(system.template.get("template", "SYSTEM"))
    visible_name = str(system.template.get("name", system_name))
    suffix = _slug(business_name)
    namespace = _key_slug(business_name)
    root = system_name[:-7] if system_name.endswith("_SYSTEM") else system_name
    business_technical = f"{root}_{suffix}"
    business_file = output_dir / f"{business_technical}.yaml"
    if business_file.exists() and not overwrite:
        raise FileExistsError(f"Output file already exists: {business_file}")

    document = deepcopy(system.document)
    export = document["zabbix_export"]
    template = export["templates"][0]
    discovery_rules = template.get("discovery_rules", [])
    if not isinstance(discovery_rules, list):
        raise TemplateFormatError("'discovery_rules' must be a list when present.")
    source_valuemaps = template.get("valuemaps", [])

    selected: list[dict[str, Any]] = []
    fs_count = 0
    service_count = 0
    skipped_services = 0
    for rule in discovery_rules:
        if not isinstance(rule, dict):
            continue
        key = str(rule.get("key", ""))
        name = str(rule.get("name", "")).lower()
        if include_filesystems and ("vfs.fs" in key or "filesystem" in name):
            selected.append(_clone_filesystem_rule(rule, namespace))
            fs_count += 1
        elif include_services and ("service" in key or "service" in name):
            clone = _clone_service_rule(rule, namespace)
            if clone is None:
                skipped_services += 1
            else:
                selected.append(clone)
                service_count += 1

    required_valuemaps = _select_required_valuemaps(source_valuemaps, selected)

    template["template"] = business_technical
    template["name"] = f"{visible_name.removesuffix(' SYSTEM')} {business_name}"
    template["templates"] = [{"name": system_name}]
    for key in ("items", "triggers", "graphs", "valuemaps", "dashboards"):
        template.pop(key, None)
    template.pop("macros", None)
    template.pop("tags", None)

    if selected:
        template["discovery_rules"] = selected
    else:
        template.pop("discovery_rules", None)
    if required_valuemaps:
        template["valuemaps"] = required_valuemaps

    tags = _normalise_tags(business_tags)
    if tags:
        template["tags"] = tags
    macros = _business_macros(
        filesystem_matches,
        filesystem_not_matches,
        service_matches,
        service_not_matches,
    )
    if macros:
        template["macros"] = macros

    export.pop("triggers", None)
    export.pop("graphs", None)
    _rewrite_strings(document, {f"/{system_name}/": f"/{business_technical}/"})
    _rewrite_template_hosts(document, system_name, business_technical)
    _regenerate_uuids(document)

    generated = ZabbixTemplate.from_document(business_file, document)
    ensure_valid_template(generated)
    write_document(business_file, document)

    return BusinessCreationResult(
        file=business_file,
        template=business_technical,
        filesystem_rules=fs_count,
        service_rules=service_count,
        skipped_service_rules=skipped_services,
    )