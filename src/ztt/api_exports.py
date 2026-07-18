"""Additional Zabbix API export commands for hosts and groups."""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter
from typing import Annotated, Any

import typer
from ruamel.yaml import YAML

from ztt.api_cli import (
    _api_error,
    _format_ms,
    _format_size,
    _ok,
    _safe_filename,
    api_app,
    app,
    console,
)
from ztt.profiles import ProfileError, get_profile
from ztt.zabbix_api import ZabbixAPIClient, ZabbixAPIError


def _validate_export(document: str, expected_key: str) -> int:
    """Validate the basic structure of a serialized Zabbix YAML export."""
    try:
        parsed = YAML(typ="safe").load(document)
    except Exception as exc:  # ruamel exposes several parser exception classes
        raise ZabbixAPIError(f"Exported YAML is invalid: {exc}") from exc

    if not isinstance(parsed, dict):
        raise ZabbixAPIError("Exported YAML does not contain a mapping at its root.")
    export = parsed.get("zabbix_export")
    if not isinstance(export, dict):
        raise ZabbixAPIError("Exported YAML does not contain a zabbix_export section.")
    objects = export.get(expected_key)
    if not isinstance(objects, list) or not objects:
        raise ZabbixAPIError(
            f"Exported YAML does not contain a non-empty '{expected_key}' section."
        )
    return len(objects)


def _resolve_host(client: ZabbixAPIClient, name: str) -> tuple[str, str, str]:
    result = client.call(
        "host.get",
        {
            "output": ["hostid", "host", "name"],
            "search": {"host": name, "name": name},
            "searchByAny": True,
        },
    )
    if not isinstance(result, list):
        raise ZabbixAPIError("host.get returned an invalid value.")

    matches = [
        item
        for item in result
        if isinstance(item, dict) and name in {str(item.get("host", "")), str(item.get("name", ""))}
    ]
    if not matches:
        raise ZabbixAPIError(f"Host '{name}' was not found.")
    if len(matches) > 1:
        details = ", ".join(
            f"{item.get('host', '')} ({item.get('hostid', '')})" for item in matches
        )
        raise ZabbixAPIError(f"Host name '{name}' is ambiguous: {details}")

    item = matches[0]
    return str(item.get("hostid", "")), str(item.get("host", "")), str(item.get("name", ""))


def _resolve_group(
    client: ZabbixAPIClient,
    method: str,
    object_label: str,
    name: str,
) -> tuple[str, str]:
    result = client.call(
        method,
        {
            "output": ["groupid", "name"],
            "filter": {"name": [name]},
        },
    )
    if not isinstance(result, list):
        raise ZabbixAPIError(f"{method} returned an invalid value.")
    matches = [item for item in result if isinstance(item, dict) and str(item.get("name", "")) == name]
    if not matches:
        raise ZabbixAPIError(f"{object_label} '{name}' was not found.")
    if len(matches) > 1:
        details = ", ".join(str(item.get("groupid", "")) for item in matches)
        raise ZabbixAPIError(f"{object_label} name '{name}' is ambiguous: {details}")

    item = matches[0]
    return str(item.get("groupid", "")), str(item.get("name", ""))


def _export_configuration(client: ZabbixAPIClient, option_name: str, object_id: str) -> str:
    result = client.call(
        "configuration.export",
        {
            "format": "yaml",
            "options": {option_name: [object_id]},
        },
    )
    if not isinstance(result, str) or not result.strip():
        raise ZabbixAPIError("configuration.export returned an empty or invalid document.")
    return result


