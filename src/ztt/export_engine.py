"""Generic read-only export engine for Zabbix configuration objects."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Any

from ruamel.yaml import YAML

from ztt.export_models import (
    ExportResult,
    ExportStatistics,
    ExportTarget,
    ExportTimings,
    ResolvedExportObject,
)
from ztt.profiles import ZabbixProfile
from ztt.zabbix_api import ZabbixAPIClient, ZabbixAPIError


class ExportEngine:
    """Resolve, export, validate and write one Zabbix configuration object."""

    def __init__(self, profile: ZabbixProfile) -> None:
        self.profile = profile
        self.client = ZabbixAPIClient.from_profile(profile)

    def export(
        self,
        *,
        target: ExportTarget,
        requested_name: str,
        destination: Path,
        overwrite: bool = False,
    ) -> ExportResult:
        if destination.exists() and not overwrite:
            raise FileExistsError(f"Output file already exists: {destination}")

        total_started = perf_counter()

        resolve_started = perf_counter()
        resolved = self._resolve(target, requested_name)
        resolve_ms = self._elapsed_ms(resolve_started)

        export_started = perf_counter()
        document = self._export_configuration(target, resolved.object_id)
        api_export_ms = self._elapsed_ms(export_started)

        validation_started = perf_counter()
        statistics = self._validate(document, target)
        validation_ms = self._elapsed_ms(validation_started)

        write_started = perf_counter()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(document, encoding="utf-8")
        write_ms = self._elapsed_ms(write_started)

        total_ms = self._elapsed_ms(total_started)
        return ExportResult(
            profile=self.profile.name,
            target=target,
            object=resolved,
            output_file=destination,
            size_bytes=destination.stat().st_size,
            statistics=statistics,
            timings=ExportTimings(
                resolve_ms=resolve_ms,
                api_export_ms=api_export_ms,
                validation_ms=validation_ms,
                write_ms=write_ms,
                total_ms=total_ms,
            ),
        )

    def _resolve(self, target: ExportTarget, requested_name: str) -> ResolvedExportObject:
        result = self.client.call(
            target.lookup_method,
            {
                "output": [
                    target.id_field,
                    target.technical_name_field,
                    target.visible_name_field,
                ],
                "search": {
                    target.technical_name_field: requested_name,
                    target.visible_name_field: requested_name,
                },
                "searchByAny": True,
            },
        )
        if not isinstance(result, list):
            raise ZabbixAPIError(f"{target.lookup_method} returned an invalid value.")

        matches = [
            item
            for item in result
            if isinstance(item, dict)
            and requested_name
            in {
                str(item.get(target.technical_name_field, "")),
                str(item.get(target.visible_name_field, "")),
            }
        ]
        if not matches:
            raise ZabbixAPIError(f"{target.object_type} '{requested_name}' was not found.")
        if len(matches) > 1:
            details = ", ".join(
                f"{item.get(target.technical_name_field, '')} "
                f"({item.get(target.id_field, '')})"
                for item in matches
            )
            raise ZabbixAPIError(
                f"{target.object_type} name '{requested_name}' is ambiguous: {details}"
            )

        item = matches[0]
        return ResolvedExportObject(
            object_id=str(item.get(target.id_field, "")),
            requested_name=requested_name,
            technical_name=str(item.get(target.technical_name_field, "")),
            visible_name=str(item.get(target.visible_name_field, "")),
        )

    def _export_configuration(self, target: ExportTarget, object_id: str) -> str:
        result = self.client.call(
            "configuration.export",
            {
                "format": "yaml",
                "options": {target.option_name: [object_id]},
            },
        )
        if not isinstance(result, str) or not result.strip():
            raise ZabbixAPIError("configuration.export returned an empty or invalid document.")
        return result

    def _validate(self, document: str, target: ExportTarget) -> ExportStatistics:
        try:
            parsed = YAML(typ="safe").load(document)
        except Exception as exc:
            raise ZabbixAPIError(f"Exported YAML is invalid: {exc}") from exc

        if not isinstance(parsed, dict):
            raise ZabbixAPIError("Exported YAML does not contain a mapping at its root.")
        export = parsed.get("zabbix_export")
        if not isinstance(export, dict):
            raise ZabbixAPIError("Exported YAML does not contain a zabbix_export section.")
        objects = export.get(target.expected_key)
        if not isinstance(objects, list) or not objects:
            raise ZabbixAPIError(
                f"Exported YAML does not contain a non-empty '{target.expected_key}' section."
            )

        if target.expected_key != "templates":
            return ExportStatistics(
                exported_objects=len(objects),
                export_version=self._optional_string(export.get("version")),
            )

        template = objects[0] if isinstance(objects[0], dict) else {}
        return ExportStatistics(
            exported_objects=len(objects),
            export_version=self._optional_string(export.get("version")),
            items=self._list_count(template.get("items")),
            discovery_rules=self._list_count(template.get("discovery_rules")),
            triggers=self._list_count(template.get("triggers")),
            graphs=self._list_count(template.get("graphs")),
            dashboards=self._list_count(template.get("dashboards")),
            macros=self._list_count(template.get("macros")),
        )

    @staticmethod
    def _elapsed_ms(started: float) -> float:
        return (perf_counter() - started) * 1000

    @staticmethod
    def _list_count(value: Any) -> int:
        return len(value) if isinstance(value, list) else 0

    @staticmethod
    def _optional_string(value: Any) -> str | None:
        return str(value) if value is not None else None
