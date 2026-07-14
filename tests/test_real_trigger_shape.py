from pathlib import Path

from ztt.layers import create_layered_templates
from ztt.loader import load_template


def test_dependencies_inside_item_trigger_are_rewritten(tmp_path: Path) -> None:
    source = tmp_path / "source.yaml"
    source.write_text(
        """zabbix_export:
  version: '7.4'
  templates:
    - uuid: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
      template: WINDOWS
      name: Windows
      groups:
        - name: Templates/Test
      items:
        - uuid: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
          name: Memory
          key: vm.memory.util
          triggers:
            - uuid: cccccccccccccccccccccccccccccccc
              name: High memory
              expression: min(/WINDOWS/vm.memory.util,5m)>90
        - uuid: dddddddddddddddddddddddddddddddd
          name: Page table
          key: page.table
          triggers:
            - uuid: eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee
              name: Low page table
              expression: max(/WINDOWS/page.table,5m)<5000
              dependencies:
                - name: High memory
                  expression: min(/WINDOWS/vm.memory.util,5m)>90
""",
        encoding="utf-8",
    )

    result = create_layered_templates(load_template(source), tmp_path / "out")
    system = load_template(result.system_file)
    low_page_table = next(
        trigger
        for trigger in system.document["zabbix_export"]["triggers"]
        if trigger["name"] == "Low page table"
    )
    assert "/WINDOWS_SYSTEM/page.table" in low_page_table["expression"]
    assert "/WINDOWS_SYSTEM/vm.memory.util" in low_page_table["dependencies"][0]["expression"]
