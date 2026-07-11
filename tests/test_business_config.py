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
        business_tags={"layer": "business", "application": "oracle"},
        filesystem_matches=r"^(D:|E:)$",
        service_matches=r"^Oracle.*",
    )

    system = load_template(result.system_file)
    business = load_template(result.business_file)

    assert result.business_file.name == "WINDOWS_Oracle.yaml"
    assert result.business_template == "WINDOWS_Oracle"
    assert system.template["tags"][0]["value"] == "system"
    assert business.template["templates"] == [{"name": "WINDOWS_SYSTEM"}]
    assert business.template["tags"][1] == {"tag": "application", "value": "oracle"}
    macro_names = {macro["macro"] for macro in business.template["macros"]}
    assert "{$BUSINESS.FS.MATCHES}" in macro_names
    assert "{$BUSINESS.SERVICE.MATCHES}" in macro_names
