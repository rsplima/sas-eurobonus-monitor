from datetime import date
from scraper import Flight
from notifier import format_email_body, format_subject


def make_flight(d: date, airline: str, cabin: str, points: int, via: str, origin: str = "ARN", destination: str = "GIG") -> Flight:
    return Flight(date=d, origin=origin, destination=destination, airline=airline, cabin=cabin, points=points, via=via)


def test_subject_contains_trip_name():
    subject = format_subject("ARN -> GIG December")
    assert "ARN -> GIG December" in subject
    assert "[SAS Monitor]" in subject


def test_body_shows_outbound_flights():
    flights = [make_flight(date(2024, 12, 16), "Air France", "Economy", 45000, "CDG")]
    body = format_email_body("ARN -> GIG December", flights, [])
    assert "Dec 16" in body
    assert "Air France" in body
    assert "CDG" in body
    assert "45,000" in body
    assert "Economy" in body


def test_body_shows_return_flights():
    flights = [make_flight(date(2025, 1, 12), "KLM", "Business", 80000, "AMS")]
    body = format_email_body("ARN -> GIG December", [], flights)
    assert "Jan 12" in body
    assert "KLM" in body
    assert "80,000" in body


def test_body_shows_complete_trip_message():
    out = [make_flight(date(2024, 12, 16), "Air France", "Economy", 45000, "CDG")]
    ret = [make_flight(date(2025, 1, 12), "KLM", "Economy", 45000, "AMS")]
    body = format_email_body("ARN -> GIG December", out, ret)
    assert "complete trip" in body.lower()


def test_body_no_via_when_none():
    flights = [Flight(date=date(2024, 12, 16), origin="ARN", destination="GIG", airline="SAS", cabin="Economy", points=30000, via=None)]
    body = format_email_body("Test", flights, [])
    assert "None" not in body


def test_body_contains_search_link():
    flights = [make_flight(date(2024, 12, 16), "Air France", "Economy", 45000, "CDG")]
    body = format_email_body("ARN -> GIG December", flights, [])
    assert "award-finder" in body
    assert "fromCity=ARN" in body
    assert "toCity=GIG" in body
    assert "departure=2024-12-16" in body


def test_body_multiple_outbound_flights():
    flights = [
        make_flight(date(2024, 12, 16), "Air France", "Economy", 45000, "CDG"),
        make_flight(date(2024, 12, 19), "KLM", "Business", 80000, "AMS"),
    ]
    body = format_email_body("Test", flights, [])
    assert "Dec 16" in body
    assert "Dec 19" in body
