"""Command-line interface for Zabbix Template Tool."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from ztt import __version__
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
        typer.Option("--version", callback=version_callback, is_eager=True, help="Show version."),
    ] = False,
) -> None:
    """Zabbix Template Tool."""


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
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

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


if __name__ == "__main__":
    app()
