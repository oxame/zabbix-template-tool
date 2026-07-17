"""CLI extension exposing Zabbix API profile commands."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from ztt.cli import app
from ztt.profiles import ProfileError, default_config_path, get_profile, load_profiles
from ztt.zabbix_api import ZabbixAPIClient, ZabbixAPIError

console = Console()
api_app = typer.Typer(name="api", help="Connect to named Zabbix API environments.", no_args_is_help=True)
app.add_typer(api_app, name="api")


def _api_error(exc: Exception) -> None:
    console.print(f"[bold red]API error:[/bold red] {exc}")
    raise typer.Exit(code=1) from exc


def _config_option() -> Path | None:
    return None


@api_app.command("profiles")
def profiles(
    config: Annotated[
        Path | None,
        typer.Option("--config", help="Profile configuration file. Defaults to ZTT_CONFIG or ~/.config/ztt/config.yaml."),
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
) -> None:
    """Test URL, TLS and API-token access without changing Zabbix."""

    try:
        profile = get_profile(profile_name, config)
        client = ZabbixAPIClient.from_profile(profile)
        version, template_count = client.test_connection()
    except (FileNotFoundError, PermissionError, ProfileError, ZabbixAPIError) as exc:
        _api_error(exc)

    environment = "PRODUCTION" if profile.production else "QUALIFICATION/OTHER"
    console.print(f"[bold green]Connection successful[/bold green] — {profile.name}")
    console.print(f"Environment : {environment}")
    console.print(f"URL         : {profile.url}")
    console.print(f"Zabbix      : {version}")
    console.print(f"Templates   : {template_count}")
    if profile.production:
        console.print("[yellow]Production profile: API write operations will require explicit confirmation.[/yellow]")


@api_app.command("list-templates")
def list_templates(
    profile_name: Annotated[str, typer.Option("--profile", "-p", help="Named Zabbix profile.")],
    search: Annotated[str | None, typer.Option("--search", "-s", help="Filter by technical or visible name.")] = None,
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
