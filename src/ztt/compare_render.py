"""Console and JSON rendering for template comparisons."""

from __future__ import annotations

import json

from rich.console import Console
from rich.table import Table

from ztt.compare_models import TemplateComparisonResult


SECTION_LABELS = {
    "items": "Items",
    "discovery_rules": "Discovery rules",
    "triggers": "Triggers",
    "graphs": "Graphs",
    "dashboards": "Dashboards",
    "macros": "Macros",
    "value_maps": "Value maps",
    "httptests": "Web scenarios",
}


def render_comparison(
    result: TemplateComparisonResult,
    console: Console,
    *,
    json_output: bool = False,
    details: bool = False,
) -> None:
    """Render one comparison result for humans or automation."""
    if json_output:
        console.print_json(
            json.dumps(result.to_dict(include_details=details), ensure_ascii=False)
        )
        return

    status = "[bold green]IDENTICAL[/bold green]" if result.identical else "[bold yellow]DIFFERENT[/bold yellow]"
    console.print(f"[bold]Template comparison[/bold] — {status}")
    console.print(f"Template : {result.template_name}")
    console.print(f"Source   : {result.source_profile} (export {result.source_version or 'n/a'})")
    console.print(f"Target   : {result.target_profile} (export {result.target_version or 'n/a'})")
    console.print()

    table = Table(title="Comparison summary")
    table.add_column("Section")
    table.add_column("Source", justify="right")
    table.add_column("Target", justify="right")
    table.add_column("Added", justify="right")
    table.add_column("Removed", justify="right")
    table.add_column("Modified", justify="right")
    table.add_column("Unchanged", justify="right")

    for section in result.sections:
        style = "green" if section.identical else "yellow"
        table.add_row(
            SECTION_LABELS.get(section.section, section.section),
            str(section.source_count),
            str(section.target_count),
            str(section.added),
            str(section.removed),
            str(section.modified),
            str(section.unchanged),
            style=style,
        )
    console.print(table)
    console.print(
        f"Summary: [green]+{result.added}[/green] "
        f"[red]-{result.removed}[/red] "
        f"[yellow]~{result.modified}[/yellow]"
    )

    if details:
        _render_details(result, console)


def _render_details(result: TemplateComparisonResult, console: Console) -> None:
    for section in result.sections:
        if section.identical:
            continue
        console.print()
        console.print(f"[bold]{SECTION_LABELS.get(section.section, section.section)}[/bold]")
        for difference in section.differences:
            marker, style = {
                "added": ("+", "green"),
                "removed": ("-", "red"),
                "modified": ("~", "yellow"),
                "unchanged": ("=", "dim"),
            }[difference.change]
            console.print(
                f"  [{style}]{marker} {difference.identity} ({difference.change})[/{style}]"
            )
