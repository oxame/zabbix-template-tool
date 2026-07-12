import json
from pathlib import Path
from typing import Any

import pytest

from ztt.profiles import ZabbixProfile
from ztt.zabbix_api import ZabbixAPIClient, ZabbixAPIError


class _Response:
    def __init__(self, document: dict[str, Any]) -> None:
        self._data = json.dumps(document).encode("utf-8")

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._data


def _profile() -> ZabbixProfile:
    return ZabbixProfile(
        name="qual",
        url="https://zabbix.example/api_jsonrpc.php",
        token_env="TOKEN",
        ca_file=Path("/tmp/ca.pem"),
    )


def test_version_sends_bearer_token(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_urlopen(request: Any, **kwargs: Any) -> _Response:
        captured["authorization"] = request.get_header("Authorization")
        captured["payload"] = json.loads(request.data)
        captured["timeout"] = kwargs["timeout"]
        return _Response({"jsonrpc": "2.0", "result": "7.4.9", "id": 1})

    monkeypatch.setattr("ztt.zabbix_api.urlopen", fake_urlopen)
    monkeypatch.setattr("ztt.zabbix_api.ssl.create_default_context", lambda **kwargs: object())

    client = ZabbixAPIClient(_profile(), "secret-token")

    assert client.version() == "7.4.9"
    assert captured["authorization"] == "Bearer secret-token"
    assert captured["payload"]["method"] == "apiinfo.version"
    assert captured["timeout"] == 30


def test_list_templates_returns_summaries(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request: Any, **kwargs: Any) -> _Response:
        payload = json.loads(request.data)
        assert payload["method"] == "template.get"
        assert payload["params"]["search"] == {"name": "Windows", "host": "Windows"}
        return _Response(
            {
                "jsonrpc": "2.0",
                "result": [
                    {"templateid": "10001", "host": "Windows technical", "name": "Windows"}
                ],
                "id": 1,
            }
        )

    monkeypatch.setattr("ztt.zabbix_api.urlopen", fake_urlopen)
    monkeypatch.setattr("ztt.zabbix_api.ssl.create_default_context", lambda **kwargs: object())

    templates = ZabbixAPIClient(_profile(), "token").list_templates("Windows")

    assert templates[0].templateid == "10001"
    assert templates[0].host == "Windows technical"


def test_json_rpc_error_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "ztt.zabbix_api.urlopen",
        lambda *args, **kwargs: _Response(
            {
                "jsonrpc": "2.0",
                "error": {"code": -32602, "message": "Invalid params.", "data": "Permission denied"},
                "id": 1,
            }
        ),
    )
    monkeypatch.setattr("ztt.zabbix_api.ssl.create_default_context", lambda **kwargs: object())

    with pytest.raises(ZabbixAPIError, match="Permission denied"):
        ZabbixAPIClient(_profile(), "token").list_templates()
