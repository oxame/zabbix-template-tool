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


def test_merge_error_mode_blocks_apply_on_conflict(tmp_path: Path) -> None:
    first = load_template(_template(tmp_path / "a.yaml", "A", "item.same", "a"))
    second = load_template(_template(tmp_path / "b.yaml", "B", "item.same", "b"))

    with pytest.raises(ValueError, match="Merge conflicts detected"):
        merge_templates([first, second], tmp_path / "merged.yaml", apply=True)
