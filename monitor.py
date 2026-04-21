from typing import List
from config import Trip
from scraper import Flight


def evaluate_alert(trip: Trip, outbound: List[Flight], returns: List[Flight]) -> bool:
    if trip.alert_mode == "complete_trip":
        return len(outbound) > 0 and len(returns) > 0
    if trip.alert_mode == "any_leg":
        return len(outbound) > 0 or len(returns) > 0
    return False
