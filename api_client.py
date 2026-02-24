"""HTTP client layer for the TicketForge CLI integration assignment.

This module is intentionally isolated from CLI concerns.
It uses `requests` with robust error handling for:
- network timeouts
- connection/request issues
- 4xx/5xx HTTP responses
- 429 API rate limits
- JSON decoding errors
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests
from requests import Response


class APIClientError(Exception):
    """Base exception for all API client failures."""


class AuthenticationError(APIClientError):
    """Raised when authentication fails (HTTP 401/403)."""


class RateLimitError(APIClientError):
    """Raised when the API returns HTTP 429."""

    def __init__(self, message: str, retry_after_seconds: Optional[int] = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


@dataclass
class APIConfig:
    """Configuration container for API client setup."""

    base_url: str
    auth_type: Optional[str] = None
    basic_auth_token: Optional[str] = None
    token: Optional[str] = None
    api_key: Optional[str] = None
    api_key_header: str = "X-API-Key"
    timeout_seconds: float = 10.0
    list_tickets_endpoint: str = "/workitems/mine"
    create_ticket_endpoint: str = "/workitem/publish"
    update_ticket_endpoint: str = "/workitem/{ref}"
    custom_fields_endpoint: str = "/custom-fields"
    signup_endpoint: str = "/user/register"


class APIClient:
    def __init__(
        self,
        base_url: str,
        auth_type: Optional[str] = None,
        basic_auth_token: Optional[str] = None,
        token: Optional[str] = None,
        api_key: Optional[str] = None,
        api_key_header: str = "X-API-Key",
        timeout_seconds: float = 10.0,
        list_tickets_endpoint: str = "/workitems/mine",
        create_ticket_endpoint: str = "/workitem/publish",
        update_ticket_endpoint: str = "/workitem/{ref}",
        custom_fields_endpoint: str = "/custom-fields",
        signup_endpoint: str = "/user/register",
    ) -> None:
        self.config = APIConfig(
            base_url=base_url.rstrip("/"),
            auth_type=(auth_type or "none").lower(),
            basic_auth_token=basic_auth_token,
            token=token,
            api_key=api_key,
            api_key_header=api_key_header,
            timeout_seconds=timeout_seconds,
            list_tickets_endpoint=list_tickets_endpoint,
            create_ticket_endpoint=create_ticket_endpoint,
            update_ticket_endpoint=update_ticket_endpoint,
            custom_fields_endpoint=custom_fields_endpoint,
            signup_endpoint=signup_endpoint,
        )
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json", "Content-Type": "application/json"})
        self._configure_auth()

    def _configure_auth(self) -> None:
        """Configure authentication headers based on selected auth mode."""
        auth_type = self.config.auth_type

        if auth_type in (None, "none"):
            return

        if auth_type == "basic":
            if not self.config.basic_auth_token:
                raise APIClientError("Authentication type 'basic' selected but no basic auth token was provided.")
            self.session.headers["Authorization"] = f"Basic {self.config.basic_auth_token}"
            return

        if auth_type == "bearer":
            if not self.config.token:
                raise APIClientError("Authentication type 'bearer' selected but no token was provided.")
            self.session.headers["Authorization"] = f"Bearer {self.config.token}"
            return

        if auth_type == "api_key":
            if not self.config.api_key:
                raise APIClientError("Authentication type 'api_key' selected but no API key was provided.")
            self.session.headers[self.config.api_key_header] = self.config.api_key
            return

        raise APIClientError(
            f"Unsupported auth_type '{auth_type}'. Use one of: none, basic, bearer, api_key."
        )

    def _request(self, method: str, endpoint: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.config.base_url}{endpoint}"

        try:
            response: Response = self.session.request(
                method=method,
                url=url,
                json=payload,
                timeout=self.config.timeout_seconds,
            )
            response.raise_for_status()
        except requests.exceptions.Timeout as error:
            raise APIClientError(
                f"Request timed out after {self.config.timeout_seconds}s: {method.upper()} {endpoint}"
            ) from error
        except requests.exceptions.HTTPError as error:
            status_code = error.response.status_code if error.response is not None else "unknown"
            response_body = ""
            retry_after: Optional[int] = None
            api_message: Optional[str] = None

            if error.response is not None and error.response.text:
                response_body = error.response.text.strip()[:300]

            if error.response is not None:
                try:
                    response_json = error.response.json()
                    if isinstance(response_json, dict):
                        message_value = response_json.get("message")
                        if isinstance(message_value, str) and message_value.strip():
                            api_message = message_value.strip()
                except ValueError:
                    api_message = None

            if error.response is not None:
                retry_after_raw = error.response.headers.get("Retry-After")
                if retry_after_raw and retry_after_raw.isdigit():
                    retry_after = int(retry_after_raw)

            if status_code == 429:
                message = f"HTTP 429 rate limit hit for {method.upper()} {endpoint}"
                if retry_after is not None:
                    message += f" | Retry after: {retry_after}s"
                if api_message:
                    message += f" | Message: {api_message}"
                raise RateLimitError(message, retry_after_seconds=retry_after) from error

            if status_code in (401, 403):
                raise AuthenticationError(api_message or "Invalid credentials") from error

            message = f"HTTP {status_code} for {method.upper()} {endpoint}"
            if api_message:
                message += f" | Message: {api_message}"
            if response_body:
                message += f" | Response: {response_body}"
            raise APIClientError(message) from error
        except requests.exceptions.RequestException as error:
            raise APIClientError(f"Network/request error for {method.upper()} {endpoint}: {error}") from error

        if response.status_code == 204:
            return {}

        if not response.text or not response.text.strip():
            return {}

        try:
            return response.json()
        except ValueError as error:
            raise APIClientError(
                f"Failed to decode JSON response for {method.upper()} {endpoint}."
            ) from error

    def list_tickets(self, limit: int = 5, cursor: str | None = None) -> Any:
        """Fetch tickets using configured endpoint with optional cursor pagination."""
        endpoint = f"{self.config.list_tickets_endpoint}?limit={limit}"
        if cursor:
            endpoint += f"&cursor={cursor}"
        return self._request(method="GET", endpoint=endpoint)

    def create_ticket(self, payload: Dict[str, Any]) -> Any:
        """Create a new ticket.

        TODO: Validate and map payload fields according to TicketForge requirements.
        """
        return self._request(method="POST", endpoint=self.config.create_ticket_endpoint, payload=payload)

    def update_ticket(self, ticket_ref: str, payload: Dict[str, Any]) -> Any:
        """Update an existing ticket via PUT /workitem/{ref}."""
        endpoint = self.config.update_ticket_endpoint.format(ref=ticket_ref)
        return self._request(method="PUT", endpoint=endpoint, payload=payload)

    def get_custom_fields(self) -> Any:
        """Fetch custom fields and return the customFields list."""
        response = self._request(method="GET", endpoint=self.config.custom_fields_endpoint)
        if not isinstance(response, dict):
            return []
        custom_fields = response.get("customFields", [])
        if isinstance(custom_fields, list):
            return custom_fields
        return []

    def signup(self, username: str, password: str) -> Any:
        """Register a new user via POST /user/register."""
        payload = {"username": username, "password": password}
        return self._request(method="POST", endpoint=self.config.signup_endpoint, payload=payload)

    def create_custom_field(self, name: str, label: str) -> Any:
        """Create a custom field via POST /custom-fields."""
        payload = {"name": name, "label": label}
        return self._request(method="POST", endpoint=self.config.custom_fields_endpoint, payload=payload)

    def update_custom_field(self, field_id: str, label: str) -> Any:
        """Update a custom field via PUT /custom-fields/{id}."""
        payload = {"label": label}
        endpoint = f"{self.config.custom_fields_endpoint}/{field_id}"
        return self._request(method="PUT", endpoint=endpoint, payload=payload)

    def delete_custom_field(self, field_id: str) -> Any:
        """Delete a custom field via DELETE /custom-fields/{id}."""
        endpoint = f"{self.config.custom_fields_endpoint}/{field_id}"
        return self._request(method="DELETE", endpoint=endpoint)
