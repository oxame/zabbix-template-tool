from pathlib import Path

import pytest
from ruamel.yaml import YAML

from ztt.lld import list_discovery_rules, move_discovery_rules
from ztt.loader import load_template
from ztt.template import TemplateFormatError


SOURCE = """\
zabbix_export:
  version: '7.4'
  templates:
    - uuid: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
      template: TEMPLATE_BASE
      name: Base
      discovery_rules:
        - uuid: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
          name: Filesystem discovery
          key: vfs.fs.discovery
          preprocessing:
            - type: JSONPATH
              parameters:
                - $.data
          item_prototypes:
            - uuid: cccccccccccccccccccccccccccccccc
              name: 'Free space on {#FSNAME}'
              key: 'vfs.fs.size[{#FSNAME},free]'
          trigger_prototypes:
            - uuid: dddddddddddddddddddddddddddddddd
              expression: 'last(/TEMPLATE_BASE/vfs.fs.size[{#FSNAME},free])<1'
              name: 'Low free space on {#FSNAME}'
          overrides:
            - name: Ignore temporary filesystems
              step: '1'
"""

DESTINATION = """\
zabbix_export:
  version: '7.4'
  templates:
    - uuid: eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee
      template: TEMPLATE_SYSTEM
      name: System
"""


def _write_templates(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "base.yaml"
    destination = tmp_path / "system.yaml"
    source.write_text(SOURCE, encoding="utf-8")
    destination.write_text(DESTINATION, encoding="utf-8")
    return source, destination


def test_list_discovery_rules_counts_nested_objects(tmp_path: Path) -> None:
    source, _ = _write_templates(tmp_path)

    rules = list_discovery_rules(load_template(source))

    assert len(rules) == 1
    assert rules[0].name == "Filesystem discovery"
    assert rules[0].item_prototypes == 1
    assert rules[0].trigger_prototypes == 1
    assert rules[0].overrides == 1


def test_move_lld_dry_run_does_not_modify_files(tmp_path: Path) -> None:
    source, destination = _write_templates(tmp_path)
    before_source = source.read_text(encoding="utf-8")
    before_destination = destination.read_text(encoding="utf-8")

    result = move_discovery_rules(
        load_template(source),
        load_template(destination),
        selectors=["vfs.fs.discovery"],
    )

    assert result.dry_run is True
    assert len(result.moved) == 1
    assert source.read_text(encoding="utf-8") == before_source
    assert destination.read_text(encoding="utf-8") == before_destination


def test_move_lld_applies_complete_rule_and_creates_backups(tmp_path: Path) -> None:
    source, destination = _write_templates(tmp_path)

    result = move_discovery_rules(
        load_template(source),
        load_template(destination),
        selectors=["Filesystem discovery"],
        dry_run=False,
    )

    assert result.source_remaining == 0
    assert result.destination_total == 1
    assert source.with_suffix(".yaml.bak").exists()
    assert destination.with_suffix(".yaml.bak").exists()

    yaml = YAML(typ="safe")
    source_data = yaml.load(source.read_text(encoding="utf-8"))
    destination_data = yaml.load(destination.read_text(encoding="utf-8"))
    source_template = source_data["zabbix_export"]["templates"][0]
    moved_rule = destination_data["zabbix_export"]["templates"][0]["discovery_rules"][0]

    assert "discovery_rules" not in source_template
    assert moved_rule["key"] == "vfs.fs.discovery"
    assert len(moved_rule["item_prototypes"]) == 1
    assert len(moved_rule["trigger_prototypes"]) == 1
    assert len(moved_rule["overrides"]) == 1
    assert len(moved_rule["preprocessing"]) == 1


def test_move_lld_rejects_duplicate_destination_rule(tmp_path: Path) -> None:
    source, destination = _write_templates(tmp_path)
    destination.write_text(SOURCE.replace("TEMPLATE_BASE", "TEMPLATE_SYSTEM"), encoding="utf-8")

    with pytest.raises(TemplateFormatError, match="already contains"):
        move_discovery_rules(
            load_template(source),
            load_template(destination),
            move_all=True,
            dry_run=False,
        )
