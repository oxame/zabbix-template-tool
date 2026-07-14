from pathlib import Path

from ztt.business import create_business_template
from ztt.layers import create_layered_templates
from ztt.loader import load_template
from ztt.naming import rename_business_template, rename_layered_templates


SAMPLE = Path(__file__).parent / "samples" / "template.yaml"


def test_rename_all_layers_and_links(tmp_path: Path) -> None:
    generated = create_layered_templates(
        load_template(SAMPLE),
        tmp_path,
        prefix="temporary",
        business_name="BDD",
    )
    result = rename_layered_templates(
        generated,
        base_name="EFS - Linux agent actif BASE",
        system_name="EFS - Linux agent actif SYSTEM",
        business_name="EFS - Linux agent actif BDD",
    )

    base = load_template(result.base_file)
    system = load_template(result.system_file)
    business = load_template(result.business_file)

    assert result.base_file.name == "EFS_-_Linux_agent_actif_BASE.yaml"
    assert result.system_file.name == "EFS_-_Linux_agent_actif_SYSTEM.yaml"
    assert result.business_file.name == "EFS_-_Linux_agent_actif_BDD.yaml"
    assert base.template["template"] == "EFS - Linux agent actif BASE"
    assert base.template["name"] == "EFS - Linux agent actif BASE"
    assert system.template["templates"] == [{"name": "EFS - Linux agent actif BASE"}]
    assert business.template["templates"] == [{"name": "EFS - Linux agent actif SYSTEM"}]


def test_rename_additional_business_template(tmp_path: Path) -> None:
    layers = create_layered_templates(
        load_template(SAMPLE),
        tmp_path,
        prefix="temporary",
    )
    renamed = rename_layered_templates(
        layers,
        base_name="EFS - Windows actif BASE",
        system_name="EFS - Windows actif SYSTEM",
        business_name="EFS - Windows actif BUSINESS",
    )
    generated = create_business_template(
        load_template(renamed.system_file),
        tmp_path,
        business_name="SQL",
    )
    result = rename_business_template(
        generated,
        template_name="EFS - Windows actif SQL",
    )

    business = load_template(result.file)
    assert result.file.name == "EFS_-_Windows_actif_SQL.yaml"
    assert business.template["template"] == "EFS - Windows actif SQL"
    assert business.template["name"] == "EFS - Windows actif SQL"
    assert business.template["templates"] == [{"name": "EFS - Windows actif SYSTEM"}]
