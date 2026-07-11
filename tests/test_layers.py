from pathlib import Path
from typing import Any

from ztt.layers import create_layered_templates
from ztt.loader import load_template


SAMPLE = Path(__file__).parent / "samples" / "template.yaml"


def _collect_uuids(value: Any) -> set[str]:
    uuids: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "uuid" and isinstance(child, str):
                uuids.add(child)
            else:
                uuids.update(_collect_uuids(child))
    elif isinstance(value, list):
        for child in value:
            uuids.update(_collect_uuids(child))
    return uuids


def test_create_three_linked_layers(tmp_path: Path) -> None:
    source = load_template(SAMPLE)
    result = create_layered_templates(
        source,
        tmp_path,
        prefix="TEMPLATE_TEST",
    )

    assert result.base_file.exists()
    assert result.system_file.exists()
    assert result.business_file.exists()
    assert result.discovery_rules == 1

    base = load_template(result.base_file)
    system = load_template(result.system_file)
    business = load_template(result.business_file)

    assert base.template["template"] == "TEMPLATE_TEST_BASE"
    assert "discovery_rules" not in base.template
    assert len(base.template["items"]) == 1

    assert system.template["template"] == "TEMPLATE_TEST_SYSTEM"
    assert len(system.template["discovery_rules"]) == 1
    assert "items" not in system.template
    assert "dashboards" not in system.template
    assert system.template["templates"] == [{"name": "TEMPLATE_TEST_BASE"}]

    assert business.template["template"] == "TEMPLATE_TEST_BUSINESS"
    assert "items" not in business.template
    assert "discovery_rules" not in business.template
    assert "dashboards" not in business.template
    assert business.template["templates"] == [{"name": "TEMPLATE_TEST_SYSTEM"}]

    source_uuids = _collect_uuids(source.document)
    base_uuids = _collect_uuids(base.document)
    system_uuids = _collect_uuids(system.document)
    business_uuids = _collect_uuids(business.document)
    assert source_uuids.isdisjoint(base_uuids)
    assert source_uuids.isdisjoint(system_uuids)
    assert source_uuids.isdisjoint(business_uuids)
    assert base_uuids.isdisjoint(system_uuids)
    assert base_uuids.isdisjoint(business_uuids)
    assert system_uuids.isdisjoint(business_uuids)


def test_rewrite_references_copy_valuemaps_and_skip_dashboards(tmp_path: Path) -> None:
    source_file = tmp_path / "source.yaml"
    source_file.write_text(
        """zabbix_export:
  version: '7.4'
  templates:
    - uuid: 11111111111111111111111111111111
      template: ORIGINAL
      name: Original
      groups:
        - name: Templates/Test
      items:
        - uuid: 22222222222222222222222222222222
          name: Standalone item
          key: base.key
      discovery_rules:
        - uuid: 33333333333333333333333333333333
          name: LLD
          key: discovery.key
          item_prototypes:
            - uuid: 99999999999999999999999999999999
              name: Prototype item
              key: prototype.key[{#ID}]
              valuemap:
                name: Test map
          trigger_prototypes:
            - uuid: 44444444444444444444444444444444
              name: Prototype trigger
              expression: last(/ORIGINAL/prototype.key[{#ID}])=1
      macros:
        - macro: '{$TEST}'
          value: '1'
      valuemaps:
        - uuid: 55555555555555555555555555555555
          name: Test map
          mappings: []
        - uuid: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
          name: Unused map
          mappings: []
      dashboards:
        - uuid: 66666666666666666666666666666666
          name: Overview
          pages:
            - widgets:
                - type: graphprototype
                  fields:
                    - type: GRAPH_PROTOTYPE
                      name: graphid.0
                      value:
                        host: ORIGINAL
                        name: Prototype graph
  triggers:
    - uuid: 77777777777777777777777777777777
      name: Base trigger
      expression: last(/ORIGINAL/base.key)=1
  graphs:
    - uuid: 88888888888888888888888888888888
      name: Base graph
      graph_items:
        - item:
            host: ORIGINAL
            key: base.key
""",
        encoding="utf-8",
    )

    result = create_layered_templates(
        load_template(source_file),
        tmp_path / "out",
        prefix="LAYERED",
    )
    base = load_template(result.base_file)
    system = load_template(result.system_file)
    business = load_template(result.business_file)

    assert result.dashboards == 1
    assert "dashboards" not in base.template
    assert "triggers" in base.document["zabbix_export"]
    assert "graphs" in base.document["zabbix_export"]
    assert "/LAYERED_BASE/base.key" in base.document["zabbix_export"]["triggers"][0][
        "expression"
    ]
    assert (
        base.document["zabbix_export"]["graphs"][0]["graph_items"][0]["item"]["host"]
        == "LAYERED_BASE"
    )

    assert "triggers" not in system.document["zabbix_export"]
    assert "graphs" not in system.document["zabbix_export"]
    assert "dashboards" not in system.template
    assert [valuemap["name"] for valuemap in system.template["valuemaps"]] == ["Test map"]
    assert "/LAYERED_SYSTEM/prototype.key" in system.template["discovery_rules"][0][
        "trigger_prototypes"
    ][0]["expression"]

    assert business.template["templates"] == [{"name": "LAYERED_SYSTEM"}]
    assert "dashboards" not in business.template


def test_refuse_existing_outputs(tmp_path: Path) -> None:
    source = load_template(SAMPLE)
    create_layered_templates(source, tmp_path, prefix="TEMPLATE_TEST")

    try:
        create_layered_templates(source, tmp_path, prefix="TEMPLATE_TEST")
    except FileExistsError:
        pass
    else:
        raise AssertionError("Existing outputs must be rejected without overwrite=True")
