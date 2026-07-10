from pathlib import Path

from ztt.layers import create_base_system_layers
from ztt.loader import load_template


SAMPLE = Path(__file__).parent / "samples" / "template.yaml"


def test_create_base_and_system_layers(tmp_path: Path) -> None:
    result = create_base_system_layers(
        load_template(SAMPLE),
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
    assert base.template["uuid"] != system.template["uuid"]


def test_refuse_existing_outputs(tmp_path: Path) -> None:
    source = load_template(SAMPLE)
    create_base_system_layers(source, tmp_path, prefix="TEMPLATE_TEST")

    try:
        create_base_system_layers(source, tmp_path, prefix="TEMPLATE_TEST")
    except FileExistsError:
        pass
    else:
        raise AssertionError("Existing outputs must be rejected without overwrite=True")
