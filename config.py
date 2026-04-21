from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional, List, Iterator
import yaml


@dataclass
class DateRange:
    date_from: date
    date_to: date

    def dates(self) -> Iterator[date]:
        current = self.date_from
        while current <= self.date_to:
            yield current
            current += timedelta(days=1)


@dataclass
class Leg:
    origin: str
    destination: str
    date_range: DateRange


@dataclass
class Trip:
    name: str
    outbound: Leg
    return_leg: Optional[Leg]
    alert_mode: str  # "complete_trip" | "any_leg"


@dataclass
class EmailConfig:
    sender: str
    recipient: str


@dataclass
class Config:
    trips: List[Trip]
    email: EmailConfig


def _parse_leg(data: dict) -> Leg:
    return Leg(
        origin=data["origin"],
        destination=data["destination"],
        date_range=DateRange(
            date_from=data["date_from"],
            date_to=data["date_to"],
        ),
    )


def load_config(path: str = "config.yaml") -> Config:
    with open(path) as f:
        data = yaml.safe_load(f)

    trips = []
    for t in data["trips"]:
        return_leg = _parse_leg(t["return"]) if "return" in t else None
        trips.append(Trip(
            name=t["name"],
            outbound=_parse_leg(t["outbound"]),
            return_leg=return_leg,
            alert_mode=t["alert_mode"],
        ))

    return Config(
        trips=trips,
        email=EmailConfig(
            sender=data["email"]["sender"],
            recipient=data["email"]["recipient"],
        ),
    )
