"""Safe promotion of one Zabbix template between configured profiles."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from ruamel.yaml import YAML

from ztt.profiles import get_profile
from ztt.zabbix_api import ZabbixAPIClient


@dataclass(slots=True, frozen=True)
class PromotionResult:
    """Result returned after a template promotion."""

    template: str
    source_profile: str
    target_profile: str
    target_existed: bool
    backup_file: Path | None
    metadata_file: Path | None
    history_file: Path
    source_sha256: str
    source_export_version: str | None
    promoted_at: str
    duration_seconds: float
    rollback_performed: bool = False


class PromotionService:
    """Copy a template from one profile to another with backup and rollback."""

    def __init__(
        self,
        source_profile: str,
        target_profile: str,
        config: Path | None = None,
    ) -> None:
        self.source_profile = get_profile(source_profile, config)
        self.target_profile = get_profile(target_profile, config)
        self.source_client = ZabbixAPIClient.from_profile(self.source_profile)
        self.target_client = ZabbixAPIClient.from_profile(self.target_profile)

    def promote_template(
        self,
        template_name: str,
        backup_dir: Path,
    ) -> PromotionResult:
        """Promote one template and restore the previous target export on failure."""
        started = perf_counter()
        promoted_at = datetime.now(timezone.utc)
        timestamp = promoted_at.strftime("%Y%m%dT%H%M%SZ")
        safe_name = self._safe_filename(template_name)

        source_yaml = self.source_client.export_template(template_name)
        source_sha256 = hashlib.sha256(source_yaml.encode("utf-8")).hexdigest()
        source_export_version = self._export_version(source_yaml)

        target_template = self.target_client.find_template(template_name)
        target_existed = target_template is not None
        backup_file: Path | None = None
        metadata_file: Path | None = None
        previous_yaml: str | None = None

        template_backup_dir = (
            backup_dir
            / self.target_profile.name
            / safe_name
            / promoted_at.strftime("%Y")
            / promoted_at.strftime("%m")
            / promoted_at.strftime("%d")
        )
        history_file = backup_dir / "promotion-history.jsonl"

        if target_existed:
            previous_yaml = self.target_client.export_template(template_name)
            previous_sha256 = hashlib.sha256(previous_yaml.encode("utf-8")).hexdigest()
            previous_version = self._export_version(previous_yaml) or "unknown"
            version_label = self._safe_filename(previous_version)
            backup_file = template_backup_dir / (
                f"{safe_name}_{timestamp}_zbx-{version_label}_{previous_sha256[:12]}.yaml"
            )
            metadata_file = backup_file.with_suffix(".json")
            template_backup_dir.mkdir(parents=True, exist_ok=True)
            backup_file.write_text(previous_yaml, encoding="utf-8")
            metadata_file.write_text(
                json.dumps(
                    {
                        "template": template_name,
                        "profile": self.target_profile.name,
                        "backup_created_at": promoted_at.isoformat(),
                        "zabbix_export_version": self._export_version(previous_yaml),
                        "sha256": previous_sha256,
                        "reason": "template promotion backup",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

        rollback_performed = False
        try:
            self.target_client.import_template(source_yaml)
            self.target_client.resolve_template(template_name)
        except Exception:
            if previous_yaml is not None:
                self.target_client.import_template(previous_yaml)
                rollback_performed = True
            raise

        result = PromotionResult(
            template=template_name,
            source_profile=self.source_profile.name,
            target_profile=self.target_profile.name,
            target_existed=target_existed,
            backup_file=backup_file,
            metadata_file=metadata_file,
            history_file=history_file,
            source_sha256=source_sha256,
            source_export_version=source_export_version,
            promoted_at=promoted_at.isoformat(),
            duration_seconds=perf_counter() - started,
            rollback_performed=rollback_performed,
        )
        self._append_history(result)
        return result

    @staticmethod
    def _append_history(result: PromotionResult) -> None:
        result.history_file.parent.mkdir(parents=True, exist_ok=True)
        document = asdict(result)
        for key in ("backup_file", "metadata_file", "history_file"):
            value = document[key]
            document[key] = str(value) if value is not None else None
        with result.history_file.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(document, ensure_ascii=False) + "\n")

    @staticmethod
    def _safe_filename(value: str) -> str:
        cleaned = re.sub(r"\s+", "_", value.strip())
        cleaned = re.sub(r"[^A-Za-z0-9_.-]", "_", cleaned)
        return cleaned or "template"

    @staticmethod
    def _export_version(document: str) -> str | None:
        yaml = YAML(typ="safe")
        parsed = yaml.load(document)
        if not isinstance(parsed, dict):
            return None
        export = parsed.get("zabbix_export")
        if not isinstance(export, dict):
            return None
        version = export.get("version")
        return str(version) if version is not None else None
