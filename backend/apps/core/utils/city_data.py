"""
City Data Utility
=================
Loads and queries static city data from JSON file.

The city data is a curated list of ~5000 major cities keyed by
ISO 3166-1 alpha-2 country code. Used for:
  - Backend validation of city fields on UserProfile and BusinessAccount
  - Frontend cascading Country → City dropdowns (via API endpoint)

Usage:
    from apps.core.utils.city_data import get_cities_for_country, is_valid_city

    cities = get_cities_for_country("US")  # ["New York", "Los Angeles", ...]
    valid = is_valid_city("US", "New York")  # True
"""

import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def load_city_data() -> dict[str, list[str]]:
    """Load city data from static JSON file. Cached in memory after first call."""
    data_path = Path(__file__).resolve().parent.parent / "data" / "cities.json"
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_cities_for_country(country_code: str) -> list[str]:
    """Get city list for a given ISO 3166-1 alpha-2 country code."""
    if not country_code:
        return []
    return load_city_data().get(country_code.upper(), [])


def get_all_countries() -> list[str]:
    """Get sorted list of all available country codes."""
    return sorted(load_city_data().keys())


def is_valid_city(country_code: str, city: str) -> bool:
    """
    Validate that a city exists in the given country's city list.

    Returns False if country_code or city is empty.
    """
    if not country_code or not city:
        return False
    cities = get_cities_for_country(country_code)
    return city in cities
