from pathlib import Path

from ztt.layers import create_layered_templates
from ztt.loader import load_template


def test_move_embedded_and_top_level_triggers_to_system(tmp_path: Path) -> None:
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
          name: Agent ping
          key: agent.ping
          triggers:
            - uuid: 33333333333333333333333333333333
              name: Agent unavailable
              expression: nodata(/ORIGINAL/agent.ping,5m)=1
        - uuid: 44444444444444444444444444444444
          name: Memory utilization
          key: vm.memory.util
          triggers:
            - uuid: 55555555555555555555555555555555
              name: High memory utilization
              expression: min(/ORIGINAL/vm.memory.util,5m)>90
              dependencies:
                - name: Agent unavailable
                  expression: nodata(/ORIGINAL/agent.ping,5m)=1
  triggers:
    - uuid: 66666666666666666666666666666666
      name: Global trigger
      expression: last(/ORIGINAL/agent.ping)=0
""",
        encoding="utf-8",
    )

    result = create_layered_templates(load_template(source_file), tmp_path / "out")
    base = load_template(result.base_file)
    system = load_template(result.system_file)
    business = load_template(result.business_file)

    assert "triggers" not in base.document["zabbix_export"]
    assert all("triggers" not in item for item in base.template["items"])

    triggers = system.document["zabbix_export"]["triggers"]
    assert {trigger["name"] for trigger in triggers} == {
        "Agent unavailable",
        "High memory utilization",
        "Global trigger",
    }
    assert all("/ORIGINAL/" not in trigger["expression"] for trigger in triggers)
    assert all("/ORIGINAL/" not in str(trigger.get("dependencies", [])) for trigger in triggers)
    assert all("/ORIGINAL_SYSTEM/" in trigger["expression"] for trigger in triggers)

    assert "triggers" not in business.document["zabbix_export"]
