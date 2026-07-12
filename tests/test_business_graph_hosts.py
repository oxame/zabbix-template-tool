from pathlib import Path

from ztt.business import create_business_template
from ztt.loader import load_template


def test_create_business_rewrites_graph_prototype_hosts(tmp_path: Path) -> None:
    system_file = tmp_path / "SYSTEM.yaml"
    system_file.write_text(
        """zabbix_export:
  version: '7.4'
  templates:
    - uuid: 11111111111111111111111111111111
      template: WINDOWS_SYSTEM
      name: Windows SYSTEM
      groups:
        - name: Templates/Test
      templates:
        - name: WINDOWS_BASE
      discovery_rules:
        - uuid: 22222222222222222222222222222222
          name: Mounted filesystem discovery
          type: DEPENDENT
          key: vfs.fs.dependent.discovery
          master_item:
            key: vfs.fs.get
          item_prototypes:
            - uuid: 33333333333333333333333333333333
              name: FS used percentage
              type: DEPENDENT
              key: vfs.fs.dependent.size[{#FSNAME},pused]
              master_item:
                key: vfs.fs.get
          graph_prototypes:
            - uuid: 44444444444444444444444444444444
              name: FS usage
              graph_items:
                - item:
                    host: WINDOWS_SYSTEM
                    key: vfs.fs.dependent.size[{#FSNAME},pused]
""",
        encoding="utf-8",
    )

    result = create_business_template(
        load_template(system_file),
        tmp_path,
        business_name="EDI",
        include_filesystems=True,
        filesystem_matches=".*",
        filesystem_not_matches="",
    )

    business = load_template(result.file)
    graph_item = business.template["discovery_rules"][0]["graph_prototypes"][0][
        "graph_items"
    ][0]["item"]

    assert graph_item["host"] == "WINDOWS_EDI"
    assert graph_item["key"] == "ztt.business.edi.vfs.fs.dependent.size[{#FSNAME},pused]"
    assert business.template["templates"] == [{"name": "WINDOWS_SYSTEM"}]
