from dataclasses import dataclass
from datetime import date
from typing import List, Optional
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class Flight:
    date: date
    airline: str
    cabin: str
    points: int
    via: Optional[str]


def search_flights(origin: str, destination: str, search_date: date) -> List[Flight]:
    """Search flysas.com bonus trips for one specific date. Returns empty list if none found or on error."""
    for attempt in range(3):
        try:
            return _run_search(origin, destination, search_date)
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed for {origin}→{destination} {search_date}: {e}")
            if attempt < 2:
                time.sleep(5)
    logger.error(f"All attempts failed for {origin}→{destination} {search_date}")
    return []


def _run_search(origin: str, destination: str, search_date: date) -> List[Flight]:
    # Implemented in Task 4 after site investigation
    raise NotImplementedError
