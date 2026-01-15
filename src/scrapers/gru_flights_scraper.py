"""
Compat module for importing the GRU scraper.

The project historically used the executable script `gru-scraper.py` (with a hyphen),
which cannot be imported as a normal Python module. Tests and runners import
`src.scrapers.gru_flights_scraper`, so this file bridges that gap by loading the
script and re-exporting its public API.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, cast


def _load_legacy_script_module() -> ModuleType:
    legacy_path = Path(__file__).with_name("gru-scraper.py")
    spec = importlib.util.spec_from_file_location("src.scrapers._gru_scraper_legacy", legacy_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load legacy scraper script at {legacy_path}")

    module = importlib.util.module_from_spec(spec)
    # Necessário para dataclasses/typing (Python 3.14+): o módulo deve existir em sys.modules
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[call-arg]
    return module


_legacy = _load_legacy_script_module()

# Re-export expected symbols
GRUFlightScraper = cast(Any, getattr(_legacy, "GRUFlightScraper"))
main = cast(Any, getattr(_legacy, "main"))

__all__ = ["GRUFlightScraper", "main"]

