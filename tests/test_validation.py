from pathlib import Path

from ztt.loader import load_template
from ztt.validation import validate_template


def _write_template(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


def test_validation_reports_missing_valuemap(tmp_path: Path) -> None:
    template_file = tmp_path / "business.yaml"
    _write_template(
        template_file,
        """zabbix_export:
  version: '7.4'
  templates:
    - uuid: 11111111111111111111111111111111
      template: WINDOWS_BDD
      name: Windows BDD
      groups:
        - name: Templates/Test
      discovery_rules:
        - uuid: 22222222222222222222222222222222
          name: Windows services discovery - BUSINESS bdd
          key: ztt.business.bdd.service.discovery
          item_prototypes:
            - uuid: 33333333333333333333333333333333
              name: Service state
              key: ztt.business.bdd.service.info[{#SERVICE.NAME},state]
              valuemap:
                name: Windows service state
""",
    )

    report = validate_template(load_template(template_file))

    assert not report.valid
    assert [issue.code for issue in report.issues] == ["missing_valuemap"]
    assert "Windows service state" in report.issues[0].message


def test_validation_accepts_required_valuemap(tmp_path: Path) -> None:
    template_file = tmp_path / "business.yaml"
    _write_template(
        template_file,
        """zabbix_export:
  version: '7.4'
  templates:
    - uuid: 11111111111111111111111111111111
      template: WINDOWS_BDD
      name: Windows BDD
      groups:
        - name: Templates/Test
      discovery_rules:
        - uuid: 22222222222222222222222222222222
          name: Windows services discovery - BUSINESS bdd
          key: ztt.business.bdd.service.discovery
          item_prototypes:
            - uuid: 33333333333333333333333333333333
              name: Service state
              key: ztt.business.bdd.service.info[{#SERVICE.NAME},state]
              valuemap:
                name: Windows service state
      valuemaps:
        - uuid: 44444444444444444444444444444444
          name: Windows service state
          mappings:
            - value: '0'
              newvalue: Running
""",
    )

    report = validate_template(load_template(template_file))

    assert report.valid


def test_validation_reports_duplicate_prototype_key(tmp_path: Path) -> None:
    template_file = tmp_path / "business.yaml"
    _write_template(
        template_file,
        """zabbix_export:
  version: '7.4'
  templates:
    - uuid: 11111111111111111111111111111111
      template: WINDOWS_BDD
      name: Windows BDD
      groups:
        - name: Templates/Test
      discovery_rules:
        - uuid: 22222222222222222222222222222222
          name: Filesystems
          key: ztt.business.bdd.fs.discovery
          item_prototypes:
            - uuid: 33333333333333333333333333333333
              name: First
              key: ztt.business.bdd.same[{#FSNAME}]
            - uuid: 44444444444444444444444444444444
              name: Second
              key: ztt.business.bdd.same[{#FSNAME}]
""",
    )

    report = validate_template(load_template(template_file))

    assert not report.valid
    assert [issue.code for issue in report.issues] == ["duplicate_prototype_key"]
