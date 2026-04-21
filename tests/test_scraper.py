"""Unit tests for pure functions in scraper.py."""
from datetime import date

import pytest

from scraper import Flight, _format_swedish_date, _parse_flight_text


class TestFormatSwedishDate:
    def test_wednesday(self):
        assert _format_swedish_date(date(2024, 12, 18)) == "ons 18 dec."

    def test_monday(self):
        assert _format_swedish_date(date(2024, 12, 16)) == "mån 16 dec."

    def test_saturday(self):
        assert _format_swedish_date(date(2024, 12, 21)) == "lör 21 dec."

    def test_day_number_no_leading_zero(self):
        assert _format_swedish_date(date(2025, 1, 5)) == "sön 5 jan."

    def test_january(self):
        assert _format_swedish_date(date(2025, 1, 10)) == "fre 10 jan."

    def test_ends_with_period(self):
        result = _format_swedish_date(date(2024, 12, 14))
        assert result.endswith(".")


class TestParseFlightText:
    def test_basic_economy_flight(self):
        text = "Air France\nEconomy\n45 000 poäng\nvia Paris"
        flight = _parse_flight_text(text, "ARN", "GIG", date(2024, 12, 16))
        assert flight is not None
        assert flight.points == 45000
        assert flight.airline == "Air France"
        assert flight.cabin == "Economy"
        assert flight.via == "Paris"

    def test_business_flight(self):
        text = "Lufthansa\nBusiness Class\n80 000 poäng"
        flight = _parse_flight_text(text, "ARN", "GIG", date(2024, 12, 16))
        assert flight is not None
        assert flight.points == 80000
        assert flight.cabin == "Business"

    def test_no_via(self):
        text = "KLM\nEconomy\n45 000 poäng"
        flight = _parse_flight_text(text, "ARN", "GIG", date(2024, 12, 16))
        assert flight is not None
        assert flight.via is None

    def test_nonbreaking_space_in_points(self):
        # SAS sometimes uses U+00A0 as the thousands separator
        text = "Air France\nEconomy\n45 000 poäng"
        flight = _parse_flight_text(text, "ARN", "GIG", date(2024, 12, 16))
        assert flight is not None
        assert flight.points == 45000

    def test_points_without_trailing_word(self):
        # Some cards omit "poäng" and show a bare number
        text = "Swiss\nBusiness\n80000"
        flight = _parse_flight_text(text, "ARN", "GIG", date(2024, 12, 16))
        assert flight is not None
        assert flight.points == 80000

    def test_no_points_returns_none(self):
        text = "Air France\nEconomy\n"
        assert _parse_flight_text(text, "ARN", "GIG", date(2024, 12, 16)) is None

    def test_empty_string_returns_none(self):
        assert _parse_flight_text("", "ARN", "GIG", date(2024, 12, 16)) is None

    def test_date_preserved(self):
        text = "KLM\nEconomy\n45 000 poäng"
        search_date = date(2025, 1, 12)
        flight = _parse_flight_text(text, "ARN", "GIG", search_date)
        assert flight is not None
        assert flight.date == search_date

    def test_unknown_airline(self):
        text = "Some Unknown Carrier\nEconomy\n45 000 poäng"
        flight = _parse_flight_text(text, "ARN", "GIG", date(2024, 12, 16))
        assert flight is not None
        assert flight.airline == "Unknown"