def _run_export(
    *,
    profile_name: str,
    config: Path | None,
    destination: Path,
    overwrite: bool,
    json_output: bool,
    object_type: str,
    requested_name: str,
    resolve: Any,
    option_name: str,
    expected_key: str,
) -> None:
    if destination.exists() and not overwrite:
        _api_error(FileExistsError(f"Output file already exists: {destination}"))

    total_started = perf_counter()
    try:
        profile = get_profile(profile_name, config)
        client = ZabbixAPIClient.from_profile(profile)

        resolve_started = perf_counter()
        object_id, technical_name, visible_name = resolve(client)
        resolve_ms = (perf_counter() - resolve_started) * 1000

        export_started = perf_counter()
        document = _export_configuration(client, option_name, object_id)
        export_ms = (perf_counter() - export_started) * 1000

        validation_started = perf_counter()
        object_count = _validate_export(document, expected_key)
        validation_ms = (perf_counter() - validation_started) * 1000

        write_started = perf_counter()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(document, encoding="utf-8")
        write_ms = (perf_counter() - write_started) * 1000
    except (
        FileNotFoundError,
        PermissionError,
        ProfileError,
        ZabbixAPIError,
        OSError,
    ) as exc:
        _api_error(exc)

    total_ms = (perf_counter() - total_started) * 1000
    size_bytes = destination.stat().st_size
    result = {
        "status": "ok",
        "profile": profile.name,
        "object": {
            "type": object_type,
            "id": object_id,
            "requested_name": requested_name,
            "technical_name": technical_name,
            "visible_name": visible_name,
            "exported_objects": object_count,
        },
        "output": {
            "file": str(destination.resolve()),
            "size_bytes": size_bytes,
        },
        "timings_ms": {
            "resolve": round(resolve_ms, 3),
            "api_export": round(export_ms, 3),
            "validation": round(validation_ms, 3),
            "write": round(write_ms, 3),
            "total": round(total_ms, 3),
        },
    }

    if json_output:
        console.print_json(json.dumps(result, ensure_ascii=False))
        return

    console.print(f"[bold]{object_type} export[/bold]")
    _ok("Object resolved", f"{technical_name} ({object_id})", resolve_ms)
    _ok("API export", requested_name, export_ms)
    _ok("YAML validation", f"{object_count} object(s)", validation_ms)
    _ok("File written", str(destination), write_ms)
    console.print()
    console.print(f"Profile       : {profile.name}")
    console.print(f"Object type   : {object_type}")
    console.print(f"Object ID     : {object_id}")
    console.print(f"Technical name: {technical_name}")
    console.print(f"Visible name  : {visible_name}")
    console.print(f"File          : {destination.resolve()}")
    console.print(f"Size          : {_format_size(size_bytes)}")
    console.print(f"Total time    : {_format_ms(total_ms)}")


@api_app.command("export-host")
def export_host(
    profile_name: Annotated[str, typer.Option("--profile", "-p", help="Named Zabbix profile.")],
    host_name: Annotated[str, typer.Option("--host", "-H", help="Exact technical or visible host name.")],
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Destination YAML file.")] = None,
    config: Annotated[Path | None, typer.Option("--config")] = None,
    overwrite: Annotated[bool, typer.Option("--overwrite")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Return machine-readable JSON.")] = False,
) -> None:
    """Export one host from Zabbix as a YAML file."""
    destination = output or Path(f"{_safe_filename(host_name)}.yaml")
    _run_export(
        profile_name=profile_name,
        config=config,
        destination=destination,
        overwrite=overwrite,
        json_output=json_output,
        object_type="Host",
        requested_name=host_name,
        resolve=lambda client: _resolve_host(client, host_name),
        option_name="hosts",
        expected_key="hosts",
    )


@api_app.command("export-host-group")
def export_host_group(
    profile_name: Annotated[str, typer.Option("--profile", "-p", help="Named Zabbix profile.")],
    group_name: Annotated[str, typer.Option("--group", "-g", help="Exact host group name.")],
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Destination YAML file.")] = None,
    config: Annotated[Path | None, typer.Option("--config")] = None,
    overwrite: Annotated[bool, typer.Option("--overwrite")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Return machine-readable JSON.")] = False,
) -> None:
    """Export one host group from Zabbix as a YAML file."""
    destination = output or Path(f"host-group_{_safe_filename(group_name)}.yaml")
    _run_export(
        profile_name=profile_name,
        config=config,
        destination=destination,
        overwrite=overwrite,
        json_output=json_output,
        object_type="Host group",
        requested_name=group_name,
        resolve=lambda client: (
            lambda result: (result[0], result[1], result[1])
        )(_resolve_group(client, "hostgroup.get", "Host group", group_name)),
        option_name="host_groups",
        expected_key="host_groups",
    )


@api_app.command("export-template-group")
def export_template_group(
    profile_name: Annotated[str, typer.Option("--profile", "-p", help="Named Zabbix profile.")],
    group_name: Annotated[str, typer.Option("--group", "-g", help="Exact template group name.")],
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Destination YAML file.")] = None,
    config: Annotated[Path | None, typer.Option("--config")] = None,
    overwrite: Annotated[bool, typer.Option("--overwrite")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Return machine-readable JSON.")] = False,
) -> None:
    """Export one template group from Zabbix as a YAML file."""
    destination = output or Path(f"template-group_{_safe_filename(group_name)}.yaml")
    _run_export(
        profile_name=profile_name,
        config=config,
        destination=destination,
        overwrite=overwrite,
        json_output=json_output,
        object_type="Template group",
        requested_name=group_name,
        resolve=lambda client: (
            lambda result: (result[0], result[1], result[1])
        )(_resolve_group(client, "templategroup.get", "Template group", group_name)),
        option_name="template_groups",
        expected_key="template_groups",
    )


if __name__ == "__main__":
    app()
