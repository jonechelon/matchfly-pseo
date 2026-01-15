"""MatchFly Scrapers Module.

Keep imports lightweight so that importing the package doesn't immediately pull
optional runtime dependencies. Consumers can import the concrete scraper from
`src.scrapers.gru_flights_scraper`.
"""

from __future__ import annotations

from typing import Any

__all__ = ["GRUFlightScraper", "main"]


def __getattr__(name: str) -> Any:
    if name in ("GRUFlightScraper", "main"):
        from .gru_flights_scraper import GRUFlightScraper, main

        return {"GRUFlightScraper": GRUFlightScraper, "main": main}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

