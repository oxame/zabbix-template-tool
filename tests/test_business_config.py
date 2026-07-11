from pathlib import Path

from ztt.layers import create_layered_templates
from ztt.loader import load_template


SAMPLE = Path(__file__).parent / "samples" / "template.yaml"


def test_business_name_macros_and_tags(tmp_path: Path) -> None:
    result = create_layered_templates(
        load_template(SAMPLE),
        tmp_path,
        prefix="WINDOWS",
        business_name="Oracle",
        system_tags={"layer": "system", "technology": "windows"},
        business_tags={
            "layer": "business",
            "application": "oracle",
            "responsibility": "DBA",
        },
        filesystem_matches=r"^(D:|E:)$",
        filesystem_not_matches=r"^C:$",
        service_matches=r"^Oracle.*",
        service_not_matches="",
    )

    system = load_template(result.system_file)
    business = load_template(result.business_file)

    assert result.business_file.name == "WINDOWS_Oracle.yaml"
    assert result.business_template == "WINDOWS_Oracle"
    assert system.template["tags"] == [
        {"tag": "layer", "value": "system"},
        {"tag": "technology", "value": "windows"},
    ]
    assert business.template["templates"] == [{"name": "WINDOWS_SYSTEM"}]
    assert business.template["tags"] == [
        {"tag": "layer", "value": "business"},
        {"tag": "application", "value": "oracle"},
        {"tag": "responsibility", "value": "DBA"},
    ]
    assert business.template["macros"] == [
        {"macro": "{$BUSINESS.FS.MATCHES}", "value": r"^(D:|E:)$"},
        {"macro": "{$BUSINESS.FS.NOT_MATCHES}", "value": r"^C:$"},
        {"macro": "{$BUSINESS.SERVICE.MATCHES}", "value": r"^Oracle.*"},
        {"macro": "{$BUSINESS.SERVICE.NOT_MATCHES}", "value": ""},
    ]
