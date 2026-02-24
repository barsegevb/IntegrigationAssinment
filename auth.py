from __future__ import annotations

import base64
from getpass import getpass
from typing import Any, Dict, Tuple

from api_client import APIClient, APIClientError, AuthenticationError
from config_manager import load_config, save_config
from ui import console, print_auth_menu


def build_client(config: Dict[str, Any], override_token: str | None = None, auth_type: str | None = None) -> APIClient:
    endpoints = config.get("endpoints", {})
    return APIClient(
        base_url=config.get("base_url", "https://integrations-assignment-ticketforge.vercel.app/api/tforge").strip(),
        auth_type=auth_type or config.get("auth_type", "basic"),
        basic_auth_token=override_token if override_token is not None else (config.get("basic_auth_token") or None),
        token=config.get("bearer_token") or None,
        api_key=config.get("api_key") or None,
        api_key_header=config.get("api_key_header") or "X-API-Key",
        list_tickets_endpoint=endpoints.get("list_tickets", "/workitems/mine"),
        create_ticket_endpoint=endpoints.get("create_ticket", "/workitem/publish"),
        update_ticket_endpoint=endpoints.get("update_ticket", "/workitem/{ref}"),
        custom_fields_endpoint=endpoints.get("custom_fields", "/custom-fields"),
        signup_endpoint=endpoints.get("signup", "/user/register"),
    )


def create_basic_auth_token(username: str, password: str) -> str:
    raw = f"{username}:{password}".encode("utf-8")
    return base64.b64encode(raw).decode("utf-8")


def login(config: Dict[str, Any], username: str | None = None, password: str | None = None) -> Tuple[Dict[str, Any], bool]:
    console.print("\n[bold]Login[/bold]")

    entered_username = username or input("Username: ").strip()
    entered_password = password or getpass("Password: ")

    if not entered_username or not entered_password:
        console.print("[yellow]Username and password are required.[/yellow]")
        return config, False

    token = create_basic_auth_token(entered_username, entered_password)
    client = build_client(config, override_token=token, auth_type="basic")

    try:
        client.list_tickets(limit=1)
    except AuthenticationError:
        console.print("[red]Invalid username or password[/red]")
        return config, False
    except APIClientError as error:
        console.print(f"[red]Login verification failed:[/red] {error}")
        return config, False

    config["auth_type"] = "basic"
    config["basic_auth_token"] = token
    save_config(config)
    console.print("[green]Login Successful[/green]")
    return config, True


def signup(config: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    console.print("\n[bold]Signup[/bold]")
    username = input("Choose username: ").strip()
    password = getpass("Choose password (min 6 chars): ")

    if len(password) < 6:
        console.print("[yellow]Password must be at least 6 characters.[/yellow]")
        return config, False

    if not username:
        console.print("[yellow]Username is required.[/yellow]")
        return config, False

    unauth_client = build_client(config, auth_type="none")

    try:
        unauth_client.signup(username=username, password=password)
        console.print("[green]Signup successful. Logging you in...[/green]")
    except APIClientError as error:
        console.print(f"[red]Signup failed:[/red] {error}")
        return config, False

    return login(config, username=username, password=password)


def has_valid_config(config: Dict[str, Any]) -> bool:
    token = str(config.get("basic_auth_token", "") or "").strip()
    return bool(token and token != "TODO_BASE64_BASIC_AUTH_TOKEN")


def ensure_authenticated(config: Dict[str, Any]) -> Dict[str, Any]:
    if has_valid_config(config):
        try:
            client = build_client(config)
            client.list_tickets(limit=1)
            return config
        except AuthenticationError:
            console.print("[yellow]Stored credentials are invalid. Please log in again.[/yellow]")
        except APIClientError as error:
            console.print(f"[yellow]Could not verify saved credentials:[/yellow] {error}")

    def handle_auth_quit(current_config: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
        raise SystemExit(0)

    auth_actions = {
        "1": login,
        "2": signup,
        "3": handle_auth_quit,
    }

    while True:
        print_auth_menu()
        choice = input("Choose option (1-3): ").strip()
        action = auth_actions.get(choice)

        if action is None:
            console.print("[yellow]Invalid option. Choose 1, 2, or 3.[/yellow]")
            continue

        config, ok = action(config)
        if ok:
            return config


def run_auth_flow() -> Dict[str, Any]:
    config = load_config()
    return ensure_authenticated(config)
