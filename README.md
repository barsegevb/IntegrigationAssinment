# TicketForge CLI Integration

Command-line app for interacting with TicketForge via reverse-engineered REST APIs.

## Features
- Setup/config flow to store API connection details locally.
- List tickets with pagination navigation (`N`/`P`/`Q`).
- Create ticket via prompted input fields.
- Update ticket by ID.
- Robust API error handling (timeouts, network errors, `4xx/5xx`, and `429` rate limits).
- Clean terminal UI using `rich` tables and formatted JSON output.

## Project Structure
- `main.py`: Primary CLI script.
- `api_client.py`: REST client and error handling logic.
- `requirements.txt`: Dependencies.
- `tests/test_main_helpers.py`: Unit tests for core helper logic.

## Installation
1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Run
```bash
python main.py
```

## Example Usage Flow
1. Select **Setup / Config** and enter:
	- Base URL discovered in browser network tab
	- Auth type (`none`, `bearer`, or `api_key`)
	- Token/key details if applicable
2. Select **List Tickets** to browse pages.
3. Select **Create Ticket** and provide ticket fields.
4. Select **Update Ticket** and send partial updates.

## Testing
```bash
pytest -q
```

## Assumptions
- TicketForge API docs are unavailable; endpoint paths and payload schemas must be discovered from network traffic.
- `main.py` and `api_client.py` intentionally include TODO markers where exact endpoint paths and schema-specific fields must be injected.
- Listing expects a paginated API; parser supports common response shapes (`tickets`, `items`, `data`, `results`) as temporary compatibility logic.

## AI Disclosure
This scaffold was generated with AI assistance (GitHub Copilot, Gemini) and then tailored for the assignment constraints. All endpoint paths, auth headers, and business-specific payload fields must be validated and completed manually against observed TicketForge network traffic.