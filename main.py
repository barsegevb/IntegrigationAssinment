from __future__ import annotations

from auth import run_auth_flow
from commands import run_dashboard
from ui import console, print_header


def main() -> None:
    print_header()
    config = run_auth_flow()
    run_dashboard(config)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user.[/yellow]")
