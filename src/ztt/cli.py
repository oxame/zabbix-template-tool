"""Command-line interface for Zabbix Template Tool."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from ztt import __version__
from ztt.dependencies import analyze_lld_dependencies
from ztt.layers import create_layered_templates
from ztt.lld import list_discovery_rules, move_discovery_rules
from ztt.loader import load_template
from ztt.template import TemplateFormatError

app = typer.Typer(
    name="ztt",
    help="Inspect and refactor Zabbix YAML templates.",
    no_args_is_help=True,
)
console = Console()


def version_callback(value: bool) -> None:
    if value:
        console.print(f"ztt {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=version_callback,
            is_eager=True,
            help="Show version.",
        ),
    ] = False,
) -> None:
    """Zabbix Template Tool."""


def _parse_tags(value: str) -> dict[str, str]:
    tags: dict[str, str] = {}
    for entry in value.split(","):
        entry = entry.strip()
        if not entry:
            continue
        if "=" not in entry:
            raise ValueError(f"Invalid tag '{entry}'. Expected name=value.")
        name, tag_value = entry.split("=", 1)
        name = name.strip()
        if not name:
            raise ValueError("Tag name cannot be empty.")
        tags[name] = tag_value.strip()
    return tags


@app.command("info")
def info(
    template_file: Annotated[
        Path,
        typer.Argument(exists=False, dir_okay=False, readable=True, help="Zabbix YAML export."),
    ],
) -> None:
    """Display a summary of the first template contained in a YAML export."""
    try:
        summary = load_template(template_file).summary()
    except (FileNotFoundError, PermissionError, TemplateFormatError) as exc:
        _exit_with_error(exc)

    metadata = Table(show_header=False, box=None)
    metadata.add_row("File", str(summary.file))
    metadata.add_row("Export version", summary.export_version)
    metadata.add_row("Template", summary.template_name)
    metadata.add_row("Visible name", summary.visible_name)
    console.print(metadata)

    counts = Table(title="Objects")
    counts.add_column("Type")
    counts.add_column("Count", justify="right")
    counts.add_row("Items", str(summary.items))
    counts.add_row("Discovery rules (LLD)", str(summary.discovery_rules))
    counts.add_row("Triggers", str(summary.triggers))
    counts.add_row("Graphs", str(summary.graphs))
    counts.add_row("Dashboards", str(summary.dashboards))
    counts.add_row("Macros", str(summary.macros))
    console.print(counts)


@app.command("list-lld")
def list_lld(
    template_file: Annotated[
        Path,
        typer.Argument(exists=False, dir_okay=False, readable=True, help="Zabbix YAML export."),
    ],
) -> None:
    """List low-level discovery rules and their nested prototype counts."""
    try:
        template = load_template(template_file)
        rules = list_discovery_rules(template)
    except (FileNotFoundError, PermissionError, TemplateFormatError) as exc:
        _exit_with_error(exc)

    title = template.template.get("name", template.path.name)
    table = Table(title=f"LLD rules — {title}")
    for column in ("#", "Name", "Key", "Items", "Triggers", "Graphs", "Overrides"):
        table.add_column(column)
    for rule in rules:
        table.add_row(
            str(rule.index),
            rule.name,
            rule.key,
            str(rule.item_prototypes),
            str(rule.trigger_prototypes),
            str(rule.graph_prototypes),
            str(rule.overrides),
        )
    console.print(table)
    if not rules:
        console.print("[yellow]No discovery rule found.[/yellow]")


@app.command("analyze")
def analyze(
    template_file: Annotated[
        Path,
        typer.Argument(exists=False, dir_okay=False, readable=True, help="Zabbix YAML export."),
    ],
) -> None:
    """Analyze external dependencies referenced by discovery rules."""
    try:
        reports = analyze_lld_dependencies(load_template(template_file))
    except (FileNotFoundError, PermissionError, TemplateFormatError) as exc:
        _exit_with_error(exc)

    for report in reports:
        table = Table(title=f"{report.rule_name} — {report.rule_key}")
        for column in ("Status", "Type", "Reference", "Location"):
            table.add_column(column)
        for dependency in report.dependencies:
            status = "[green]OK[/green]" if dependency.present else "[red]MISSING[/red]"
            table.add_row(status, dependency.kind, dependency.reference, dependency.location)
        console.print(table)
        if not report.dependencies:
            console.print("[dim]No external dependency detected.[/dim]")
    if not reports:
        console.print("[yellow]No discovery rule found.[/yellow]")


@app.command("create-layers")
def create_layers(
    source_file: Annotated[
        Path,
        typer.Argument(exists=False, dir_okay=False, readable=True, help="Existing Zabbix YAML template export."),
    ],
    output_dir: Annotated[
        Path | None,
        typer.Option("--output-dir", "-o", help="Generated-file directory; defaults beside source."),
    ] = None,
    prefix: Annotated[
        str | None,
        typer.Option("--prefix", help="Technical-name prefix for generated templates."),
    ] = None,
    business_name: Annotated[
        str | None,
        typer.Option("--business-name", help="Business layer name, e.g. Oracle, SQL or Liaison."),
    ] = None,
    interactive: Annotated[
        bool,
        typer.Option("--interactive/--no-interactive", help="Ask for BUSINESS macros and tags."),
    ] = False,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Replace existing generated files."),
    ] = False,
) -> None:
    """Create linked BASE, SYSTEM and configurable BUSINESS templates."""
    try:
        source = load_template(source_file)
        destination = output_dir if output_dir is not None else source.path.parent

        fs_matches: str | None = None
        fs_not_matches: str | None = None
        service_matches: str | None = None
        service_not_matches: str | None = None
        system_tags: dict[str, str] = {"layer": "system"}
        business_tags: dict[str, str] = {"layer": "business"}

        if interactive:
            business_name = typer.prompt("Nom du template BUSINESS", default=business_name or "BUSINESS")
            if typer.confirm("Renseigner les macros Filesystem métier ?", default=False):
                fs_matches = typer.prompt("{$BUSINESS.FS.MATCHES}", default=".*")
                fs_not_matches = typer.prompt("{$BUSINESS.FS.NOT_MATCHES}", default="")
            if typer.confirm("Renseigner les macros Services métier ?", default=False):
                service_matches = typer.prompt("{$BUSINESS.SERVICE.MATCHES}", default=".*")
                service_not_matches = typer.prompt("{$BUSINESS.SERVICE.NOT_MATCHES}", default="")
            system_tags = _parse_tags(
                typer.prompt("Tags SYSTEM (nom=valeur, séparés par des virgules)", default="layer=system")
            )
            default_business_tags = f"layer=business,application={business_name.lower()}"
            business_tags = _parse_tags(
                typer.prompt(
                    "Tags BUSINESS (nom=valeur, séparés par des virgules)",
                    default=default_business_tags,
                )
            )
        else:
            business_name = business_name or "BUSINESS"

        result = create_layered_templates(
            source,
            destination,
            prefix=prefix,
            overwrite=overwrite,
            business_name=business_name,
            system_tags=system_tags,
            business_tags=business_tags,
            filesystem_matches=fs_matches,
            filesystem_not_matches=fs_not_matches,
            service_matches=service_matches,
            service_not_matches=service_not_matches,
        )
    except (
        FileNotFoundError,
        FileExistsError,
        PermissionError,
        TemplateFormatError,
        ValueError,
    ) as exc:
        _exit_with_error(exc)

    console.print("[bold green]Layered templates created.[/bold green]")
    console.print(f"BASE     : {result.base_file} ({result.base_template})")
    console.print(f"SYSTEM   : {result.system_file} ({result.system_template})")
    console.print(f"BUSINESS : {result.business_file} ({result.business_template})")
    console.print(f"LLD rules transferred to SYSTEM: {result.discovery_rules}")
    console.print(f"[yellow]Dashboards skipped temporarily: {result.dashboards}[/yellow]")
    console.print("Business discovery macros are prepared; LLD cloning is not enabled yet.")
    console.print("Import order: BASE, SYSTEM, then BUSINESS.")
    console.print("The source YAML file was not modified.")


@app.command("move-lld")
def move_lld(
    source_file: Annotated[
        Path,
        typer.Argument(exists=False, dir_okay=False, readable=True),
    ],
    destination_file: Annotated[
        Path,
        typer.Argument(exists=False, dir_okay=False, readable=True),
    ],
    select: Annotated[
        list[str] | None,
        typer.Option("--select", "-s", help="Exact LLD name, key, or UUID."),
    ] = None,
    move_all: Annotated[
        bool,
        typer.Option("--all", help="Move every LLD rule from the source."),
    ] = False,
    apply: Annotated[
        bool,
        typer.Option("--apply", help="Write changes; otherwise only simulate."),
    ] = False,
    backup: Annotated[
        bool,
        typer.Option("--backup/--no-backup", help="Create .bak copies before writing."),
    ] = True,
) -> None:
    """Move complete LLD rule blocks from one template export to another."""
    try:
        result = move_discovery_rules(
            load_template(source_file),
            load_template(destination_file),
            selectors=select,
            move_all=move_all,
            dry_run=not apply,
            backup=backup,
        )
    except (FileNotFoundError, PermissionError, TemplateFormatError) as exc:
        _exit_with_error(exc)

    mode = "Simulation" if result.dry_run else "Applied"
    console.print(f"[bold]{mode}:[/bold] {len(result.moved)} LLD rule(s)")
    for rule in result.moved:
        console.print(f"  • {rule.name} [dim]({rule.key})[/dim]")
    console.print(f"Source rules remaining: {result.source_remaining}")
    console.print(f"Destination rules after move: {result.destination_total}")
    if result.dry_run:
        console.print("[yellow]No file changed. Add --apply to perform the move.[/yellow]")


def _exit_with_error(exc: Exception) -> None:
    console.print(f"[bold red]Error:[/bold red] {exc}")
    raise typer.Exit(code=1) from exc


if __name__ == "__main__":
    app()
