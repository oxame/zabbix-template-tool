"""Zabbix JSON-RPC client using API tokens."""

from __future__ import annotations

import json
import ssl
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ztt.profiles import ZabbixProfile


class ZabbixAPIError(RuntimeError):
    """Raised for transport errors and JSON-RPC errors returned by Zabbix."""


@dataclass(slots=True, frozen=True)
class ZabbixTemplateSummary:
    templateid: str
    host: str
    name: str


class ZabbixAPIClient:
    def __init__(self, profile: ZabbixProfile, token: str) -> None:
        self.profile = profile
        self.token = token
        self._request_id = 0

    @classmethod
    def from_profile(cls, profile: ZabbixProfile) -> "ZabbixAPIClient":
        return cls(profile, profile.token())

    def _ssl_context(self) -> ssl.SSLContext:
        if not self.profile.verify_tls:
            return ssl._create_unverified_context()  # noqa: S323
        if self.profile.ca_file is not None:
            return ssl.create_default_context(cafile=str(self.profile.ca_file))
        return ssl.create_default_context()

    def call(self, method: str, params: dict[str, Any] | list[Any] | None = None) -> Any:
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": {} if params is None else params,
            "id": self._request_id,
        }
        request = Request(
            self.profile.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json-rpc",
                "Authorization": f"Bearer {self.token}",
                "User-Agent": "zabbix-template-tool",
            },
            method="POST",
        )
        try:
            with urlopen(
                request,
                timeout=self.profile.timeout,
                context=self._ssl_context(),
            ) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            raise ZabbixAPIError(
                f"Zabbix API returned HTTP {exc.code} for profile '{self.profile.name}'."
            ) from exc
        except URLError as exc:
            raise ZabbixAPIError(
                f"Cannot reach Zabbix profile '{self.profile.name}': {exc.reason}"
            ) from exc
        except TimeoutError as exc:
            raise ZabbixAPIError(
                f"Zabbix profile '{self.profile.name}' timed out after "
                f"{self.profile.timeout:g} seconds."
            ) from exc

        try:
            document = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ZabbixAPIError("Zabbix API returned invalid JSON.") from exc
        if not isinstance(document, dict):
            raise ZabbixAPIError("Zabbix API returned an unexpected JSON document.")
        error = document.get("error")
        if isinstance(error, dict):
            code = error.get("code", "unknown")
            message = error.get("message", "API error")
            data = error.get("data")
            suffix = f": {data}" if data else ""
            raise ZabbixAPIError(f"Zabbix API error {code}: {message}{suffix}")
        if "result" not in document:
            raise ZabbixAPIError("Zabbix API response does not contain a result.")
        return document["result"]

    def version(self) -> str:
        result = self.call("apiinfo.version")
        if not isinstance(result, str):
            raise ZabbixAPIError("apiinfo.version returned an invalid value.")
        return result

    def list_templates(self, search: str | None = None) -> list[ZabbixTemplateSummary]:
        params: dict[str, Any] = {
            "output": ["templateid", "host", "name"],
            "sortfield": "name",
        }
        if search:
            params["search"] = {"name": search, "host": search}
            params["searchByAny"] = True
        result = self.call("template.get", params)
        if not isinstance(result, list):
            raise ZabbixAPIError("template.get returned an invalid value.")
        templates: list[ZabbixTemplateSummary] = []
        for item in result:
            if not isinstance(item, dict):
                continue
            templates.append(
                ZabbixTemplateSummary(
                    templateid=str(item.get("templateid", "")),
                    host=str(item.get("host", "")),
                    name=str(item.get("name", "")),
                )
            )
        return templates

    def resolve_template(self, name: str) -> ZabbixTemplateSummary:
        exact = [item for item in self.list_templates(name) if name in {item.host, item.name}]
        if not exact:
            raise ZabbixAPIError(f"Template '{name}' was not found.")
        if len(exact) > 1:
            matches = ", ".join(f"{item.host} ({item.templateid})" for item in exact)
            raise ZabbixAPIError(f"Template name '{name}' is ambiguous: {matches}")
        return exact[0]

    def export_template(self, name: str, *, export_format: str = "yaml") -> str:
        template = self.resolve_template(name)
        result = self.call(
            "configuration.export",
            {
                "format": export_format,
                "options": {"templates": [template.templateid]},
            },
        )
        if not isinstance(result, str) or not result.strip():
            raise ZabbixAPIError("configuration.export returned an empty or invalid document.")
        return result

    def test_connection(self) -> tuple[str, int]:
        version = self.version()
        templates = self.list_templates()
        return version, len(templates)
