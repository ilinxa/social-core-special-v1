# apps/explore/tests/test_city_data.py
"""Tests for city data utility (apps.core.utils.city_data)."""

import pytest

from apps.core.utils.city_data import (
    get_all_countries,
    get_cities_for_country,
    is_valid_city,
    load_city_data,
)


class TestLoadCityData:
    """Tests for load_city_data()."""

    def test_loads_data_dict(self):
        data = load_city_data()
        assert isinstance(data, dict)
        assert len(data) > 0

    def test_keys_are_country_codes(self):
        data = load_city_data()
        for code in data:
            assert len(code) == 2
            assert code == code.upper()

    def test_values_are_city_lists(self):
        data = load_city_data()
        for cities in data.values():
            assert isinstance(cities, list)
            assert len(cities) > 0
            for city in cities:
                assert isinstance(city, str)

    def test_contains_major_countries(self):
        data = load_city_data()
        for code in ["US", "GB", "DE", "FR", "JP", "CN", "IN", "BR"]:
            assert code in data, f"Missing country: {code}"


class TestGetCitiesForCountry:
    """Tests for get_cities_for_country()."""

    def test_valid_country(self):
        cities = get_cities_for_country("US")
        assert isinstance(cities, list)
        assert len(cities) > 0
        assert "New York" in cities

    def test_unknown_country(self):
        cities = get_cities_for_country("XX")
        assert cities == []

    def test_empty_country(self):
        cities = get_cities_for_country("")
        assert cities == []

    def test_case_insensitive(self):
        cities = get_cities_for_country("us")
        assert len(cities) > 0
        assert cities == get_cities_for_country("US")


class TestGetAllCountries:
    """Tests for get_all_countries()."""

    def test_returns_sorted_list(self):
        countries = get_all_countries()
        assert isinstance(countries, list)
        assert countries == sorted(countries)

    def test_contains_expected_countries(self):
        countries = get_all_countries()
        assert "US" in countries
        assert "GB" in countries


class TestIsValidCity:
    """Tests for is_valid_city()."""

    def test_valid_city(self):
        assert is_valid_city("US", "New York") is True

    def test_invalid_city(self):
        assert is_valid_city("US", "FakeCity12345") is False

    def test_empty_country(self):
        assert is_valid_city("", "New York") is False

    def test_empty_city(self):
        assert is_valid_city("US", "") is False

    def test_unknown_country(self):
        assert is_valid_city("XX", "SomeCity") is False
