from pathlib import Path

import pytest

from ztt.loader import load_template
from ztt.template import TemplateFormatError


SAMPLE = Path(__file__).parent / "samples" / "template.yaml"


def test_load_template_summary() -> None:
    summary = load_template(SAMPLE).summary()

    assert summary.export_version == "7.4"
    assert summary.template_name == "TEMPLATE_TEST_BASE"
    assert summary.visible_name == "Test Base"
    assert summary.items == 1
    assert summary.discovery_rules == 1
    assert summary.macros == 1


def test_reject_non_zabbix_yaml(tmp_path: Path) -> None:
    path = tmp_path / "invalid.yaml"
    path.write_text("hello: world\n", encoding="utf-8")

    with pytest.raises(TemplateFormatError, match="zabbix_export"):
        load_template(path)
