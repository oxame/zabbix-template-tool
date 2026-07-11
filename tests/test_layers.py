from pathlib import Path
from typing import Any

from ztt.layers import create_base_system_layers
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


def test_create_base_and_system_layers(tmp_path: Path) -> None:
    source = load_template(SAMPLE)
    result = create_base_system_layers(
        source,
        tmp_path,
        prefix="TEMPLATE_TEST",
    )

    assert result.base_file.exists()
    assert result.system_file.exists()
    assert result.discovery_rules == 1

    base = load_template(result.base_file)
    system = load_template(result.system_file)

    assert base.template["template"] == "TEMPLATE_TEST_BASE"
    assert "discovery_rules" not in base.template
    assert len(base.template["items"]) == 1

    assert system.template["template"] == "TEMPLATE_TEST_SYSTEM"
    assert len(system.template["discovery_rules"]) == 1
    assert "items" not in system.template
    assert system.template["templates"] == [{"name": "TEMPLATE_TEST_BASE"}]

    source_uuids = _collect_uuids(source.document)
    base_uuids = _collect_uuids(base.document)
    system_uuids = _collect_uuids(system.document)
    assert source_uuids.isdisjoint(base_uuids)
    assert source_uuids.isdisjoint(system_uuids)
    assert base_uuids.isdisjoint(system_uuids)


def test_refuse_existing_outputs(tmp_path: Path) -> None:
    source = load_template(SAMPLE)
    create_base_system_layers(source, tmp_path, prefix="TEMPLATE_TEST")

    try:
        create_base_system_layers(source, tmp_path, prefix="TEMPLATE_TEST")
    except FileExistsError:
        pass
    else:
        raise AssertionError("Existing outputs must be rejected without overwrite=True")
