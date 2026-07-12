from pathlib import Path

import pytest

from ztt.profiles import ProfileError, get_profile, load_profiles


def _config(path: Path) -> Path:
    path.write_text(
        """profiles:
  qual:
    url: https://zabbix-qual.example/zabbix
    token_env: ZTT_ZABBIX_QUAL_TOKEN
    verify_tls: true
  prod:
    url: https://zabbix-prod.example/api_jsonrpc.php
    token_env: ZTT_ZABBIX_PROD_TOKEN
    production: true
    timeout: 15
""",
        encoding="utf-8",
    )
    return path


def test_loads_qual_and_prod_profiles(tmp_path: Path) -> None:
    profiles = load_profiles(_config(tmp_path / "config.yaml"))

    assert profiles["qual"].url == "https://zabbix-qual.example/zabbix/api_jsonrpc.php"
    assert not profiles["qual"].production
    assert profiles["prod"].url == "https://zabbix-prod.example/api_jsonrpc.php"
    assert profiles["prod"].production
    assert profiles["prod"].timeout == 15


def test_token_is_read_only_from_environment(tmp_path: Path) -> None:
    profile = get_profile("QUAL", _config(tmp_path / "config.yaml"))

    assert profile.token({"ZTT_ZABBIX_QUAL_TOKEN": "secret"}) == "secret"
    with pytest.raises(ProfileError, match="ZTT_ZABBIX_QUAL_TOKEN"):
        profile.token({})


def test_unknown_profile_lists_available_names(tmp_path: Path) -> None:
    with pytest.raises(ProfileError, match="qual, prod"):
        get_profile("integration", _config(tmp_path / "config.yaml"))
