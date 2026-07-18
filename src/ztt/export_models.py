"""Typed models shared by the Zabbix export engine, services and CLI."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class ExportTarget:
    """Description of one exportable Zabbix object type."""

    object_type: str
    lookup_method: str
    option_name: str
    expected_key: str
    id_field: str
    technical_name_field: str
    visible_name_field: str


@dataclass(frozen=True, slots=True)
class ResolvedExportObject:
    """Object identity returned by the Zabbix lookup request."""

    object_id: str
    requested_name: str
    technical_name: str
    visible_name: str


@dataclass(frozen=True, slots=True)
class ExportStatistics:
    """Statistics extracted from the validated YAML document."""

    exported_objects: int = 0
    export_version: str | None = None
    items: int = 0
    discovery_rules: int = 0
    triggers: int = 0
    graphs: int = 0
    dashboards: int = 0
    macros: int = 0


@dataclass(frozen=True, slots=True)
class ExportTimings:
    """Durations, in milliseconds, for the export workflow."""

    resolve_ms: float = 0.0
    api_export_ms: float = 0.0
    validation_ms: float = 0.0
    write_ms: float = 0.0
    total_ms: float = 0.0


@dataclass(frozen=True, slots=True)
class ExportResult:
    """Complete result returned by the export service."""

    profile: str
    target: ExportTarget
    object: ResolvedExportObject
    output_file: Path
    size_bytes: int
    statistics: ExportStatistics
    timings: ExportTimings
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return the stable machine-readable representation used by ``--json``."""
        return {
            "status": "ok",
            "profile": self.profile,
            "object": {
                "type": self.target.object_type,
                "id": self.object.object_id,
                "requested_name": self.object.requested_name,
                "technical_name": self.object.technical_name,
                "visible_name": self.object.visible_name,
                **asdict(self.statistics),
            },
            "output": {
                "file": str(self.output_file.resolve()),
                "size_bytes": self.size_bytes,
            },
            "timings_ms": {
                "resolve": round(self.timings.resolve_ms, 3),
                "api_export": round(self.timings.api_export_ms, 3),
                "validation": round(self.timings.validation_ms, 3),
                "write": round(self.timings.write_ms, 3),
                "total": round(self.timings.total_ms, 3),
            },
            **self.metadata,
        }
