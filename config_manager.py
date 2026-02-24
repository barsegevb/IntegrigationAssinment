from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

CONFIG_FILE = Path("ticketforge_config.json")
DEFAULT_PAGE_SIZE = 5


def default_config() -> Dict[str, Any]:
    return {
        "base_url": "https://integrations-assignment-ticketforge.vercel.app/api/tforge",
        "auth_type": "basic",  # Supported: none, basic, bearer, api_key
        "basic_auth_token": "TODO_BASE64_BASIC_AUTH_TOKEN",
        "bearer_token": "",
        "api_key": "",
        "api_key_header": "X-API-Key",
        "page_size": DEFAULT_PAGE_SIZE,
        "update_method": "PUT",
        "endpoints": {
            "list_tickets": "/workitems/mine",
            "create_ticket": "/workitem/publish",
            "update_ticket": "/workitem/{ref}",
            "custom_fields": "/custom-fields",
        },
    }


def normalize_auth_type(raw_value: str) -> str:
    value = raw_value.strip().lower()
    if value in {"none", "basic", "bearer", "api_key"}:
        return value
    return "none"


def load_config() -> Dict[str, Any]:
    if not CONFIG_FILE.exists():
        config = default_config()
        save_config(config)
        return config

    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as file:
            loaded = json.load(file)
    except (OSError, ValueError):
        return default_config()

    config = default_config()
    config.update(loaded)

    if isinstance(loaded.get("endpoints"), dict):
        config["endpoints"].update(loaded["endpoints"])

    return config


def save_config(config: Dict[str, Any]) -> None:
    with CONFIG_FILE.open("w", encoding="utf-8") as file:
        json.dump(config, file, indent=2, ensure_ascii=False)
