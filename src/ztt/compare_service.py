"""Application service for comparing templates across Zabbix profiles."""

from __future__ import annotations

from pathlib import Path

from ztt.compare_engine import CompareEngine
from ztt.compare_models import TemplateComparisonResult
from ztt.export_engine import ExportEngine
from ztt.export_service import TEMPLATE
from ztt.profiles import get_profile


class CompareService:
    """Export templates in memory from two profiles and compare them."""

    def __init__(
        self,
        source_profile: str,
        target_profile: str,
        config: Path | None = None,
    ) -> None:
        self.source_engine = ExportEngine(get_profile(source_profile, config))
        self.target_engine = ExportEngine(get_profile(target_profile, config))
        self.engine = CompareEngine()

    def compare_template(self, template_name: str) -> TemplateComparisonResult:
        _, source_document = self.source_engine.fetch_document(
            target=TEMPLATE,
            requested_name=template_name,
        )
        _, target_document = self.target_engine.fetch_document(
            target=TEMPLATE,
            requested_name=template_name,
        )
        return self.engine.compare_templates(
            template_name=template_name,
            source_profile=self.source_engine.profile.name,
            target_profile=self.target_engine.profile.name,
            source_document=source_document,
            target_document=target_document,
        )
