"""Application service exposing typed Zabbix export operations."""

from __future__ import annotations

from pathlib import Path

from ztt.export_engine import ExportEngine
from ztt.export_models import ExportResult, ExportTarget
from ztt.profiles import get_profile


TEMPLATE = ExportTarget(
    object_type="Template",
    lookup_method="template.get",
    option_name="templates",
    expected_key="templates",
    id_field="templateid",
    technical_name_field="host",
    visible_name_field="name",
)

HOST = ExportTarget(
    object_type="Host",
    lookup_method="host.get",
    option_name="hosts",
    expected_key="hosts",
    id_field="hostid",
    technical_name_field="host",
    visible_name_field="name",
)

HOST_GROUP = ExportTarget(
    object_type="Host group",
    lookup_method="hostgroup.get",
    option_name="host_groups",
    expected_key="host_groups",
    id_field="groupid",
    technical_name_field="name",
    visible_name_field="name",
)

TEMPLATE_GROUP = ExportTarget(
    object_type="Template group",
    lookup_method="templategroup.get",
    option_name="template_groups",
    expected_key="template_groups",
    id_field="groupid",
    technical_name_field="name",
    visible_name_field="name",
)


class ExportService:
    """Facade used by CLI commands and future compare/import workflows."""

    def __init__(self, profile_name: str, config: Path | None = None) -> None:
        self.engine = ExportEngine(get_profile(profile_name, config))

    def export_template(
        self,
        name: str,
        destination: Path,
        *,
        overwrite: bool = False,
    ) -> ExportResult:
        return self._export(TEMPLATE, name, destination, overwrite)

    def export_host(
        self,
        name: str,
        destination: Path,
        *,
        overwrite: bool = False,
    ) -> ExportResult:
        return self._export(HOST, name, destination, overwrite)

    def export_host_group(
        self,
        name: str,
        destination: Path,
        *,
        overwrite: bool = False,
    ) -> ExportResult:
        return self._export(HOST_GROUP, name, destination, overwrite)

    def export_template_group(
        self,
        name: str,
        destination: Path,
        *,
        overwrite: bool = False,
    ) -> ExportResult:
        return self._export(TEMPLATE_GROUP, name, destination, overwrite)

    def _export(
        self,
        target: ExportTarget,
        name: str,
        destination: Path,
        overwrite: bool,
    ) -> ExportResult:
        return self.engine.export(
            target=target,
            requested_name=name,
            destination=destination,
            overwrite=overwrite,
        )
