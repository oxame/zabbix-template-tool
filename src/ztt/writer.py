"""YAML writing utilities preserving Zabbix export structure."""

from pathlib import Path
from typing import Any

from ruamel.yaml import YAML


def write_document(path: Path, document: dict[str, Any]) -> None:
    """Write a Zabbix YAML document using round-trip formatting."""
    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    yaml.width = 4096
    with path.open("w", encoding="utf-8") as stream:
        yaml.dump(document, stream)
