"""Pure structural comparison engine for exported Zabbix templates."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from ztt.compare_models import (
    FieldDifference,
    ObjectDifference,
    SectionComparison,
    TemplateComparisonResult,
)
from ztt.zabbix_api import ZabbixAPIError


class CompareEngine:
    """Compare two parsed Zabbix YAML exports without performing I/O."""

    SECTION_IDENTITIES: dict[str, tuple[str, ...]] = {
        "items": ("key", "name"),
        "discovery_rules": ("key", "name"),
        "triggers": ("name", "expression"),
        "graphs": ("name",),
        "dashboards": ("name",),
        "macros": ("macro",),
        "value_maps": ("name",),
        "httptests": ("name",),
    }
    IGNORED_FIELDS = frozenset({"uuid"})

    def compare_templates(
        self,
        *,
        template_name: str,
        source_profile: str,
        target_profile: str,
        source_document: Mapping[str, Any],
        target_document: Mapping[str, Any],
    ) -> TemplateComparisonResult:
        source_export, source_template = self._extract_template(source_document, template_name)
        target_export, target_template = self._extract_template(target_document, template_name)

        sections = tuple(
            self._compare_section(
                section,
                source_template.get(section),
                target_template.get(section),
            )
            for section in self.SECTION_IDENTITIES
        )
        return TemplateComparisonResult(
            template_name=template_name,
            source_profile=source_profile,
            target_profile=target_profile,
            source_version=self._optional_string(source_export.get("version")),
            target_version=self._optional_string(target_export.get("version")),
            sections=sections,
        )

    def _compare_section(
        self,
        section: str,
        source_value: Any,
        target_value: Any,
    ) -> SectionComparison:
        source_objects = self._as_object_list(source_value, section)
        target_objects = self._as_object_list(target_value, section)
        source_index = self._index_objects(section, source_objects)
        target_index = self._index_objects(section, target_objects)

        differences: list[ObjectDifference] = []
        added = removed = modified = unchanged = 0
        for identity in sorted(source_index.keys() | target_index.keys()):
            source_object = source_index.get(identity)
            target_object = target_index.get(identity)
            if source_object is None:
                removed += 1
                differences.append(
                    ObjectDifference(section, identity, "removed", target=target_object)
                )
            elif target_object is None:
                added += 1
                differences.append(
                    ObjectDifference(section, identity, "added", source=source_object)
                )
            else:
                field_differences = tuple(self._diff_fields(source_object, target_object))
                if field_differences:
                    modified += 1
                    differences.append(
                        ObjectDifference(
                            section,
                            identity,
                            "modified",
                            source=source_object,
                            target=target_object,
                            fields=field_differences,
                        )
                    )
                else:
                    unchanged += 1

        return SectionComparison(
            section=section,
            source_count=len(source_objects),
            target_count=len(target_objects),
            added=added,
            removed=removed,
            modified=modified,
            unchanged=unchanged,
            differences=tuple(differences),
        )

    def _diff_fields(
        self,
        source: Any,
        target: Any,
        path: str = "",
    ) -> list[FieldDifference]:
        """Return stable, human-readable leaf differences between two values."""
        if isinstance(source, Mapping) and isinstance(target, Mapping):
            differences: list[FieldDifference] = []
            keys = {
                str(key)
                for key in source.keys() | target.keys()
                if str(key) not in self.IGNORED_FIELDS
            }
            for key in sorted(keys):
                field_path = f"{path}.{key}" if path else key
                source_present = key in source
                target_present = key in target
                if not source_present:
                    differences.append(FieldDifference(field_path, None, deepcopy(target[key])))
                elif not target_present:
                    differences.append(FieldDifference(field_path, deepcopy(source[key]), None))
                else:
                    differences.extend(
                        self._diff_fields(source[key], target[key], field_path)
                    )
            return differences

        if isinstance(source, list) and isinstance(target, list):
            source_value = self._normalise(source)
            target_value = self._normalise(target)
            if source_value == target_value:
                return []
            return [FieldDifference(path or "value", source_value, target_value)]

        source_value = self._normalise(source)
        target_value = self._normalise(target)
        if source_value == target_value:
            return []
        return [FieldDifference(path or "value", source_value, target_value)]

    def _index_objects(
        self,
        section: str,
        objects: Sequence[Mapping[str, Any]],
    ) -> dict[str, Mapping[str, Any]]:
        indexed: dict[str, Mapping[str, Any]] = {}
        for position, item in enumerate(objects, start=1):
            identity = self._identity(section, item, position)
            if identity in indexed:
                raise ZabbixAPIError(
                    f"Duplicate identity '{identity}' detected in section '{section}'."
                )
            indexed[identity] = item
        return indexed

    def _identity(self, section: str, item: Mapping[str, Any], position: int) -> str:
        for field in self.SECTION_IDENTITIES[section]:
            value = item.get(field)
            if value not in (None, ""):
                return str(value)
        raise ZabbixAPIError(
            f"Object #{position} in section '{section}' has no usable identity field."
        )

    def _normalise(self, value: Any) -> Any:
        if isinstance(value, Mapping):
            return {
                str(key): self._normalise(item)
                for key, item in sorted(value.items(), key=lambda entry: str(entry[0]))
                if str(key) not in self.IGNORED_FIELDS
            }
        if isinstance(value, list):
            normalised = [self._normalise(item) for item in value]
            return sorted(normalised, key=self._stable_sort_key)
        return deepcopy(value)

    @staticmethod
    def _stable_sort_key(value: Any) -> str:
        return repr(value)

    @staticmethod
    def _as_object_list(value: Any, section: str) -> list[Mapping[str, Any]]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ZabbixAPIError(f"Template section '{section}' is not a list.")
        if not all(isinstance(item, Mapping) for item in value):
            raise ZabbixAPIError(f"Template section '{section}' contains an invalid object.")
        return list(value)

    @staticmethod
    def _extract_template(
        document: Mapping[str, Any],
        requested_name: str,
    ) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
        export = document.get("zabbix_export")
        if not isinstance(export, Mapping):
            raise ZabbixAPIError("Document does not contain a zabbix_export mapping.")
        templates = export.get("templates")
        if not isinstance(templates, list) or not templates:
            raise ZabbixAPIError("Document does not contain a non-empty templates section.")

        matches = [
            template
            for template in templates
            if isinstance(template, Mapping)
            and requested_name
            in {str(template.get("template", "")), str(template.get("name", ""))}
        ]
        if not matches and len(templates) == 1 and isinstance(templates[0], Mapping):
            matches = [templates[0]]
        if not matches:
            raise ZabbixAPIError(f"Template '{requested_name}' was not found in the export.")
        if len(matches) > 1:
            raise ZabbixAPIError(f"Template '{requested_name}' is ambiguous in the export.")
        return export, matches[0]

    @staticmethod
    def _optional_string(value: Any) -> str | None:
        return str(value) if value is not None else None
