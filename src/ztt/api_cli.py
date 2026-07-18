"""CLI extension exposing Zabbix API profile and export commands."""

from __future__ import annotations

import json
import os
from pathlib import Path
from time import perf_counter
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from ztt.cli import app
from ztt.loader import load_template
from ztt.profiles import ProfileError, default_config_path, get_profile, load_profiles
from ztt.template import TemplateFormatError
from ztt.zabbix_api import ConnectionDiagnostics, ZabbixAPIClient, ZabbixAPIError

console = Console()
api_app = typer.Typer(name="api", help="Connect to named Zabbix API environments.", no_args_is_help=True)
app.add_typer(api_app, name="api")


def _api_error(exc: Exception) -> None:
    console.print(f"[bold red]API error:[/bold red] {exc}")
    raise typer.Exit(code=1) from exc


def _safe_filename(value: str) -> str:
    cleaned = "_".join(value.strip().split())
    return cleaned.replace("/", "_").replace("\\", "_")


def _format_ms(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1f} ms"


def _format_size(size_bytes: int) -> str:
    size = float(size_bytes)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if size < 1024 or unit == "GiB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size_bytes} B"


def _ok(label: str, value: str | None = None, duration_ms: float | None = None) -> None:
    suffix = f" : {value}" if value else ""
    timing = f" [dim]({_format_ms(duration_ms)})[/dim]" if duration_ms is not None else ""
    console.print(f"  [bold green]✓[/bold green] {label}{suffix}{timing}")


def _warning(label: str) -> None:
    console.print(f"  [bold yellow]⚠[/bold yellow] {label}")


def _diagnostics_document(
    profile_name: str,
    environment: str,
    config_path: Path,
    diagnostics: ConnectionDiagnostics,
) -> dict[str, object]:
    return {
        "status": "ok",
        "profile": profile_name,
        "environment": environment,
        "configuration_file": str(config_path),
        "network": {
            "host": diagnostics.host,
            "port": diagnostics.port,
            "addresses": list(diagnostics.addresses),
            "dns_ms": round(diagnostics.timings.dns_ms, 3),
            "tcp_ms": round(diagnostics.timings.tcp_ms, 3),
        },
        "tls": {
            "enabled": diagnostics.tls_enabled,
            "verified": diagnostics.tls_verified,
            "protocol": diagnostics.tls_protocol,
            "duration_ms": (
                round(diagnostics.timings.tls_ms, 3)
                if diagnostics.timings.tls_ms is not None
                else None
            ),
        },
        "api": {
            "zabbix_version": diagnostics.zabbix_version,
            "template_count": diagnostics.template_count,
            "public_api_ms": round(diagnostics.timings.public_api_ms, 3),
            "authenticated_api_ms": round(diagnostics.timings.authenticated_api_ms, 3),
        },
        "total_ms": round(diagnostics.timings.total_ms, 3),
    }


@api_app.command("profiles")
def profiles(
    config: Annotated[
        Path | None,
        typer.Option(
            "--config",
            help="Profile configuration file. Defaults to ZTT_CONFIG or ~/.config/ztt/config.yaml.",
        ),
    ] = None,
) -> None:
    """List configured QUAL, PROD and other named Zabbix environments."""
    try:
        entries = load_profiles(config)
    except (FileNotFoundError, PermissionError, ProfileError) as exc:
        _api_error(exc)

    table = Table(title=f"Zabbix API profiles — {config or default_config_path()}")
    table.add_column("Profile")
    table.add_column("Environment")
    table.add_column("URL")
    table.add_column("TLS")
    table.add_column("Token variable")
    table.add_column("Token set")
    for profile in entries.values():
        environment = "PROD" if profile.production else "QUAL/OTHER"
        token_set = "yes" if os.environ.get(profile.token_env, "").strip() else "no"
        table.add_row(
            profile.name,
            environment,
            profile.url,
            "verify" if profile.verify_tls else "disabled",
            profile.token_env,
            token_set,
        )
    console.print(table)


@api_app.command("test")
def test(
    profile_name: Annotated[str, typer.Option("--profile", "-p", help="Named Zabbix profile.")],
    config: Annotated[Path | None, typer.Option("--config")] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Return machine-readable JSON instead of the formatted report."),
    ] = False,
) -> None:
    """Diagnose configuration, network, TLS and API-token access without changing Zabbix."""
    config_path = config or default_config_path()
    if not json_output:
        console.print("[bold]Configuration[/bold]")
    try:
        profile = get_profile(profile_name, config)
        token = profile.token()
    except (FileNotFoundError, PermissionError, ProfileError) as exc:
        _api_error(exc)

    if not json_output:
        _ok("Configuration file", str(config_path))
        _ok("Profile", profile.name)
        _ok("URL", profile.url)
        _ok("Token variable", profile.token_env)
        _ok("Token detected", f"{len(token)} characters")
        console.print("\n[bold]Network and API[/bold]")

    try:
        diagnostics = ZabbixAPIClient(profile, token).diagnose_connection()
    except ZabbixAPIError as exc:
        _api_error(exc)

    environment = "PRODUCTION" if profile.production else "QUALIFICATION/OTHER"
    if json_output:
        console.print_json(
            json.dumps(
                _diagnostics_document(profile.name, environment, config_path, diagnostics),
                ensure_ascii=False,
            )
        )
        return

    _ok("DNS resolution", ", ".join(diagnostics.addresses), diagnostics.timings.dns_ms)
    _ok(
        "TCP connection",
        f"{diagnostics.host}:{diagnostics.port}",
        diagnostics.timings.tcp_ms,
    )
    if diagnostics.tls_enabled:
        _ok("TLS negotiation", diagnostics.tls_protocol or "established", diagnostics.timings.tls_ms)
        if diagnostics.tls_verified:
            _ok("TLS certificate verification")
        else:
            _warning("TLS certificate verification disabled by profile")
    else:
        _warning("Unencrypted HTTP profile")
    _ok("HTTP and JSON-RPC response")
    _ok(
        "Public apiinfo.version",
        diagnostics.zabbix_version,
        diagnostics.timings.public_api_ms,
    )
    _ok(
        "Authenticated template.get",
        f"{diagnostics.template_count} template(s)",
        diagnostics.timings.authenticated_api_ms,
    )

    console.print(f"\n[bold green]Connection successful[/bold green] — {profile.name}")
    console.print(f"Environment : {environment}")
    console.print(f"Total time  : {_format_ms(diagnostics.timings.total_ms)}")


