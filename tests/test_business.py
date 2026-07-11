from pathlib import Path

from ztt.business import create_business_template
from ztt.loader import load_template


def test_create_additional_business_with_filesystem_lld(tmp_path: Path) -> None:
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
          filter:
            conditions:
              - macro: '{#FSNAME}'
                value: '{$VFS.FS.FSNAME.MATCHES}'
          item_prototypes:
            - uuid: 33333333333333333333333333333333
              name: FS used
              key: vfs.fs.size[{#FSNAME},used]
        - uuid: 44444444444444444444444444444444
          name: Windows services discovery
          key: service.discovery
          item_prototypes:
            - uuid: 55555555555555555555555555555555
              name: Service state
              key: service.info[{#SERVICE.NAME},state]
""",
        encoding="utf-8",
    )

    result = create_business_template(
        load_template(system_file),
        tmp_path,
        business_name="BDD",
        include_filesystems=True,
        include_services=True,
        filesystem_matches="data|u01",
        filesystem_not_matches="^C:$",
        service_matches="Oracle.*",
        service_not_matches="",
        business_tags={"layer": "business", "application": "bdd"},
    )

    business = load_template(result.file)
    assert result.file.name == "WINDOWS_BDD.yaml"
    assert result.filesystem_rules == 1
    assert result.service_rules == 0
    assert result.skipped_service_rules == 1
    assert business.template["templates"] == [{"name": "WINDOWS_SYSTEM"}]
    rule = business.template["discovery_rules"][0]
    assert rule["key"] == "ztt.business.bdd.fs.discovery"
    assert rule["item_prototypes"][0]["key"] == "ztt.business.bdd.vfs.fs.size[{#FSNAME},used]"
    assert rule["master_item"]["key"] == "vfs.fs.get"
    assert business.template["tags"] == [
        {"tag": "layer", "value": "business"},
        {"tag": "application", "value": "bdd"},
    ]
    assert business.template["macros"][0] == {
        "macro": "{$BUSINESS.FS.MATCHES}",
        "value": "data|u01",
    }
