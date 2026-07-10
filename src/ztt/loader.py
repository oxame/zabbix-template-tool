"""YAML loading utilities."""

from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from ztt.template import TemplateFormatError, ZabbixTemplate


def load_template(path: Path) -> ZabbixTemplate:
    """Load and validate the basic structure of a Zabbix YAML template export."""
    if not path.exists():
        raise FileNotFoundError(f"Template file not found: {path}")
    if not path.is_file():
        raise TemplateFormatError(f"The path is not a file: {path}")

    yaml = YAML(typ="rt")
    try:
        with path.open("r", encoding="utf-8") as stream:
            document = yaml.load(stream)
    except YAMLError as exc:
        raise TemplateFormatError(f"Invalid YAML in {path}: {exc}") from exc

    return ZabbixTemplate.from_document(path, document)
