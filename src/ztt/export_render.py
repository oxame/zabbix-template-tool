"""Console and JSON rendering for export results."""

from __future__ import annotations

import json

from rich.console import Console

from ztt.export_models import ExportResult


def format_ms(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1f} ms"


def format_size(size_bytes: int) -> str:
    size = float(size_bytes)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if size < 1024 or unit == "GiB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size_bytes} B"


def render_export(result: ExportResult, console: Console, *, json_output: bool = False) -> None:
    """Render one export result without coupling the service to Rich or Typer."""
    if json_output:
        console.print_json(json.dumps(result.to_dict(), ensure_ascii=False))
        return

    timings = result.timings
    statistics = result.statistics
    console.print(f"[bold]{result.target.object_type} export[/bold]")
    _ok(
        console,
        "Object resolved",
        f"{result.object.technical_name} ({result.object.object_id})",
        timings.resolve_ms,
    )
    _ok(console, "API export", result.object.requested_name, timings.api_export_ms)
    _ok(
        console,
        "YAML validation",
        f"{statistics.exported_objects} object(s)",
        timings.validation_ms,
    )
    _ok(console, "File written", str(result.output_file), timings.write_ms)
    console.print()
    console.print(f"Profile       : {result.profile}")
    console.print(f"Object type   : {result.target.object_type}")
    console.print(f"Object ID     : {result.object.object_id}")
    console.print(f"Technical name: {result.object.technical_name}")
    console.print(f"Visible name  : {result.object.visible_name}")
    if statistics.export_version:
        console.print(f"Version       : {statistics.export_version}")
    if result.target.expected_key == "templates":
        console.print(
            "Objects       : "
            f"{statistics.items} items, "
            f"{statistics.discovery_rules} LLD, "
            f"{statistics.triggers} triggers"
        )
    console.print(f"File          : {result.output_file.resolve()}")
    console.print(f"Size          : {format_size(result.size_bytes)}")
    console.print(f"Total time    : {format_ms(timings.total_ms)}")


def _ok(
    console: Console,
    label: str,
    value: str | None = None,
    duration_ms: float | None = None,
) -> None:
    suffix = f" : {value}" if value else ""
    timing = f" [dim]({format_ms(duration_ms)})[/dim]" if duration_ms is not None else ""
    console.print(f"  [bold green]✓[/bold green] {label}{suffix}{timing}")
