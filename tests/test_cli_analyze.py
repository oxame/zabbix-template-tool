"""Regression tests for the analyze CLI rendering."""

from io import StringIO
from pathlib import Path

from rich.console import Console

from ztt import cli
from ztt.dependencies import Dependency, RuleDependencyReport


def test_analyze_renders_zabbix_references_as_literal_text(monkeypatch) -> None:
    """Zabbix keys containing brackets must not be parsed as Rich markup."""
    report = RuleDependencyReport(
        rule_name="Network interface discovery [active]",
        rule_key='net.if.discovery["{#IFNAME}"]',
        dependencies=(
            Dependency(
                kind="master_item",
                reference='net.if.in["{#IFNAME}"]',
                present=True,
                location="rule.item_prototypes[0].master_item",
            ),
        ),
    )
    output = StringIO()

    monkeypatch.setattr(cli, "console", Console(file=output, force_terminal=False, width=160))
    monkeypatch.setattr(cli, "load_template", lambda _path: object())
    monkeypatch.setattr(cli, "analyze_lld_dependencies", lambda _template: [report])

    cli.analyze(Path("template.yaml"))

    rendered = output.getvalue()
    assert "Network interface discovery [active]" in rendered
    assert 'net.if.discovery["{#IFNAME}"]' in rendered
    assert 'net.if.in["{#IFNAME}"]' in rendered
    assert "rule.item_prototypes[0].master_item" in rendered
