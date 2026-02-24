from config_manager import normalize_auth_type
from ui import extract_has_more, extract_ticket_list


def test_normalize_auth_type_known_values() -> None:
    assert normalize_auth_type("none") == "none"
    assert normalize_auth_type("basic") == "basic"
    assert normalize_auth_type("Bearer") == "bearer"
    assert normalize_auth_type("API_KEY") == "api_key"


def test_normalize_auth_type_unknown_falls_back_to_none() -> None:
    assert normalize_auth_type("cookie") == "none"


def test_extract_ticket_list_from_list_payload() -> None:
    payload = {"workitems": [{"id": "1", "title": "A"}, {"id": "2", "title": "B"}]}
    tickets = extract_ticket_list(payload)
    assert len(tickets) == 2
    assert tickets[0]["id"] == "1"


def test_extract_ticket_list_from_object_payload() -> None:
    payload = {"workitems": [{"id": "x", "title": "Issue"}]}
    tickets = extract_ticket_list(payload)
    assert len(tickets) == 1
    assert tickets[0]["id"] == "x"


def test_extract_ticket_list_unknown_shape_returns_empty_list() -> None:
    payload = {"unexpected": {"nested": True}}
    tickets = extract_ticket_list(payload)
    assert tickets == []


def test_extract_has_more_true() -> None:
    payload = {"pagination": {"limit": 5, "hasMore": True}}
    assert extract_has_more(payload) is True


def test_extract_has_more_false_by_default() -> None:
    payload = {"workitems": []}
    assert extract_has_more(payload) is False
