"""CLI command for safe template promotion between Zabbix profiles."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Annotated

import typer

from ztt.api_cli import _api_error, api_app, console
from ztt.profiles import ProfileError
from ztt.promotion_service import PromotionService
from ztt.zabbix_api import ZabbixAPIError


@api_app.command("promote-template")
def promote_template(
    source_profile: Annotated[
        str,
        typer.Option("--source", "-s", help="Source Zabbix profile, for example QUAL."),
    ],
    target_profile: Annotated[
        str,
        typer.Option("--target", "-d", help="Target Zabbix profile, for example PROD."),
    ],
    template_name: Annotated[
        str,
        typer.Option("--template", "-t", help="Exact template name to promote."),
    ],
    backup_dir: Annotated[
        Path,
        typer.Option(
            "--backup-dir",
            help="Directory used for PROD backups, metadata and promotion history.",
        ),
    ] = Path("backups"),
    config: Annotated[Path | None, typer.Option("--config")] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Return machine-readable JSON."),
    ] = False,
) -> None:
    """Copy a template from source to target after backing up the target version."""
    try:
        result = PromotionService(source_profile, target_profile, config).promote_template(
            template_name,
            backup_dir,
        )
    except (
        FileNotFoundError,
        PermissionError,
        ProfileError,
        ZabbixAPIError,
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        _api_error(exc)

    document = asdict(result)
    for key in ("backup_file", "metadata_file", "history_file"):
        value = document[key]
        document[key] = str(value) if value is not None else None

    if json_output:
        console.print_json(json.dumps(document, ensure_ascii=False))
        return

    console.print("[bold green]Template promotion successful[/bold green]")
    console.print(f"Template : {result.template}")
    console.print(f"Source   : {result.source_profile}")
    console.print(f"Target   : {result.target_profile}")
    console.print(f"Existing : {'yes' if result.target_existed else 'no'}")
    if result.backup_file is not None:
        console.print(f"Backup   : {result.backup_file}")
        console.print(f"Metadata : {result.metadata_file}")
    else:
        console.print("Backup   : not required (template absent on target)")
    console.print(f"History  : {result.history_file}")
    console.print(f"Version  : {result.source_export_version or 'unknown'}")
    console.print(f"SHA-256  : {result.source_sha256}")
    console.print(f"Duration : {result.duration_seconds:.2f} s")
