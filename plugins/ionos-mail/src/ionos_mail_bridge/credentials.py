"""Mailbox credentials in the operating system keyring."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import keyring


SERVICE = "ionos-mail-bridge"
REGIONS = {"com": "ionos.com", "de": "ionos.de"}


def _account_file() -> Path:
    base = os.getenv("XDG_CONFIG_HOME")
    if base:
        return Path(base) / SERVICE / "account.json"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / SERVICE / "account.json"
    return Path.home() / ".config" / SERVICE / "account.json"


def _saved_account() -> dict:
    path = _account_file()
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"Could not read account configuration at {path}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Invalid account configuration at {path}")
    return payload


def saved_address() -> str:
    value = _saved_account().get("address", "")
    return value if isinstance(value, str) else ""


def saved_region() -> str:
    region = _saved_account().get("region", "com")
    if region not in REGIONS:
        raise RuntimeError(f"Invalid saved IONOS region: {region!r}")
    return region


def _write_account(payload: dict) -> None:
    path = _account_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    try:
        with temp.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle)
            handle.write("\n")
        os.chmod(temp, 0o600)
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def set_region(region: str) -> None:
    if region not in REGIONS:
        raise ValueError("Region must be 'com' or 'de'")
    payload = _saved_account()
    payload["region"] = region
    _write_account(payload)


def password_for(address: str) -> str:
    password = os.getenv("IONOS_MAIL_PASSWORD", "")
    if password:
        return password
    try:
        return keyring.get_password(SERVICE, address) or ""
    except Exception as exc:
        raise RuntimeError("Could not read mailbox password from the OS keyring") from exc


def save_account(address: str, password: str) -> None:
    if not password or "\n" in password or "\r" in password:
        raise ValueError("Password must be a nonempty single line")
    try:
        keyring.set_password(SERVICE, address, password)
    except Exception as exc:
        raise RuntimeError("Could not store mailbox password in the OS keyring") from exc
    payload = _saved_account()
    payload["address"] = address
    _write_account(payload)
