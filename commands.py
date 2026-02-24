from __future__ import annotations

from typing import Any, Dict, List

from api_client import APIClient, APIClientError, AuthenticationError, RateLimitError
from auth import build_client, ensure_authenticated
from config_manager import save_config
from ui import (
    console,
    extract_has_more,
    extract_next_cursor,
    extract_ticket_list,
    print_main_menu,
    render_custom_fields_table,
    render_single_ticket,
    render_tickets_table,
)


def _build_custom_field_label_map(client: APIClient) -> Dict[str, str]:
    field_map: Dict[str, str] = {}
    for field in client.get_custom_fields():
        if not isinstance(field, dict):
            continue
        name = str(field.get("name") or "").strip()
        label = str(field.get("label") or "").strip()
        if name:
            field_map[name] = label or name
    return field_map


def _find_latest_ticket_snapshot(
    client: APIClient,
    ticket_ref: str,
    fallback_ticket: Dict[str, Any] | None,
    limit: int = 50,
) -> Dict[str, Any]:
    try:
        response = client.list_tickets(limit=limit)
        server_tickets = extract_ticket_list(response)
        for ticket in server_tickets:
            ref = str(ticket.get("ref") or "").strip()
            if ref == ticket_ref:
                return ticket
    except APIClientError:
        pass

    return fallback_ticket if isinstance(fallback_ticket, dict) else {"ref": ticket_ref}


def _enrich_ticket_for_display(ticket: Dict[str, Any], label_map: Dict[str, str]) -> Dict[str, Any]:
    enriched_ticket = dict(ticket)
    enriched_ticket["customFieldLabels"] = dict(label_map)
    return enriched_ticket


