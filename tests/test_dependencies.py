from pathlib import Path

from ztt.dependencies import analyze_lld_dependencies
from ztt.loader import load_template


def test_analyze_lld_dependencies(tmp_path: Path) -> None:
    path = tmp_path / "template.yaml"
    path.write_text(
        """zabbix_export:
  version: '7.4'
  value_maps:
    - uuid: 11111111111111111111111111111111
      name: Filesystem status
      mappings: []
  templates:
    - uuid: 22222222222222222222222222222222
      template: TEMPLATE_TEST
      name: Test
      groups:
        - name: Templates/Test
      items:
        - uuid: 33333333333333333333333333333333
          name: Master
          key: master.key
      macros:
        - macro: '{$FS.WARN}'
          value: '80'
      discovery_rules:
        - uuid: 44444444444444444444444444444444
          name: Filesystem discovery
          key: vfs.fs.discovery
          filter:
            conditions:
              - macro: '{#FSNAME}'
                value: '{$FS.WARN}'
          item_prototypes:
            - uuid: 55555555555555555555555555555555
              name: Used
              key: fs.used[{#FSNAME}]
              master_item:
                key: master.key
              value_map:
                name: Filesystem status
            - uuid: 66666666666666666666666666666666
              name: Missing dependency
              key: fs.missing[{#FSNAME}]
              master_item:
                key: missing.master
              description: '{$FS.CRIT}'
""",
        encoding="utf-8",
    )

    reports = analyze_lld_dependencies(load_template(path))

    assert len(reports) == 1
    dependencies = {
        (item.kind, item.reference): item.present
        for item in reports[0].dependencies
    }
    assert dependencies[("macro", "{$FS.WARN}")] is True
    assert dependencies[("macro", "{$FS.CRIT}")] is False
    assert dependencies[("value_map", "Filesystem status")] is True
    assert dependencies[("master_item", "master.key")] is True
    assert dependencies[("master_item", "missing.master")] is False
    assert len(reports[0].missing) == 2
