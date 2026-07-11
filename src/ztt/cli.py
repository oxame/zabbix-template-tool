"""Command-line interface for Zabbix Template Tool."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from ztt import __version__
from ztt.dependencies import analyze_lld_dependencies
from ztt.layers import create_base_system_layers
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


@app.command("info")
def info(
    template_file: Annotated[
        Path,
        typer.Argument(
            exists=False,
            dir_okay=False,
            readable=True,
            help="Zabbix YAML export.",
        ),
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
        typer.Argument(
            exists=False,
            dir_okay=False,
            readable=True,
            help="Zabbix YAML export.",
        ),
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
        typer.Argument(
            exists=False,
            dir_okay=False,
            readable=True,
            help="Zabbix YAML export.",
        ),
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
            table.add_row(
                status,
                dependency.kind,
                dependency.reference,
                dependency.location,
            )
        console.print(table)
        if not report.dependencies:
            console.print("[dim]No external dependency detected.[/dim]")
    if not reports:
        console.print("[yellow]No discovery rule found.[/yellow]")


@app.command("create-layers")
def create_layers(
    source_file: Annotated[
        Path,
        typer.Argument(
            exists=False,
            dir_okay=False,
            readable=True,
            help="Existing Zabbix YAML template export.",
        ),
    ],
    output_dir: Annotated[
        Path | None,
        typer.Option(
            "--output-dir",
            "-o",
            help="Directory for generated files. Defaults to the source file directory.",
        ),
    ] = None,
    prefix: Annotated[
        str | None,
        typer.Option("--prefix", help="Technical-name prefix for generated templates."),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Replace existing generated files."),
    ] = False,
) -> None:
    """Create linked BASE and SYSTEM templates from an existing export."""
    try:
        source = load_template(source_file)
        destination = output_dir if output_dir is not None else source.path.parent
        result = create_base_system_layers(
            source,
            destination,
            prefix=prefix,
            overwrite=overwrite,
        )
    except (FileNotFoundError, FileExistsError, PermissionError, TemplateFormatError) as exc:
        _exit_with_error(exc)

    console.print("[bold green]Layered templates created.[/bold green]")
    console.print(f"BASE   : {result.base_file} ({result.base_template})")
    console.print(f"SYSTEM : {result.system_file} ({result.system_template})")
    console.print(f"LLD rules transferred to SYSTEM: {result.discovery_rules}")
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
