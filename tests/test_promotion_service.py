from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from ztt.promotion_service import PromotionService
from ztt.zabbix_api import ZabbixTemplateSummary


SOURCE_YAML = """zabbix_export:
  version: '7.4'
  templates:
    - uuid: 11111111111111111111111111111111
      template: Example template
      name: Example template
"""

TARGET_YAML = """zabbix_export:
  version: '7.2'
  templates:
    - uuid: 11111111111111111111111111111111
      template: Example template
      name: Example template
"""


class FakeClient:
    def __init__(self, exported: str, exists: bool = True) -> None:
        self.exported = exported
        self.exists = exists
        self.imported: list[str] = []

    def export_template(self, name: str) -> str:
        return self.exported

    def list_templates(self, search: str | None = None) -> list[ZabbixTemplateSummary]:
        if not self.exists:
            return []
        return [ZabbixTemplateSummary("42", "Example template", "Example template")]

    def resolve_template(self, name: str) -> ZabbixTemplateSummary:
        return ZabbixTemplateSummary("42", name, name)

    def call(self, method: str, params: dict[str, object]) -> bool:
        assert method == "configuration.import"
        self.imported.append(str(params["source"]))
        return True


def test_promote_existing_template_creates_versioned_backup(tmp_path: Path) -> None:
    service = object.__new__(PromotionService)
    service.source_profile = SimpleNamespace(name="qual")
    service.target_profile = SimpleNamespace(name="prod")
    service.source_client = FakeClient(SOURCE_YAML)
    service.target_client = FakeClient(TARGET_YAML)

    result = service.promote_template("Example template", tmp_path)

    assert result.target_existed is True
    assert result.backup_file is not None
    assert result.backup_file.exists()
    assert "zbx-7.2" in result.backup_file.name
    assert result.backup_file.read_text(encoding="utf-8") == TARGET_YAML
    assert result.metadata_file is not None
    metadata = json.loads(result.metadata_file.read_text(encoding="utf-8"))
    assert metadata["zabbix_export_version"] == "7.2"
    assert service.target_client.imported == [SOURCE_YAML]
    assert result.history_file.exists()


def test_promote_missing_template_does_not_create_backup(tmp_path: Path) -> None:
    service = object.__new__(PromotionService)
    service.source_profile = SimpleNamespace(name="qual")
    service.target_profile = SimpleNamespace(name="prod")
    service.source_client = FakeClient(SOURCE_YAML)
    service.target_client = FakeClient(TARGET_YAML, exists=False)

    result = service.promote_template("Example template", tmp_path)

    assert result.target_existed is False
    assert result.backup_file is None
    assert result.metadata_file is None
    assert service.target_client.imported == [SOURCE_YAML]
