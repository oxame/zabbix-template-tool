"""Typed models for safe template promotion workflows."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from ztt.compare_models import TemplateComparisonResult

SyncMode = Literal["dry-run", "apply"]


@dataclass(frozen=True, slots=True)
class TemplateSyncPlan:
    """Validated promotion plan from one Zabbix profile to another."""

    template_name: str
    source_profile: str
    target_profile: str
    mode: SyncMode
    target_is_production: bool
    comparison: TemplateComparisonResult
    backup_file: Path | None = None

    @property
    def changes_required(self) -> bool:
        return not self.comparison.identical

    def to_dict(self, *, include_details: bool = True) -> dict[str, Any]:
        result = asdict(self)
        result["backup_file"] = str(self.backup_file) if self.backup_file is not None else None
        result["changes_required"] = self.changes_required
        result["comparison"] = self.comparison.to_dict(include_details=include_details)
        return result
