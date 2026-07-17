from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from ztt.profiles import ProfileError, ZabbixProfile, load_profiles
from ztt.zabbix_api import ZabbixAPIClient, ZabbixAPIError


def test_load_profiles_qual_and_prod(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    config.write_text(
        """
profiles:
  qual:
    url: https://qual.example/zabbix
    token_env: QUAL_TOKEN
  prod:
    url: https://prod.example/zabbix/api_jsonrpc.php
    token_env: PROD_TOKEN
    production: true
""".strip(),
        encoding="utf-8",
    )

    profiles = load_profiles(config)

    assert profiles["qual"].url == "https://qual.example/zabbix/api_jsonrpc.php"
    assert profiles["qual"].production is False
    assert profiles["prod"].url == "https://prod.example/zabbix/api_jsonrpc.php"
    assert profiles["prod"].production is True


def test_profile_requires_environment_token() -> None:
    profile = ZabbixProfile("qual", "https://example/api_jsonrpc.php", "MISSING_TOKEN")
    with pytest.raises(ProfileError, match="MISSING_TOKEN"):
        profile.token({})


def test_version_omits_authorization_header(monkeypatch: pytest.MonkeyPatch) -> None:
    profile = ZabbixProfile("qual", "https://example/api_jsonrpc.php", "TOKEN")
    client = ZabbixAPIClient(profile, "secret")
    captured: dict[str, Any] = {}

    class Response:
        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return b'{"jsonrpc":"2.0","result":"7.4.0","id":1}'

    def fake_urlopen(request: object, **kwargs: object) -> Response:
        captured["headers"] = dict(request.header_items())  # type: ignore[attr-defined]
        captured["payload"] = json.loads(request.data.decode("utf-8"))  # type: ignore[attr-defined]
        return Response()

    monkeypatch.setattr("ztt.zabbix_api.urlopen", fake_urlopen)

    assert client.version() == "7.4.0"
    assert "Authorization" not in captured["headers"]
    assert captured["payload"]["method"] == "apiinfo.version"


def test_authenticated_call_sends_bearer_token(monkeypatch: pytest.MonkeyPatch) -> None:
    profile = ZabbixProfile("qual", "https://example/api_jsonrpc.php", "TOKEN")
    client = ZabbixAPIClient(profile, "secret")
    captured: dict[str, Any] = {}

    class Response:
        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return b'{"jsonrpc":"2.0","result":[],"id":1}'

    def fake_urlopen(request: object, **kwargs: object) -> Response:
        captured["headers"] = dict(request.header_items())  # type: ignore[attr-defined]
        return Response()

    monkeypatch.setattr("ztt.zabbix_api.urlopen", fake_urlopen)

    assert client.call("template.get", {"output": []}) == []
    assert captured["headers"]["Authorization"] == "Bearer secret"


def test_resolve_template_rejects_ambiguous_name(monkeypatch: pytest.MonkeyPatch) -> None:
    profile = ZabbixProfile("qual", "https://example/api_jsonrpc.php", "TOKEN")
    client = ZabbixAPIClient(profile, "secret")
    monkeypatch.setattr(
        client,
        "list_templates",
        lambda search=None: [
            type("T", (), {"templateid": "1", "host": "Same", "name": "One"})(),
            type("T", (), {"templateid": "2", "host": "Other", "name": "Same"})(),
        ],
    )

    with pytest.raises(ZabbixAPIError, match="ambiguous"):
        client.resolve_template("Same")


def test_export_template_calls_configuration_export(monkeypatch: pytest.MonkeyPatch) -> None:
    profile = ZabbixProfile("qual", "https://example/api_jsonrpc.php", "TOKEN")
    client = ZabbixAPIClient(profile, "secret")
    calls: list[tuple[str, object]] = []

    monkeypatch.setattr(
        client,
        "resolve_template",
        lambda name: type("T", (), {"templateid": "42"})(),
    )

    def fake_call(method: str, params: object = None) -> object:
        calls.append((method, params))
        return "zabbix_export:\n  version: '7.4'\n"

    monkeypatch.setattr(client, "call", fake_call)

    exported = client.export_template("Windows by Zabbix agent")

    assert exported.startswith("zabbix_export:")
    assert calls == [
        (
            "configuration.export",
            {"format": "yaml", "options": {"templates": ["42"]}},
        )
    ]
