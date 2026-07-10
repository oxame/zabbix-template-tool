"""Domain model for a Zabbix YAML export."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


class TemplateFormatError(ValueError):
    """Raised when a YAML file is not a supported Zabbix template export."""


@dataclass(slots=True)
class TemplateSummary:
    """Counts and metadata extracted from one Zabbix template."""

    file: Path
    export_version: str
    template_name: str
    visible_name: str
    items: int
    discovery_rules: int
    triggers: int
    graphs: int
    dashboards: int
    macros: int


@dataclass(slots=True)
class ZabbixTemplate:
    """A loaded Zabbix export and its primary template object."""

    path: Path
    document: dict[str, Any]
    template: dict[str, Any]

    @classmethod
    def from_document(cls, path: Path, document: Any) -> "ZabbixTemplate":
        if not isinstance(document, dict):
            raise TemplateFormatError("The YAML root must be a mapping.")

        export = document.get("zabbix_export")
        if not isinstance(export, dict):
            raise TemplateFormatError("Missing 'zabbix_export' mapping.")

        templates = export.get("templates")
        if not isinstance(templates, list) or not templates:
            raise TemplateFormatError("No template found in 'zabbix_export.templates'.")

        template = templates[0]
        if not isinstance(template, dict):
            raise TemplateFormatError("The first template must be a mapping.")

        return cls(path=path, document=document, template=template)

    @property
    def export_version(self) -> str:
        return str(self.document["zabbix_export"].get("version", "unknown"))

    def summary(self) -> TemplateSummary:
        def count(name: str) -> int:
            value = self.template.get(name, [])
            return len(value) if isinstance(value, list) else 0

        technical_name = str(self.template.get("template", "unknown"))
        visible_name = str(self.template.get("name", technical_name))

        return TemplateSummary(
            file=self.path,
            export_version=self.export_version,
            template_name=technical_name,
            visible_name=visible_name,
            items=count("items"),
            discovery_rules=count("discovery_rules"),
            triggers=count("triggers"),
            graphs=count("graphs"),
            dashboards=count("dashboards"),
            macros=count("macros"),
        )
