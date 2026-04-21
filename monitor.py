import logging
import sys
from typing import List

from config import Trip, load_config
from notifier import format_email_body, format_subject, send_email
from scraper import Flight, search_flights

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def evaluate_alert(trip: Trip, outbound: List[Flight], returns: List[Flight]) -> bool:
    if trip.alert_mode == "complete_trip":
        return len(outbound) > 0 and len(returns) > 0
    if trip.alert_mode == "any_leg":
        return len(outbound) > 0 or len(returns) > 0
    return False


def run_trip(trip: Trip) -> tuple[List[Flight], List[Flight]]:
    outbound_flights: List[Flight] = []
    return_flights: List[Flight] = []

    logger.info(f"Searching outbound: {trip.outbound.origin}->{trip.outbound.destination}")
    for d in trip.outbound.date_range.dates():
        results = search_flights(trip.outbound.origin, trip.outbound.destination, d)
        logger.info(f"  {d}: {len(results)} flight(s)")
        outbound_flights.extend(results)

    if trip.return_leg:
        logger.info(f"Searching return: {trip.return_leg.origin}->{trip.return_leg.destination}")
        for d in trip.return_leg.date_range.dates():
            results = search_flights(trip.return_leg.origin, trip.return_leg.destination, d)
            logger.info(f"  {d}: {len(results)} flight(s)")
            return_flights.extend(results)

    return outbound_flights, return_flights


def main() -> None:
    cfg = load_config()

    for trip in cfg.trips:
        logger.info(f"=== Processing trip: {trip.name} ===")
        outbound, returns = run_trip(trip)

        if evaluate_alert(trip, outbound, returns):
            subject = format_subject(trip.name)
            body = format_email_body(trip.name, outbound, returns)
            send_email(cfg.email.sender, cfg.email.recipient, subject, body)
        else:
            logger.info(f"No alert condition met for: {trip.name}")


if __name__ == "__main__":
    main()
