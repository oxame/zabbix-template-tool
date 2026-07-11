from pathlib import Path
from shutil import copy2

from typer.testing import CliRunner

from ztt.cli import app


SAMPLE = Path(__file__).parent / "samples" / "template.yaml"


def test_create_layers_defaults_to_source_directory(tmp_path: Path) -> None:
    source = tmp_path / "template.yaml"
    copy2(SAMPLE, source)

    result = CliRunner().invoke(
        app,
        ["create-layers", str(source), "--prefix", "TEMPLATE_TEST"],
    )

    assert result.exit_code == 0, result.output
    assert (tmp_path / "TEMPLATE_TEST_BASE.yaml").exists()
    assert (tmp_path / "TEMPLATE_TEST_SYSTEM.yaml").exists()
    assert not (Path.cwd() / "layers" / "TEMPLATE_TEST_BASE.yaml").exists()


def test_create_layers_accepts_output_directory(tmp_path: Path) -> None:
    source = tmp_path / "template.yaml"
    output = tmp_path / "generated"
    copy2(SAMPLE, source)

    result = CliRunner().invoke(
        app,
        [
            "create-layers",
            str(source),
            "--output-dir",
            str(output),
            "--prefix",
            "TEMPLATE_TEST",
        ],
    )

    assert result.exit_code == 0, result.output
    assert (output / "TEMPLATE_TEST_BASE.yaml").exists()
    assert (output / "TEMPLATE_TEST_SYSTEM.yaml").exists()
