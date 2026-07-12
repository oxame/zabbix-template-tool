from pathlib import Path

import pytest

from ztt.loader import load_template
from ztt.merge import merge_templates


def _template(path: Path, name: str, item_key: str, macro_value: str) -> Path:
    path.write_text(
        f"""zabbix_export:
  version: '7.4'
  templates:
    - uuid: 11111111111111111111111111111111
      template: {name}
      name: {name}
      groups:
        - name: Templates/Test
      items:
        - uuid: 22222222222222222222222222222222
          name: {item_key}
          key: {item_key}
      macros:
        - macro: '{{$TEST}}'
          value: '{macro_value}'
""",
        encoding="utf-8",
    )
    return path


def _business_template(path: Path, name: str, namespace: str) -> Path:
    path.write_text(
        f"""zabbix_export:
  version: '7.4'
  templates:
    - uuid: 11111111111111111111111111111111
      template: {name}
      name: {name}
      groups:
        - name: Templates/Test
      discovery_rules:
        - uuid: 22222222222222222222222222222222
          name: Filesystem discovery {namespace}
          key: ztt.business.{namespace}.fs.discovery
          item_prototypes:
            - uuid: 33333333333333333333333333333333
              name: Used percent
              key: ztt.business.{namespace}.fs.size[{{#FSNAME}},pused]
          graph_prototypes:
            - uuid: 44444444444444444444444444444444
              name: Space usage
              graph_items:
                - item:
                    host: {name}
                    key: ztt.business.{namespace}.fs.size[{{#FSNAME}},pused]
""",
        encoding="utf-8",
    )
    return path


def test_merge_dry_run_does_not_write_output(tmp_path: Path) -> None:
    first = load_template(_template(tmp_path / "a.yaml", "A", "item.a", "a"))
    second = load_template(_template(tmp_path / "b.yaml", "B", "item.b", "b"))
    output = tmp_path / "merged.yaml"

    result = merge_templates([first, second], output)

    assert result.dry_run
    assert result.added["items"] == 1
    assert len(result.conflicts) == 1  # {$TEST}
    assert not output.exists()


def test_merge_apply_keep_last_writes_output(tmp_path: Path) -> None:
    first = load_template(_template(tmp_path / "a.yaml", "A", "item.a", "a"))
    second = load_template(_template(tmp_path / "b.yaml", "B", "item.b", "b"))
    output = tmp_path / "merged.yaml"

    result = merge_templates(
        [first, second], output, conflict_mode="keep-last", apply=True,
        template_name="MERGED",
    )

    merged = load_template(output)
    assert not result.dry_run
    assert merged.template["template"] == "MERGED"
    assert {item["key"] for item in merged.template["items"]} == {"item.a", "item.b"}
    assert merged.template["macros"][0]["value"] == "b"


def test_merge_rewrites_graph_prototype_hosts(tmp_path: Path) -> None:
    first = load_template(_business_template(tmp_path / "bdd.yaml", "WINDOWS_BDD", "bdd"))
    second = load_template(_business_template(tmp_path / "edi.yaml", "WINDOWS_EDI", "edi"))
    output = tmp_path / "merged.yaml"

    merge_templates(
        [first, second], output, conflict_mode="keep-last", apply=True,
        template_name="WINDOWS_MERGED",
    )

    merged = load_template(output)
    rules = merged.template["discovery_rules"]
    assert len(rules) == 2
    hosts = {
        item["item"]["host"]
        for rule in rules
        for graph in rule.get("graph_prototypes", [])
        for item in graph.get("graph_items", [])
    }
    assert hosts == {"WINDOWS_MERGED"}


def test_merge_error_mode_blocks_apply_on_conflict(tmp_path: Path) -> None:
    first = load_template(_template(tmp_path / "a.yaml", "A", "item.same", "a"))
    second = load_template(_template(tmp_path / "b.yaml", "B", "item.same", "b"))

    with pytest.raises(ValueError, match="Merge conflicts detected"):
        merge_templates([first, second], tmp_path / "merged.yaml", apply=True)
