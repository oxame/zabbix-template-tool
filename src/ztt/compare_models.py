"""Typed models used by the Zabbix comparison engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

ChangeKind = Literal["added", "removed", "modified", "unchanged"]


@dataclass(frozen=True, slots=True)
class FieldDifference:
    """Difference detected for one field inside a modified object."""

    path: str
    source: Any = None
    target: Any = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ObjectDifference:
    """Difference detected for one named object in a template section."""

    section: str
    identity: str
    change: ChangeKind
    source: Any = None
    target: Any = None
    fields: tuple[FieldDifference, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["fields"] = [field_difference.to_dict() for field_difference in self.fields]
        return result


@dataclass(frozen=True, slots=True)
class SectionComparison:
    """Comparison summary for one template section."""

    section: str
    source_count: int
    target_count: int
    added: int = 0
    removed: int = 0
    modified: int = 0
    unchanged: int = 0
    differences: tuple[ObjectDifference, ...] = field(default_factory=tuple)

    @property
    def identical(self) -> bool:
        return self.added == 0 and self.removed == 0 and self.modified == 0

    def to_dict(self, *, include_details: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            "section": self.section,
            "source_count": self.source_count,
            "target_count": self.target_count,
            "added": self.added,
            "removed": self.removed,
            "modified": self.modified,
            "unchanged": self.unchanged,
            "identical": self.identical,
        }
        if include_details:
            result["differences"] = [difference.to_dict() for difference in self.differences]
        return result


@dataclass(frozen=True, slots=True)
class TemplateComparisonResult:
    """Complete comparison result for one template across two environments."""

    template_name: str
    source_profile: str
    target_profile: str
    source_version: str | None
    target_version: str | None
    sections: tuple[SectionComparison, ...]

    @property
    def identical(self) -> bool:
        return all(section.identical for section in self.sections)

    @property
    def added(self) -> int:
        return sum(section.added for section in self.sections)

    @property
    def removed(self) -> int:
        return sum(section.removed for section in self.sections)

    @property
    def modified(self) -> int:
        return sum(section.modified for section in self.sections)

    def to_dict(self, *, include_details: bool = True) -> dict[str, Any]:
        return {
            "status": "ok",
            "template": self.template_name,
            "source_profile": self.source_profile,
            "target_profile": self.target_profile,
            "source_version": self.source_version,
            "target_version": self.target_version,
            "identical": self.identical,
            "summary": {
                "added": self.added,
                "removed": self.removed,
                "modified": self.modified,
            },
            "sections": [
                section.to_dict(include_details=include_details) for section in self.sections
            ],
        }
