from __future__ import annotations

import json
from typing import Any, Dict, List

from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.table import Table

console = Console()


def print_header() -> None:
    console.print("\n[bold cyan]TicketForge CLI[/bold cyan]")
    console.print("[dim]Manage tickets from your terminal[/dim]")


def print_auth_menu() -> None:
    console.print("\n[bold]Authentication Required[/bold]")
    console.print("1) Login")
    console.print("2) Signup")
    console.print("3) Quit")


def print_main_menu() -> None:
    console.print("\n[bold]Main Menu[/bold]")
    console.print("[C] Create Ticket")
    console.print("[F] Manage Custom Fields")
    console.print("[L] Logout")
    console.print("[Q] Quit")


def pretty_print_json(data: Any, title: str = "Response") -> None:
    try:
        encoded = json.dumps(data, ensure_ascii=False)
        console.print(Panel(JSON(encoded), title=title, border_style="blue"))
    except (TypeError, ValueError):
        console.print(f"[yellow]Warning:[/yellow] Non-serializable data: {data}")


def extract_ticket_list(payload: Any) -> List[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    workitems = payload.get("workitems", [])
    if isinstance(workitems, list):
        return workitems
    return []


def extract_has_more(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    pagination = payload.get("pagination", {})
    if not isinstance(pagination, dict):
        return False
    return bool(pagination.get("hasMore", False))


def extract_next_cursor(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    pagination = payload.get("pagination", {})
    if not isinstance(pagination, dict):
        return None
    cursor = pagination.get("nextCursor")
    if isinstance(cursor, str) and cursor.strip():
        return cursor
    return None


def render_tickets_table(tickets: List[Dict[str, Any]], has_more: bool = False) -> None:
    table = Table(title="Tickets", show_lines=False)
    table.add_column("#", style="yellow", no_wrap=True)
    table.add_column("Ref", style="cyan", no_wrap=True)
    table.add_column("Title", style="white")
    table.add_column("Stage", style="magenta")
    table.add_column("Description", style="green")

    for index, ticket in enumerate(tickets, start=1):
        ticket_id = str(ticket.get("ref") or "N/A")
        title = str(ticket.get("title") or "(untitled)")
        status = str(ticket.get("stage") or "unknown")
        description = str(ticket.get("description") or "")
        table.add_row(str(index), ticket_id, title, status, description)

    console.print(table)
    if has_more:
        console.print("[dim]Press 'M' to load more tickets...[/dim]")


def render_single_ticket(ticket: Dict[str, Any]) -> None:
    rows = Table(show_header=False, box=None, pad_edge=False)
    rows.add_column("Field", style="cyan", no_wrap=True)
    rows.add_column("Value", style="white")

    def _has_visible_value(value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        return True

    rows.add_row("Ref", str(ticket.get("ref") or "N/A"))
    rows.add_row("Title", str(ticket.get("title") or ""))
    rows.add_row("Stage", str(ticket.get("stage") or ""))

    description = ticket.get("description")
    if _has_visible_value(description):
        rows.add_row("Description", str(description))

    depends_on_values = ticket.get("dependsOn", [])
    visible_depends_on: List[str] = []
    if isinstance(depends_on_values, list):
        for item in depends_on_values:
            if isinstance(item, dict):
                key_value = (
                    item.get("ref")
                    or item.get("id")
                    or item.get("key")
                    or item.get("ticketRef")
                )
                if key_value is not None and str(key_value).strip():
                    visible_depends_on.append(str(key_value).strip())
            else:
                item_value = str(item).strip()
                if item_value:
                    visible_depends_on.append(item_value)
    elif isinstance(depends_on_values, dict):
        visible_depends_on = [str(key).strip() for key in depends_on_values.keys() if str(key).strip()]
    rows.add_row("Depends On", ", ".join(visible_depends_on) if visible_depends_on else "-")

    custom_fields_dict: Dict[str, Any] = {}
    raw_custom_fields = ticket.get("customFields")
    raw_custom_field_labels = ticket.get("customFieldLabels")

    if isinstance(raw_custom_fields, dict) and raw_custom_fields:
        custom_fields_dict = raw_custom_fields
    elif isinstance(raw_custom_field_labels, dict) and raw_custom_field_labels:
        custom_fields_dict = raw_custom_field_labels

    for key, value in custom_fields_dict.items():
        if not _has_visible_value(value):
            continue
        rows.add_row(f"[cyan]{key}:[/cyan]", str(value))

    for key, value in ticket.items():
        if key in {"ref", "dependsOn", "title", "stage", "description", "customFields", "customFieldLabels"}:
            continue
        if isinstance(value, (dict, list)):
            formatted = json.dumps(value, ensure_ascii=False)
        else:
            formatted = str(value)
        rows.add_row(str(key), formatted)

    console.print(Panel(rows, title="Selected Ticket", border_style="blue"))


def render_custom_fields_table(fields: List[Dict[str, Any]]) -> None:
    table = Table(title="Custom Fields", show_lines=False)
    table.add_column("#", style="yellow", no_wrap=True)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="white")
    table.add_column("Label", style="magenta")

    for index, field in enumerate(fields, start=1):
        field_id = str(field.get("id") or "N/A")
        name = str(field.get("name") or "")
        label = str(field.get("label") or "")
        table.add_row(str(index), field_id, name, label)

    console.print(table)
