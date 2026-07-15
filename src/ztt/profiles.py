"""Load named Zabbix API profiles without storing secrets in configuration files."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML


class ProfileError(ValueError):
    """Raised when the local ZTT profile configuration is invalid."""


def default_config_path() -> Path:
    override = os.environ.get("ZTT_CONFIG")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".config" / "ztt" / "config.yaml"


@dataclass(slots=True, frozen=True)
class ZabbixProfile:
    name: str
    url: str
    token_env: str
    production: bool = False
    verify_tls: bool = True
    ca_file: Path | None = None
    timeout: float = 30.0

    def token(self, environ: dict[str, str] | None = None) -> str:
        values = os.environ if environ is None else environ
        token = values.get(self.token_env, "").strip()
        if not token:
            raise ProfileError(
                f"Environment variable '{self.token_env}' is not set for profile '{self.name}'."
            )
        return token


def _normalise_api_url(value: str) -> str:
    url = value.strip().rstrip("/")
    if not url:
        raise ProfileError("Profile URL cannot be empty.")
    if not url.endswith("api_jsonrpc.php"):
        url = f"{url}/api_jsonrpc.php"
    return url


def load_profiles(path: Path | None = None) -> dict[str, ZabbixProfile]:
    config_path = default_config_path() if path is None else path.expanduser()
    if not config_path.exists():
        raise FileNotFoundError(
            f"ZTT configuration file not found: {config_path}. "
            "Create it with QUAL/PROD profiles before using API commands."
        )

    yaml = YAML(typ="safe")
    with config_path.open("r", encoding="utf-8") as stream:
        document = yaml.load(stream) or {}
    if not isinstance(document, dict):
        raise ProfileError("The ZTT configuration root must be a mapping.")

    raw_profiles = document.get("profiles")
    if not isinstance(raw_profiles, dict) or not raw_profiles:
        raise ProfileError("The configuration must contain a non-empty 'profiles' mapping.")

    profiles: dict[str, ZabbixProfile] = {}
    for raw_name, raw_value in raw_profiles.items():
        if not isinstance(raw_name, str) or not raw_name.strip():
            raise ProfileError("Every profile must have a non-empty name.")
        name = raw_name.strip().lower()
        if not isinstance(raw_value, dict):
            raise ProfileError(f"Profile '{name}' must be a mapping.")

        url = raw_value.get("url")
        token_env = raw_value.get("token_env")
        if not isinstance(url, str):
            raise ProfileError(f"Profile '{name}' is missing a string 'url'.")
        if not isinstance(token_env, str) or not token_env.strip():
            raise ProfileError(f"Profile '{name}' is missing a string 'token_env'.")

        ca_value: Any = raw_value.get("ca_file")
        ca_file = Path(ca_value).expanduser() if isinstance(ca_value, str) and ca_value else None
        try:
            timeout = float(raw_value.get("timeout", 30.0))
        except (TypeError, ValueError) as exc:
            raise ProfileError(f"Profile '{name}' has an invalid timeout.") from exc
        if timeout <= 0:
            raise ProfileError(f"Profile '{name}' timeout must be greater than zero.")

        profiles[name] = ZabbixProfile(
            name=name,
            url=_normalise_api_url(url),
            token_env=token_env.strip(),
            production=bool(raw_value.get("production", False)),
            verify_tls=bool(raw_value.get("verify_tls", True)),
            ca_file=ca_file,
            timeout=timeout,
        )
    return profiles


def get_profile(name: str, path: Path | None = None) -> ZabbixProfile:
    profiles = load_profiles(path)
    key = name.strip().lower()
    try:
        return profiles[key]
    except KeyError as exc:
        available = ", ".join(profiles)
        raise ProfileError(f"Unknown profile '{name}'. Available profiles: {available}") from exc
