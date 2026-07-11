from pathlib import Path

from ztt.business import create_business_template
from ztt.loader import load_template


def test_create_additional_business_with_filesystem_and_service_lld(tmp_path: Path) -> None:
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
              name: FS raw data
              type: DEPENDENT
              key: vfs.fs.dependent[{#FSNAME},data]
              value_type: TEXT
              master_item:
                key: vfs.fs.get
            - uuid: 66666666666666666666666666666666
              name: FS used
              type: DEPENDENT
              key: vfs.fs.dependent.size[{#FSNAME},used]
              master_item:
                key: vfs.fs.dependent[{#FSNAME},data]
        - uuid: 44444444444444444444444444444444
          name: Windows services discovery
          type: DEPENDENT
          key: ztt.system.service.discovery
          master_item:
            key: service.discovery
          item_prototypes:
            - uuid: 55555555555555555555555555555555
              name: Service state
              key: service.info[{#SERVICE.NAME},state]
              valuemap:
                name: Windows service state
      valuemaps:
        - uuid: 77777777777777777777777777777777
          name: Windows service state
          mappings:
            - value: '0'
              newvalue: Running
        - uuid: 88888888888888888888888888888888
          name: Unused map
          mappings:
            - value: '1'
              newvalue: Unused
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
    assert result.service_rules == 1
    assert result.skipped_service_rules == 0
    assert business.template["templates"] == [{"name": "WINDOWS_SYSTEM"}]

    filesystem_rule, service_rule = business.template["discovery_rules"]
    assert filesystem_rule["key"] == "ztt.business.bdd.fs.discovery"
    raw, used = filesystem_rule["item_prototypes"]
    assert raw["key"] == "ztt.business.bdd.vfs.fs.dependent[{#FSNAME},data]"
    assert used["key"] == "ztt.business.bdd.vfs.fs.dependent.size[{#FSNAME},used]"
    assert used["master_item"]["key"] == raw["key"]
    assert filesystem_rule["master_item"]["key"] == "vfs.fs.get"

    assert service_rule["key"] == "ztt.business.bdd.service.discovery"
    assert service_rule["item_prototypes"][0]["key"] == (
        "ztt.business.bdd.service.info[{#SERVICE.NAME},state]"
    )
    assert service_rule["item_prototypes"][0]["valuemap"] == {
        "name": "Windows service state"
    }
    assert service_rule["master_item"]["key"] == "service.discovery"

    inherited_keys = {
        "vfs.fs.dependent[{#FSNAME},data]",
        "vfs.fs.dependent.size[{#FSNAME},used]",
        "service.info[{#SERVICE.NAME},state]",
    }
    generated_keys = {
        prototype["key"]
        for rule in business.template["discovery_rules"]
        for prototype in rule.get("item_prototypes", [])
    }
    assert inherited_keys.isdisjoint(generated_keys)

    assert business.template["valuemaps"] == [
        {
            "uuid": business.template["valuemaps"][0]["uuid"],
            "name": "Windows service state",
            "mappings": [{"value": "0", "newvalue": "Running"}],
        }
    ]
    assert business.template["tags"] == [
        {"tag": "layer", "value": "business"},
        {"tag": "application", "value": "bdd"},
    ]
    macros = {entry["macro"]: entry["value"] for entry in business.template["macros"]}
    assert macros["{$BUSINESS.FS.MATCHES}"] == "data|u01"
    assert macros["{$BUSINESS.SERVICE.MATCHES}"] == "Oracle.*"