def _prepare_ticket_for_render(
    client: APIClient,
    ticket_ref: str,
    fallback_ticket: Dict[str, Any] | None,
    tickets_cache: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    limit = max(len(tickets_cache or []), 5)
    latest_ticket = _find_latest_ticket_snapshot(
        client=client,
        ticket_ref=ticket_ref,
        fallback_ticket=fallback_ticket,
        limit=limit,
    )
    label_map = _build_custom_field_label_map(client)
    return _enrich_ticket_for_display(latest_ticket, label_map)


def resolve_refs_from_input(user_input: str, tickets_cache: List[Dict[str, Any]]) -> List[str]:
    raw = user_input.strip()
    if not raw or raw.lower() == "none":
        return []

    refs: List[str] = []
    for part in raw.replace(",", " ").split():
        candidate = part.strip()
        if not candidate:
            continue

        if candidate.isdigit():
            index = int(candidate)
            if 1 <= index <= len(tickets_cache):
                ref_value = str(tickets_cache[index - 1].get("ref") or "").strip()
                if ref_value:
                    refs.append(ref_value)
                continue

        refs.append(candidate)

    return refs
def _show_operation_result(response: Any) -> None:
    console.print("[green]✔ Operation successful![/green]")
    if isinstance(response, dict):
        workitem = response.get("workitem")
        if isinstance(workitem, dict):
            render_single_ticket(workitem)
            return
        render_single_ticket(response)


def handle_create_ticket(config: Dict[str, Any], tickets_cache: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    client: APIClient = build_client(config)
    console.print("\n[bold]Create Ticket[/bold]")
    title = input("Title: ").strip()
    description = input("Description: ").strip()
    depends_on_input = input("Depends On (space-separated refs, or 'none'): ").strip()

    if not title:
        console.print("[yellow]Title is required.[/yellow]")
        return config

    custom_fields = [field for field in client.get_custom_fields() if isinstance(field, dict)]
    custom_field_values: Dict[str, Any] = {}
    if custom_fields:
        console.print("\n[bold]Custom Fields[/bold]")
        for field in custom_fields:
            field_name = str(field.get("name") or "").strip()
            field_label = str(field.get("label") or field_name or "Custom Field")
            if not field_name:
                continue
            value = input(f"{field_label} (optional): ").strip()
            if value:
                custom_field_values[field_name] = value

    dependency_refs = resolve_refs_from_input(depends_on_input, tickets_cache or [])

    payload = {
        "title": title,
        "description": description or "",
        "dependsOn": dependency_refs,
        "customFields": custom_field_values,
    }

    response = client.create_ticket(payload)
    console.print("[green]✔ Ticket created successfully![/green]")
    if isinstance(response, dict) and isinstance(response.get("workitem"), dict):
        render_single_ticket(response["workitem"])
    else:
        _show_operation_result(response)
    return config


def handle_update_ticket(
    client: APIClient,
    ticket_ref: str | None = None,
    current_ticket: Dict[str, Any] | None = None,
    tickets_cache: List[Dict[str, Any]] | None = None,
) -> None:
    console.print("\n[bold]Update Ticket[/bold]")
    allowed_stages = {"open", "in progress", "review", "closed"}

    if isinstance(current_ticket, dict):
        current_ticket_ref = str(current_ticket.get("ref") or ticket_ref or "").strip()
        if current_ticket_ref:
            current_ticket = _prepare_ticket_for_render(
                client=client,
                ticket_ref=current_ticket_ref,
                fallback_ticket=current_ticket,
                tickets_cache=tickets_cache,
            )
        render_single_ticket(current_ticket)

    if ticket_ref:
        console.print(f"[dim]Selected ticket:[/dim] {ticket_ref}")
    else:
        ticket_ref = input("Ticket ref to update (e.g., TF-205): ").strip()

    if not ticket_ref:
        console.print("[yellow]Ticket ref is required.[/yellow]")
        return

    current_title = str(current_ticket.get("title") or "") if isinstance(current_ticket, dict) else ""
    current_description = str(current_ticket.get("description") or "") if isinstance(current_ticket, dict) else ""
    current_stage = str(current_ticket.get("stage") or "") if isinstance(current_ticket, dict) else ""

    input_title = input(f"Title [{current_title}]: ").strip()
    input_description = input(f"Description [{current_description}]: ").strip()
    input_stage = input("Stage [open, in progress, review, closed] (blank to keep current): ").strip()
    if input_stage:
        normalized_stage = input_stage.lower()
        if normalized_stage not in allowed_stages:
            console.print("[yellow]Invalid stage. Allowed values: open, in progress, review, closed.[/yellow]")
            return
        input_stage = normalized_stage

    new_title = input_title if input_title else current_title
    new_description = input_description if input_description else current_description
    new_stage = input_stage if input_stage else current_stage

    depends_on_input = input("New Parent Ticket Ref (blank or 'none' to clear): ").strip()

    payload: Dict[str, Any] = {}
    payload["title"] = new_title
    payload["description"] = new_description
    payload["stage"] = new_stage

    payload["dependsOn"] = resolve_refs_from_input(depends_on_input, tickets_cache or [])
    dependency_changed = True

    current_depends_on: List[str] = []
    if isinstance(current_ticket, dict):
        existing_depends_on = current_ticket.get("dependsOn")
        if isinstance(existing_depends_on, list):
            current_depends_on = [str(item).strip() for item in existing_depends_on if str(item).strip()]
        elif isinstance(existing_depends_on, str) and existing_depends_on.strip():
            current_depends_on = [existing_depends_on.strip()]

    active_parent_list = payload.get("dependsOn", []) or current_depends_on
    if new_stage.strip().lower() == "closed" and active_parent_list:
        parent_ref_for_warning = active_parent_list[0]
        console.print(
            f"[yellow]Note: This ticket has a dependency on {parent_ref_for_warning}. "
            "Ensure the parent is also resolved.[/yellow]"
        )

    current_custom_fields = {}
    if isinstance(current_ticket, dict):
        existing_fields = current_ticket.get("customFields", {})
        if isinstance(existing_fields, dict):
            current_custom_fields = existing_fields

    custom_fields = [field for field in client.get_custom_fields() if isinstance(field, dict)]
    custom_field_values: Dict[str, Any] = {}
    if custom_fields:
        console.print("\n[bold]Custom Fields[/bold]")
        for field in custom_fields:
            field_name = str(field.get("name") or "").strip()
            field_label = str(field.get("label") or field_name or "Custom Field")
            if not field_name:
                continue

            current_value = current_custom_fields.get(field_name, "")
            if isinstance(current_value, (dict, list)):
                current_value_display = str(current_value)
            else:
                current_value_display = str(current_value)

            prompt = f"{field_label} (current: {current_value_display or '-'}, blank to skip): "
            value = input(prompt).strip()
            if value:
                custom_field_values[field_name] = value

    payload["customFields"] = custom_field_values

    if not (new_title or new_description or new_stage or custom_field_values or dependency_changed):
        console.print("[yellow]No updates provided. Nothing sent.[/yellow]")
        return

    response = client.update_ticket(ticket_ref=ticket_ref, payload=payload)
    console.print("[green]✔ Ticket updated successfully![/green]")
    if isinstance(response, dict) and isinstance(response.get("workitem"), dict):
        updated_ticket = _enrich_ticket_for_display(response["workitem"], _build_custom_field_label_map(client))
        render_single_ticket(updated_ticket)
    else:
        _show_operation_result(response)


def handle_logout(config: Dict[str, Any]) -> Dict[str, Any]:
    config["basic_auth_token"] = ""
    save_config(config)
    console.print("\n[green]Logged out successfully.[/green]")
    return ensure_authenticated(config)


def handle_manage_custom_fields(client: APIClient) -> None:
    while True:
        console.print("\n[bold]Manage Custom Fields[/bold]")
        fields = [field for field in client.get_custom_fields() if isinstance(field, dict)]
        if not fields:
            console.print("[yellow]No custom fields found.[/yellow]")
        else:
            render_custom_fields_table(fields)

        choice = input("Action [A, D, B] or enter Field # to edit: ").strip().lower()

        if choice == "a":
            name = input("Field name: ").strip()
            label = input("Field label: ").strip()
            if not name or not label:
                console.print("[yellow]Name and label are required.[/yellow]")
                continue
            try:
                response = client.create_custom_field(name=name, label=label)
                _show_operation_result(response)
            except APIClientError as error:
                error_text = str(error).lower()
                if "http 400" in error_text and "duplicate" in error_text:
                    console.print("[yellow]⚠ A field with this name already exists.[/yellow]")
                    continue
                raise

        elif choice.isdigit():
            index = int(choice)
            if not (1 <= index <= len(fields)):
                console.print("[yellow]Invalid field index for current view.[/yellow]")
                continue

            selected_field = fields[index - 1]
            field_id = str(selected_field.get("id") or "").strip()
            if not field_id:
                console.print("[yellow]Selected field has no ID and cannot be edited.[/yellow]")
                continue

            console.print(
                f"Editing field [cyan]{selected_field.get('name') or field_id}[/cyan] "
                f"(ID: {field_id})"
            )
            label = input("New label: ").strip()
            if not label:
                console.print("[yellow]New label is required.[/yellow]")
                continue
            response = client.update_custom_field(field_id=field_id, label=label)
            _show_operation_result(response)

        elif choice == "d":
            delete_target = input("Field # or ID to delete: ").strip()
            field_id = delete_target
            if delete_target.isdigit():
                index = int(delete_target)
                if 1 <= index <= len(fields):
                    field_id = str(fields[index - 1].get("id") or "").strip()
                else:
                    console.print("[yellow]Invalid field index for current view.[/yellow]")
                    continue

            if not field_id:
                console.print("[yellow]Field ID is required.[/yellow]")
                continue

            response = client.delete_custom_field(field_id=field_id)
            if response:
                _show_operation_result(response)
            else:
                console.print("[green]Field deleted successfully.[/green]")

        elif choice == "b":
            break

        else:
            console.print("[yellow]Invalid action. Use A, D, B, or a field number.[/yellow]")


def handle_manage_custom_fields_action(config: Dict[str, Any]) -> Dict[str, Any]:
    client: APIClient = build_client(config)
    handle_manage_custom_fields(client)
    return config


def handle_quit(config: Dict[str, Any]) -> Dict[str, Any]:
    console.print("\n[green]Goodbye![/green]")
    raise SystemExit(0)


def run_dashboard(config: Dict[str, Any]) -> None:
    fetch_limit = 5
    tickets_cache: List[Dict[str, Any]] = []
    current_next_cursor: str | None = None
    has_more = False
    should_fetch = True

    actions = {
        "c": lambda cfg: handle_create_ticket(cfg, tickets_cache),
        "f": handle_manage_custom_fields_action,
        "l": handle_logout,
        "q": handle_quit,
    }

    while True:
        try:
            client = build_client(config)

            if should_fetch:
                response = client.list_tickets(limit=fetch_limit, cursor=current_next_cursor)
                new_tickets = extract_ticket_list(response)
                has_more = extract_has_more(response)
                current_next_cursor = extract_next_cursor(response) if has_more else None

                if tickets_cache and new_tickets:
                    tickets_cache.extend(new_tickets)
                elif not tickets_cache:
                    tickets_cache = new_tickets

                should_fetch = False

            if not tickets_cache:
                console.print("\n[yellow]No tickets found.[/yellow]")
            else:
                render_tickets_table(tickets_cache, has_more=has_more)

            print_main_menu()
            if has_more:
                choice = input("\nAction [C, F, L, Q, M] or enter Ticket # to update: ").strip().lower()
                if choice == "m":
                    if current_next_cursor:
                        should_fetch = True
                    else:
                        console.print("[yellow]No cursor available for the next page.[/yellow]")
                    continue
            else:
                choice = input("\nAction [C, F, L, Q] or enter Ticket # to update: ").strip().lower()
                if choice == "n":
                    console.print("[yellow]No more pages available.[/yellow]")
                    continue

            if choice.isdigit():
                index = int(choice)
                if 1 <= index <= len(tickets_cache):
                    selected_ticket = tickets_cache[index - 1]
                    selected_ref = str(selected_ticket.get("ref") or "").strip()
                    if not selected_ref:
                        console.print("[yellow]Selected ticket has no ref and cannot be updated.[/yellow]")
                        continue

                    prepared_ticket = _prepare_ticket_for_render(
                        client=client,
                        ticket_ref=selected_ref,
                        fallback_ticket=selected_ticket,
                        tickets_cache=tickets_cache,
                    )
                    render_single_ticket(prepared_ticket)
                    decision = input("Do you want to [E]dit this ticket or [B]ack to list? (E/B): ").strip().lower()
                    if decision == "b":
                        continue
                    if decision != "e":
                        console.print("[yellow]Invalid choice. Returning to dashboard.[/yellow]")
                        continue

                    handle_update_ticket(
                        client,
                        ticket_ref=selected_ref,
                        current_ticket=prepared_ticket,
                        tickets_cache=tickets_cache,
                    )
                    tickets_cache = []
                    current_next_cursor = None
                    has_more = False
                    should_fetch = True
                    continue

                console.print("[yellow]Invalid ticket index for current view.[/yellow]")
                continue

            action = actions.get(choice)

            if action is None:
                console.print("\n[yellow]Invalid action. Use C, F, L, Q, N or a ticket number.[/yellow]")
                continue

            config = action(config)
            tickets_cache = []
            current_next_cursor = None
            has_more = False
            should_fetch = True

        except RateLimitError as error:
            retry_after = (
                f" Retry after ~{error.retry_after_seconds}s."
                if error.retry_after_seconds is not None
                else ""
            )
            console.print(f"[red]Rate limited:[/red] {error}.{retry_after}")
        except AuthenticationError:
            console.print("[red]Authentication failed. Please log in again.[/red]")
            config = ensure_authenticated(config)
        except APIClientError as error:
            console.print(f"[red]API error:[/red] {error}")
            error_text = str(error).lower()
            if "http 400" in error_text and ("depend" in error_text or "parent" in error_text):
                console.print("[yellow]Hint: Make sure the Parent Ticket IDs exist and are assigned to you.[/yellow]")
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted by user.[/yellow]")
            break
        except SystemExit:
            raise
        except Exception as error:
            console.print(f"[red]Unexpected error:[/red] {error}")
