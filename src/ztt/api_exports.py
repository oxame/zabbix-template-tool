"""Zabbix API export commands backed by the shared export service."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Callable

import typer

from ztt.api_cli import _api_error, _safe_filename, api_app, app, console
from ztt.export_models import ExportResult
from ztt.export_render import render_export
from ztt.export_service import ExportService
from ztt.profiles import ProfileError
from ztt.zabbix_api import ZabbixAPIError

ExportOperation = Callable[[ExportService, str, Path, bool], ExportResult]


def _run_export_command(
    *,
    profile_name: str,
    config: Path | None,
    name: str,
    destination: Path,
    overwrite: bool,
    json_output: bool,
    operation: ExportOperation,
) -> None:
    try:
        service = ExportService(profile_name, config)
        result = operation(service, name, destination, overwrite)
    except (
        FileNotFoundError,
        FileExistsError,
        PermissionError,
        ProfileError,
        ZabbixAPIError,
        OSError,
        ValueError,
    ) as exc:
        _api_error(exc)

    render_export(result, console, json_output=json_output)


def _export_template(
    service: ExportService,
    name: str,
    destination: Path,
    overwrite: bool,
) -> ExportResult:
    return service.export_template(name, destination, overwrite=overwrite)


def _export_host(
    service: ExportService,
    name: str,
    destination: Path,
    overwrite: bool,
) -> ExportResult:
    return service.export_host(name, destination, overwrite=overwrite)


def _export_host_group(
    service: ExportService,
    name: str,
    destination: Path,
    overwrite: bool,
) -> ExportResult:
    return service.export_host_group(name, destination, overwrite=overwrite)


def _export_template_group(
    service: ExportService,
    name: str,
    destination: Path,
    overwrite: bool,
) -> ExportResult:
    return service.export_template_group(name, destination, overwrite=overwrite)


@api_app.command("export-template")
def export_template(
    profile_name: Annotated[str, typer.Option("--profile", "-p", help="Named Zabbix profile.")],
    template_name: Annotated[str, typer.Option("--template", "-t", help="Exact template name.")],
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Destination YAML file.")] = None,
    config: Annotated[Path | None, typer.Option("--config")] = None,
    overwrite: Annotated[bool, typer.Option("--overwrite")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Return machine-readable JSON.")] = False,
) -> None:
    """Export one template from Zabbix as a validated YAML file."""
    _run_export_command(
        profile_name=profile_name,
        config=config,
        name=template_name,
        destination=output or Path(f"{_safe_filename(template_name)}.yaml"),
        overwrite=overwrite,
        json_output=json_output,
        operation=_export_template,
    )


@api_app.command("export-host")
def export_host(
    profile_name: Annotated[str, typer.Option("--profile", "-p", help="Named Zabbix profile.")],
    host_name: Annotated[str, typer.Option("--host", "-H", help="Exact technical or visible host name.")],
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Destination YAML file.")] = None,
    config: Annotated[Path | None, typer.Option("--config")] = None,
    overwrite: Annotated[bool, typer.Option("--overwrite")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Return machine-readable JSON.")] = False,
) -> None:
    """Export one host from Zabbix as a validated YAML file."""
    _run_export_command(
        profile_name=profile_name,
        config=config,
        name=host_name,
        destination=output or Path(f"{_safe_filename(host_name)}.yaml"),
        overwrite=overwrite,
        json_output=json_output,
        operation=_export_host,
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
    """Export one host group from Zabbix as a validated YAML file."""
    _run_export_command(
        profile_name=profile_name,
        config=config,
        name=group_name,
        destination=output or Path(f"host-group_{_safe_filename(group_name)}.yaml"),
        overwrite=overwrite,
        json_output=json_output,
        operation=_export_host_group,
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
    """Export one template group from Zabbix as a validated YAML file."""
    _run_export_command(
        profile_name=profile_name,
        config=config,
        name=group_name,
        destination=output or Path(f"template-group_{_safe_filename(group_name)}.yaml"),
        overwrite=overwrite,
        json_output=json_output,
        operation=_export_template_group,
    )


if __name__ == "__main__":
    app()
