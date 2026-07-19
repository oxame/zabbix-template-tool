"""Console and JSON rendering for template comparisons."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from rich.console import Console
from rich.markup import escape
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

FIELD_LABELS = {
    "delay": "Update interval",
    "history": "History",
    "trends": "Trends",
    "timeout": "Timeout",
    "status": "Status",
    "type": "Type",
    "value_type": "Value type",
    "units": "Units",
    "description": "Description",
    "expression": "Expression",
    "recovery_expression": "Recovery expression",
    "priority": "Severity",
    "preprocessing": "Preprocessing",
    "tags": "Tags",
    "filter": "Filter",
    "overrides": "Overrides",
    "widgets": "Widgets",
    "triggers": "Triggers",
}

LIST_IDENTITY_FIELDS = (
    "name",
    "key",
    "macro",
    "tag",
    "type",
    "expression",
)


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

    status = (
        "[bold green]IDENTICAL[/bold green]"
        if result.identical
        else "[bold yellow]DIFFERENT[/bold yellow]"
    )
    console.print(f"[bold]Template comparison[/bold] — {status}")
    console.print(f"Template : {escape(result.template_name)}")
    console.print(
        f"Source   : {escape(result.source_profile)} "
        f"(export {escape(result.source_version or 'n/a')})"
    )
    console.print(
        f"Target   : {escape(result.target_profile)} "
        f"(export {escape(result.target_version or 'n/a')})"
    )
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
        section_label = escape(SECTION_LABELS.get(section.section, section.section))
        console.rule(f"[bold]{section_label}[/bold]")
        for difference in section.differences:
            marker, style = {
                "added": ("+", "green"),
                "removed": ("-", "red"),
                "modified": ("~", "yellow"),
                "unchanged": ("=", "dim"),
            }[difference.change]
            identity = escape(difference.identity)
            change = escape(difference.change)
            console.print()
            console.print(f"[{style}]{marker} {identity} ({change})[/{style}]")
            if difference.change == "modified":
                _render_field_differences(
                    difference.fields,
                    console,
                    source_profile=result.source_profile,
                    target_profile=result.target_profile,
                )


def _render_field_differences(
    fields: tuple[Any, ...],
    console: Console,
    *,
    source_profile: str,
    target_profile: str,
) -> None:
    if not fields:
        console.print("    [dim]Object content changed.[/dim]")
        return

    for field_difference in fields:
        label = escape(_field_label(field_difference.path))
        path = escape(field_difference.path)
        console.print(f"    [bold]{label}[/bold] [dim]({path})[/dim]")
        _render_business_value_difference(
            field_difference.source,
            field_difference.target,
            console,
            source_profile=source_profile,
            target_profile=target_profile,
            indent="      ",
        )


def _render_business_value_difference(
    source: Any,
    target: Any,
    console: Console,
    *,
    source_profile: str,
    target_profile: str,
    indent: str,
) -> None:
    if _is_mapping_list(source) or _is_mapping_list(target):
        _render_mapping_list_difference(
            source,
            target,
            console,
            source_profile=source_profile,
            target_profile=target_profile,
            indent=indent,
        )
        return

    if _is_multiline_text(source) or _is_multiline_text(target):
        _render_multiline_difference(
            source,
            target,
            console,
            source_profile=source_profile,
            target_profile=target_profile,
            indent=indent,
        )
        return

    _render_profile_value(
        source_profile,
        source,
        console,
        style="cyan",
        indent=indent,
    )
    _render_profile_value(
        target_profile,
        target,
        console,
        style="magenta",
        indent=indent,
    )


def _render_mapping_list_difference(
    source: Any,
    target: Any,
    console: Console,
    *,
    source_profile: str,
    target_profile: str,
    indent: str,
) -> None:
    source_items = _as_mapping_list(source)
    target_items = _as_mapping_list(target)
    source_index = _index_mapping_list(source_items)
    target_index = _index_mapping_list(target_items)

    for identity in sorted(source_index.keys() | target_index.keys()):
        source_item = source_index.get(identity)
        target_item = target_index.get(identity)
        escaped_identity = escape(identity)

        if source_item is None:
            console.print(f"{indent}[red]- {escaped_identity}[/red]")
            _render_mapping(target_item or {}, console, indent=f"{indent}  ")
            continue
        if target_item is None:
            console.print(f"{indent}[green]+ {escaped_identity}[/green]")
            _render_mapping(source_item, console, indent=f"{indent}  ")
            continue
        if source_item == target_item:
            continue

        console.print(f"{indent}[yellow]~ {escaped_identity}[/yellow]")
        for key in sorted(source_item.keys() | target_item.keys(), key=str):
            source_value = source_item.get(key)
            target_value = target_item.get(key)
            if source_value == target_value:
                continue
            field_label = escape(_field_label(str(key)))
            console.print(f"{indent}  [bold]{field_label}[/bold]")
            _render_business_value_difference(
                source_value,
                target_value,
                console,
                source_profile=source_profile,
                target_profile=target_profile,
                indent=f"{indent}    ",
            )


def _render_multiline_difference(
    source: Any,
    target: Any,
    console: Console,
    *,
    source_profile: str,
    target_profile: str,
    indent: str,
) -> None:
    _render_multiline_profile(source_profile, source, console, style="cyan", indent=indent)
    _render_multiline_profile(target_profile, target, console, style="magenta", indent=indent)


def _render_multiline_profile(
    profile: str,
    value: Any,
    console: Console,
    *,
    style: str,
    indent: str,
) -> None:
    console.print(f"{indent}[{style}]{escape(profile)}[/{style}]")
    rendered = _plain_value(value)
    if value is None:
        console.print(f"{indent}  [dim]— (not defined)[/dim]")
        return
    for line in rendered.splitlines() or [rendered]:
        console.print(f"{indent}  {escape(line)}", markup=True)


def _render_profile_value(
    profile: str,
    value: Any,
    console: Console,
    *,
    style: str,
    indent: str,
) -> None:
    console.print(
        f"{indent}[{style}]{escape(profile)}[/{style}] : {_format_value(value)}"
    )


def _render_mapping(value: Mapping[str, Any], console: Console, *, indent: str) -> None:
    for key, item in sorted(value.items(), key=lambda entry: str(entry[0])):
        label = escape(_field_label(str(key)))
        console.print(f"{indent}[bold]{label}[/bold] : {_format_value(item)}")


def _index_mapping_list(items: list[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    indexed: dict[str, Mapping[str, Any]] = {}
    for position, item in enumerate(items, start=1):
        identity = _mapping_identity(item, position)
        if identity in indexed:
            identity = f"{identity} #{position}"
        indexed[identity] = item
    return indexed


def _mapping_identity(item: Mapping[str, Any], position: int) -> str:
    for field in LIST_IDENTITY_FIELDS:
        value = item.get(field)
        if value not in (None, ""):
            return f"{_field_label(field)}: {_plain_value(value, max_length=100)}"
    return f"Entry #{position}"


def _as_mapping_list(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _is_mapping_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, Mapping) for item in value)


def _is_multiline_text(value: Any) -> bool:
    if isinstance(value, str):
        return "\n" in value or len(value) > 120
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return any(isinstance(item, str) and ("\n" in item or len(item) > 120) for item in value)
    return False


def _field_label(path: str) -> str:
    field_name = path.rsplit(".", 1)[-1]
    return FIELD_LABELS.get(field_name, field_name.replace("_", " ").capitalize())


def _plain_value(value: Any, *, max_length: int | None = None) -> str:
    if value is None:
        return "— (not defined)"
    if isinstance(value, str):
        rendered = value
    else:
        rendered = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str, indent=2)
    if max_length is not None and len(rendered) > max_length:
        return f"{rendered[: max_length - 1]}…"
    return rendered


def _format_value(value: Any, *, max_length: int = 240) -> str:
    if value is None:
        return "[dim]— (not defined)[/dim]"
    rendered = _plain_value(value).replace("\n", "\\n")
    if len(rendered) > max_length:
        rendered = f"{rendered[: max_length - 1]}…"
    return escape(rendered)
