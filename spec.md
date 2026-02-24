# TicketForge CLI Integration

## 1. Project Goal
Develop a command-line interface (CLI) application in Python that integrates with the "TicketForge" project management tool. The application must allow users to manage tickets directly from the terminal. 

## 2. API Details (Reverse-Engineered)
**Note to AI:** The API documentation is not public. The following endpoints and structures were reverse-engineered by inspecting network traffic.

* **Base URL:** `https://integrations-assignment-ticketforge.vercel.app/api/tforge`
* **Authentication:** HTTP Basic Auth. 
  * Header example: `Authorization: Basic QmFyc2VnZXZAaWNsYXVkLmNvbTpCYXJzZWdldjE=`
* **Rate Limiting:** The API returns an `X-Ratelimit-Limit` header (currently set to 50). The client must handle HTTP 429 Too Many Requests gracefully.

### Endpoints:
* **GET `/workitems/mine`**
  * **Purpose:** Fetches a list of the user's tickets.
  * **Query Parameters:** `limit` (integer, used for pagination), e.g., `?limit=5`.
  * **Response Format:** ```json
    {
      "workitems": [],
      "pagination": {
        "limit": 5,
        "hasMore": false
      }
    }
    ```

* **POST `/workitem/publish`**
  * **Purpose:** Creates a new ticket.
  * **Expected Payload (Inferred):**
    ```json
    {
      "title": "string",
      "description": "string"
    }
    ```

* **PUT/PATCH `/[TODO: update endpoint]`**
  * **Purpose:** Updates an existing ticket.
  * **Note:** Developer will implement this later.

## 3. Core CLI Requirements
The CLI must implement an interactive menu using a `while True` loop with the following capabilities:
1.  **Setup/Config:** Prompt the user for their Base64 Basic Auth token and save it securely in memory or a local config file.
2.  **List Tickets:** Fetch and display existing tickets in a formatted table in the terminal. Use the `pagination` object from the response to allow the user to see "next pages".
3.  **Create Ticket:** Prompt the user for `title` and `description` and send a POST request.

## 4. Enhanced Features (Bonus)
* **Pagination:** Implement fetching more tickets if `hasMore` is true.
* **Rate Limits:** Implement a retry mechanism or user warning if a 429 status code is encountered, utilizing the `X-Ratelimit-Limit` header info.
* **UI:** Use clear terminal formatting (e.g., using `rich` or standard formatted text) to make it look professional.

## 5. Instructions for AI
Generate the Python boilerplate based on this spec. Separate the logic into a `main.py` (CLI interface) and an `api_client.py` (Request handling).