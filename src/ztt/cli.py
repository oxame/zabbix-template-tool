"""Command-line interface for Zabbix Template Tool."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from ztt import __version__
from ztt.business import create_business_template
from ztt.dependencies import analyze_lld_dependencies
from ztt.layers import create_layered_templates
from ztt.lld import list_discovery_rules, move_discovery_rules
from ztt.loader import load_template
from ztt.merge import merge_templates
from ztt.naming import rename_business_template, rename_layered_templates
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


def _parse_tags(value: str) -> dict[str, str]:
    tags: dict[str, str] = {}
    for entry in value.split(","):
        entry = entry.strip()
        if not entry:
            continue
        if "=" not in entry:
            raise ValueError(f"Invalid tag '{entry}'. Expected name=value.")
        name, tag_value = entry.split("=", 1)
        if not name.strip():
            raise ValueError("Tag name cannot be empty.")
        tags[name.strip()] = tag_value.strip()
    return tags


@app.command("info")
def info(
    template_file: Annotated[
        Path,
        typer.Argument(exists=False, dir_okay=False, readable=True, help="Zabbix YAML export."),
    ],
) -> None:
    """Display a summary of the first template in a YAML export."""
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
    """List low-level discovery rules and nested prototype counts."""
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
    source_file: Annotated[Path, typer.Argument(exists=False, dir_okay=False, readable=True)],
    output_dir: Annotated[Path | None, typer.Option("--output-dir", "-o")] = None,
    prefix: Annotated[str | None, typer.Option("--prefix")] = None,
    template_name: Annotated[str | None, typer.Option("--template-name")] = None,
    base_name: Annotated[str | None, typer.Option("--base-name")] = None,
    system_name: Annotated[str | None, typer.Option("--system-name")] = None,
    business_name: Annotated[str | None, typer.Option("--business-name")] = None,
    business_template_name: Annotated[
        str | None,
        typer.Option("--business-template-name"),
    ] = None,
    interactive: Annotated[bool, typer.Option("--interactive/--no-interactive")] = False,
    overwrite: Annotated[bool, typer.Option("--overwrite")] = False,
) -> None:
    """Create linked BASE, SYSTEM and configurable BUSINESS templates."""
    try:
        source = load_template(source_file)
        destination = output_dir if output_dir is not None else source.path.parent
        fs_matches = fs_not_matches = service_matches = service_not_matches = None
        system_tags = {"layer": "system"}
        business_tags = {"layer": "business"}
        original_name = str(source.template.get("name", source.template.get("template", "TEMPLATE")))
        root_name = template_name or original_name

        if interactive:
            root_name = typer.prompt("Nom racine des nouveaux templates", default=root_name)
            business_name = typer.prompt(
                "Libellé de la couche BUSINESS",
                default=business_name or "BUSINESS",
            )
            base_name = typer.prompt(
                "Nom complet du template BASE",
                default=base_name or f"{root_name} BASE",
            )
            system_name = typer.prompt(
                "Nom complet du template SYSTEM",
                default=system_name or f"{root_name} SYSTEM",
            )
            business_template_name = typer.prompt(
                "Nom complet du template BUSINESS",
                default=business_template_name or f"{root_name} {business_name}",
            )
            if typer.confirm("Renseigner les macros Filesystem métier ?", default=False):
                fs_matches = typer.prompt("{$BUSINESS.FS.MATCHES}", default=".*")
                fs_not_matches = typer.prompt("{$BUSINESS.FS.NOT_MATCHES}", default="")
            if typer.confirm("Renseigner les macros Services métier ?", default=False):
                service_matches = typer.prompt("{$BUSINESS.SERVICE.MATCHES}", default=".*")
                service_not_matches = typer.prompt("{$BUSINESS.SERVICE.NOT_MATCHES}", default="")
            system_tags = _parse_tags(typer.prompt("Tags SYSTEM", default="layer=system"))
            default_tags = f"layer=business,application={(business_name or 'business').lower()}"
            business_tags = _parse_tags(typer.prompt("Tags BUSINESS", default=default_tags))
        else:
            business_name = business_name or "BUSINESS"
            if template_name:
                base_name = base_name or f"{root_name} BASE"
                system_name = system_name or f"{root_name} SYSTEM"
                business_template_name = business_template_name or f"{root_name} {business_name}"

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
        if any((base_name, system_name, business_template_name)):
            result = rename_layered_templates(
                result,
                base_name=base_name or result.base_template,
                system_name=system_name or result.system_template,
                business_name=business_template_name or result.business_template,
                overwrite=overwrite,
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
    console.print("Import order: BASE, SYSTEM, then BUSINESS.")


@app.command("create-business")
def create_business(
    system_file: Annotated[Path, typer.Argument(exists=False, dir_okay=False, readable=True)],
    business_name: Annotated[str | None, typer.Option("--business-name")] = None,
    template_name: Annotated[str | None, typer.Option("--template-name")] = None,
    output_dir: Annotated[Path | None, typer.Option("--output-dir", "-o")] = None,
    interactive: Annotated[bool, typer.Option("--interactive/--no-interactive")] = False,
    filesystems: Annotated[bool, typer.Option("--filesystems/--no-filesystems")] = False,
    services: Annotated[bool, typer.Option("--services/--no-services")] = False,
    overwrite: Annotated[bool, typer.Option("--overwrite")] = False,
) -> None:
    """Create an additional BUSINESS template from an existing SYSTEM export."""
    try:
        system = load_template(system_file)
        destination = output_dir if output_dir is not None else system.path.parent
        fs_matches = fs_not_matches = service_matches = service_not_matches = None
        system_visible = str(system.template.get("name", system.template.get("template", "SYSTEM")))
        root_visible = system_visible.removesuffix(" SYSTEM")
        if interactive:
            business_name = typer.prompt(
                "Libellé de la couche BUSINESS",
                default=business_name or "BUSINESS",
            )
            template_name = typer.prompt(
                "Nom complet du template BUSINESS",
                default=template_name or f"{root_visible} {business_name}",
            )
            filesystems = typer.confirm("Ajouter la LLD Filesystem métier ?", default=True)
            if filesystems:
                fs_matches = typer.prompt("{$BUSINESS.FS.MATCHES}", default=".*")
                fs_not_matches = typer.prompt("{$BUSINESS.FS.NOT_MATCHES}", default="")
            services = typer.confirm("Ajouter la LLD Services métier ?", default=False)
            if services:
                service_matches = typer.prompt("{$BUSINESS.SERVICE.MATCHES}", default=".*")
                service_not_matches = typer.prompt("{$BUSINESS.SERVICE.NOT_MATCHES}", default="")
            tags = _parse_tags(
                typer.prompt(
                    "Tags BUSINESS",
                    default=f"layer=business,application={(business_name or 'business').lower()}",
                )
            )
        else:
            business_name = business_name or "BUSINESS"
            tags = {"layer": "business", "application": business_name.lower()}
            if filesystems:
                fs_matches, fs_not_matches = ".*", ""
            if services:
                service_matches, service_not_matches = ".*", ""
        result = create_business_template(
            system,
            destination,
            business_name=business_name,
            overwrite=overwrite,
            include_filesystems=filesystems,
            include_services=services,
            business_tags=tags,
            filesystem_matches=fs_matches,
            filesystem_not_matches=fs_not_matches,
            service_matches=service_matches,
            service_not_matches=service_not_matches,
        )
        if template_name:
            result = rename_business_template(
                result,
                template_name=template_name,
                overwrite=overwrite,
            )
    except (
        FileNotFoundError,
        FileExistsError,
        PermissionError,
        TemplateFormatError,
        ValueError,
    ) as exc:
        _exit_with_error(exc)
    console.print(f"[bold green]BUSINESS template created:[/bold green] {result.file}")
    console.print(f"Template name: {result.template}")
    console.print(f"Filesystem LLD cloned: {result.filesystem_rules}")
    console.print(f"Service LLD cloned: {result.service_rules}")
    if result.skipped_service_rules:
        console.print(
            f"[yellow]Service LLD skipped (no master item): {result.skipped_service_rules}[/yellow]"
        )


@app.command("merge")
def merge(
    source_files: Annotated[list[Path], typer.Argument(help="Two or more Zabbix YAML templates.")],
    output: Annotated[Path, typer.Option("--output", "-o", help="Merged YAML output file.")],
    conflict: Annotated[
        str,
        typer.Option("--conflict", help="error, keep-first or keep-last"),
    ] = "error",
    template_name: Annotated[str | None, typer.Option("--template-name")] = None,
    apply: Annotated[bool, typer.Option("--apply", help="Write the merged file.")] = False,
    overwrite: Annotated[bool, typer.Option("--overwrite")] = False,
) -> None:
    """Merge objects from several templates. Dry-run unless --apply is used."""
    try:
        result = merge_templates(
            [load_template(path) for path in source_files],
            output,
            conflict_mode=conflict,  # type: ignore[arg-type]
            apply=apply,
            overwrite=overwrite,
            template_name=template_name,
        )
    except (
        FileNotFoundError,
        FileExistsError,
        PermissionError,
        TemplateFormatError,
        ValueError,
    ) as exc:
        _exit_with_error(exc)

    mode = "Simulation" if result.dry_run else "Applied"
    console.print(f"[bold]{mode}:[/bold] {result.source_count} templates")
    table = Table(title="Merged objects")
    table.add_column("Section")
    table.add_column("Added", justify="right")
    for section, count in result.added.items():
        table.add_row(section, str(count))
    console.print(table)
    if result.conflicts:
        conflict_table = Table(title="Conflicts")
        conflict_table.add_column("Section")
        conflict_table.add_column("Identity")
        conflict_table.add_column("Source")
        for item in result.conflicts:
            conflict_table.add_row(item.section, item.identity, str(item.source))
        console.print(conflict_table)
    if result.dry_run:
        console.print("[yellow]No file created. Add --apply to write the merge result.[/yellow]")
    else:
        console.print(f"[bold green]Merged template created:[/bold green] {result.output_file}")


@app.command("move-lld")
def move_lld(
    source_file: Annotated[Path, typer.Argument(exists=False, dir_okay=False, readable=True)],
    destination_file: Annotated[
        Path,
        typer.Argument(exists=False, dir_okay=False, readable=True),
    ],
    select: Annotated[list[str] | None, typer.Option("--select", "-s")] = None,
    move_all: Annotated[bool, typer.Option("--all")] = False,
    apply: Annotated[bool, typer.Option("--apply")] = False,
    backup: Annotated[bool, typer.Option("--backup/--no-backup")] = True,
) -> None:
    """Move complete LLD rule blocks between two template exports."""
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
