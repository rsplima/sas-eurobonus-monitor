from datetime import date
from scraper import Flight
from config import Trip, Leg, DateRange
from monitor import evaluate_alert


def make_trip(alert_mode: str, has_return: bool = True) -> Trip:
    outbound = Leg("ARN", "GIG", DateRange(date(2024, 12, 14), date(2024, 12, 21)))
    return_leg = Leg("GIG", "ARN", DateRange(date(2025, 1, 10), date(2025, 1, 16))) if has_return else None
    return Trip(name="Test", outbound=outbound, return_leg=return_leg, alert_mode=alert_mode)


def make_flight(d: date = date(2024, 12, 16)) -> Flight:
    return Flight(date=d, airline="Air France", cabin="Economy", points=45000, via="CDG")


def test_complete_trip_both_legs_found():
    trip = make_trip("complete_trip")
    assert evaluate_alert(trip, [make_flight()], [make_flight()]) is True


def test_complete_trip_only_outbound_found():
    trip = make_trip("complete_trip")
    assert evaluate_alert(trip, [make_flight()], []) is False


def test_complete_trip_only_return_found():
    trip = make_trip("complete_trip")
    assert evaluate_alert(trip, [], [make_flight()]) is False


def test_complete_trip_neither_found():
    trip = make_trip("complete_trip")
    assert evaluate_alert(trip, [], []) is False


def test_any_leg_outbound_only():
    trip = make_trip("any_leg")
    assert evaluate_alert(trip, [make_flight()], []) is True


def test_any_leg_return_only():
    trip = make_trip("any_leg")
    assert evaluate_alert(trip, [], [make_flight()]) is True


def test_any_leg_both_found():
    trip = make_trip("any_leg")
    assert evaluate_alert(trip, [make_flight()], [make_flight()]) is True


def test_any_leg_neither_found():
    trip = make_trip("any_leg")
    assert evaluate_alert(trip, [], []) is False
