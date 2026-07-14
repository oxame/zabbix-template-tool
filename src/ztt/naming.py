"""Rename generated templates while keeping filesystem-safe YAML filenames."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ztt.business import BusinessCreationResult
from ztt.layers import LayerCreationResult
from ztt.loader import load_template
from ztt.writer import write_document


def _file_slug(value: str) -> str:
    cleaned = "_".join(value.strip().split())
    return cleaned.replace("/", "_").replace("\\", "_")


def _rewrite_references(value: Any, replacements: dict[str, str]) -> None:
    ordered = sorted(replacements.items(), key=lambda entry: len(entry[0]), reverse=True)
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(child, str):
                if child in replacements:
                    value[key] = replacements[child]
                    continue
                updated = child
                for old, new in ordered:
                    updated = updated.replace(f"/{old}/", f"/{new}/")
                value[key] = updated
            else:
                _rewrite_references(child, replacements)
    elif isinstance(value, list):
        for child in value:
            _rewrite_references(child, replacements)


def _write_renamed(
    path: Path,
    document: dict[str, Any],
    template_name: str,
    overwrite: bool,
) -> Path:
    target = path.with_name(f"{_file_slug(template_name)}.yaml")
    if target != path and target.exists() and not overwrite:
        raise FileExistsError(f"Output file already exists: {target}")
    write_document(target, document)
    if target != path and path.exists():
        path.unlink()
    return target


def rename_layered_templates(
    result: LayerCreationResult,
    *,
    base_name: str,
    system_name: str,
    business_name: str,
    overwrite: bool = False,
) -> LayerCreationResult:
    """Rename all three generated layers and their internal references."""

    names = (base_name.strip(), system_name.strip(), business_name.strip())
    if any(not name for name in names):
        raise ValueError("Generated template names cannot be empty.")
    if len(set(names)) != 3:
        raise ValueError("BASE, SYSTEM and BUSINESS template names must be different.")

    replacements = {
        result.base_template: names[0],
        result.system_template: names[1],
        result.business_template: names[2],
    }
    paths: list[Path] = []
    for source_path, new_name in (
        (result.base_file, names[0]),
        (result.system_file, names[1]),
        (result.business_file, names[2]),
    ):
        loaded = load_template(source_path)
        document = loaded.document
        _rewrite_references(document, replacements)
        template = document["zabbix_export"]["templates"][0]
        template["template"] = new_name
        template["name"] = new_name
        paths.append(_write_renamed(source_path, document, new_name, overwrite))

    return LayerCreationResult(
        base_file=paths[0],
        system_file=paths[1],
        business_file=paths[2],
        base_template=names[0],
        system_template=names[1],
        business_template=names[2],
        discovery_rules=result.discovery_rules,
        dashboards=result.dashboards,
    )


def rename_business_template(
    result: BusinessCreationResult,
    *,
    template_name: str,
    overwrite: bool = False,
) -> BusinessCreationResult:
    """Rename one generated BUSINESS template and its owned object references."""

    new_name = template_name.strip()
    if not new_name:
        raise ValueError("The BUSINESS template name cannot be empty.")
    loaded = load_template(result.file)
    document = loaded.document
    _rewrite_references(document, {result.template: new_name})
    template = document["zabbix_export"]["templates"][0]
    template["template"] = new_name
    template["name"] = new_name
    target = _write_renamed(result.file, document, new_name, overwrite)
    return BusinessCreationResult(
        file=target,
        template=new_name,
        filesystem_rules=result.filesystem_rules,
        service_rules=result.service_rules,
        skipped_service_rules=result.skipped_service_rules,
    )