@api_app.command("list-templates")
def list_templates(
    profile_name: Annotated[str, typer.Option("--profile", "-p", help="Named Zabbix profile.")],
    search: Annotated[
        str | None,
        typer.Option("--search", "-s", help="Filter by technical or visible name."),
    ] = None,
    config: Annotated[Path | None, typer.Option("--config")] = None,
) -> None:
    """List templates available through a read-only template.get request."""
    try:
        profile = get_profile(profile_name, config)
        templates = ZabbixAPIClient.from_profile(profile).list_templates(search)
    except (FileNotFoundError, PermissionError, ProfileError, ZabbixAPIError) as exc:
        _api_error(exc)

    table = Table(title=f"Templates — {profile.name}")
    table.add_column("ID")
    table.add_column("Technical name")
    table.add_column("Visible name")
    for item in templates:
        table.add_row(item.templateid, item.host, item.name)
    console.print(table)
    console.print(f"{len(templates)} template(s).")


@api_app.command("export-template")
def export_template(
    profile_name: Annotated[str, typer.Option("--profile", "-p", help="Named Zabbix profile.")],
    template_name: Annotated[str, typer.Option("--template", "-t", help="Exact template name.")],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Destination YAML file."),
    ] = None,
    config: Annotated[Path | None, typer.Option("--config")] = None,
    overwrite: Annotated[bool, typer.Option("--overwrite")] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Return machine-readable JSON instead of the formatted report."),
    ] = False,
) -> None:
    """Export one template from Zabbix, validate it and save it as a YAML file."""
    destination = output or Path(f"{_safe_filename(template_name)}.yaml")
    if destination.exists() and not overwrite:
        _api_error(FileExistsError(f"Output file already exists: {destination}"))

    total_started = perf_counter()
    try:
        profile = get_profile(profile_name, config)

        api_started = perf_counter()
        document = ZabbixAPIClient.from_profile(profile).export_template(template_name)
        api_ms = (perf_counter() - api_started) * 1000

        write_started = perf_counter()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(document, encoding="utf-8")
        write_ms = (perf_counter() - write_started) * 1000

        validation_started = perf_counter()
        summary = load_template(destination).summary()
        validation_ms = (perf_counter() - validation_started) * 1000
    except (
        FileNotFoundError,
        PermissionError,
        ProfileError,
        TemplateFormatError,
        ZabbixAPIError,
        OSError,
    ) as exc:
        _api_error(exc)

    total_ms = (perf_counter() - total_started) * 1000
    size_bytes = destination.stat().st_size
    result = {
        "status": "ok",
        "profile": profile.name,
        "template": {
            "requested_name": template_name,
            "technical_name": summary.template_name,
            "visible_name": summary.visible_name,
            "export_version": summary.export_version,
            "items": summary.items,
            "discovery_rules": summary.discovery_rules,
            "triggers": summary.triggers,
            "graphs": summary.graphs,
            "dashboards": summary.dashboards,
            "macros": summary.macros,
        },
        "output": {
            "file": str(destination.resolve()),
            "size_bytes": size_bytes,
        },
        "timings_ms": {
            "api_export": round(api_ms, 3),
            "write": round(write_ms, 3),
            "validation": round(validation_ms, 3),
            "total": round(total_ms, 3),
        },
    }

    if json_output:
        console.print_json(json.dumps(result, ensure_ascii=False))
        return

    console.print("[bold]Template export[/bold]")
    _ok("API export", template_name, api_ms)
    _ok("File written", str(destination), write_ms)
    _ok("YAML validation", summary.template_name, validation_ms)
    console.print()
    console.print(f"Profile       : {profile.name}")
    console.print(f"Technical name: {summary.template_name}")
    console.print(f"Visible name  : {summary.visible_name}")
    console.print(f"Version       : {summary.export_version}")
    console.print(f"Objects       : {summary.items} items, {summary.discovery_rules} LLD, {summary.triggers} triggers")
    console.print(f"File          : {destination.resolve()}")
    console.print(f"Size          : {_format_size(size_bytes)}")
    console.print(f"Total time    : {_format_ms(total_ms)}")


if __name__ == "__main__":
    app()
