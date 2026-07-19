"""Safe template promotion service between configured Zabbix profiles."""

from __future__ import annotations

from pathlib import Path

from ztt.compare_engine import CompareEngine
from ztt.export_engine import ExportEngine
from ztt.export_service import TEMPLATE
from ztt.profiles import get_profile
from ztt.sync_models import TemplateSyncPlan


class TemplateSyncService:
    """Build and later execute QUAL-to-PROD template promotion plans."""

    def __init__(
        self,
        source_profile: str,
        target_profile: str,
        config: Path | None = None,
    ) -> None:
        source = get_profile(source_profile, config)
        target = get_profile(target_profile, config)
        if source.name == target.name:
            raise ValueError("Source and target profiles must be different.")

        self.source_engine = ExportEngine(source)
        self.target_engine = ExportEngine(target)
        self.compare_engine = CompareEngine()

    def dry_run(self, template_name: str) -> TemplateSyncPlan:
        """Export both templates in memory and return a non-destructive promotion plan."""
        _, source_document = self.source_engine.fetch_document(
            target=TEMPLATE,
            requested_name=template_name,
        )
        _, target_document = self.target_engine.fetch_document(
            target=TEMPLATE,
            requested_name=template_name,
        )
        comparison = self.compare_engine.compare_templates(
            template_name=template_name,
            source_profile=self.source_engine.profile.name,
            target_profile=self.target_engine.profile.name,
            source_document=source_document,
            target_document=target_document,
        )
        return TemplateSyncPlan(
            template_name=template_name,
            source_profile=self.source_engine.profile.name,
            target_profile=self.target_engine.profile.name,
            mode="dry-run",
            target_is_production=self.target_engine.profile.production,
            comparison=comparison,
        )
