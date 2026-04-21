"""SAS EuroBonus partner bonus flight scraper.

Searches the SAS award-finder page for available partner bonus flights.
Authentication is required: set SAS_USERNAME and SAS_PASSWORD environment variables,
or store a session cookie file at ~/.sas_session.json.
"""
from dataclasses import dataclass
from datetime import date
from typing import List, Optional
import json
import logging
import os
import time

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)

# Swedish date abbreviations for parsing tab labels
SWEDISH_DAYS = {0: 'mån', 1: 'tis', 2: 'ons', 3: 'tors', 4: 'fre', 5: 'lör', 6: 'sön'}
SWEDISH_MONTHS = {
    1: 'jan', 2: 'feb', 3: 'mar', 4: 'apr', 5: 'maj', 6: 'jun',
    7: 'jul', 8: 'aug', 9: 'sep', 10: 'okt', 11: 'nov', 12: 'dec',
}

# Page URLs
AWARD_FINDER_URL = "https://www.sas.se/award-finder"
AUTH_URL = "https://auth.flysas.com/u/login/identifier"
SESSION_COOKIE_PATH = os.path.expanduser("~/.sas_session.json")


@dataclass
class Flight:
    date: date
    airline: str
    cabin: str
    points: int
    via: Optional[str]


def _format_swedish_date(d: date) -> str:
    """Format a date in Swedish tab format: 'ons 16 dec.'"""
    return f"{SWEDISH_DAYS[d.weekday()]} {d.day} {SWEDISH_MONTHS[d.month]}."


def search_flights(origin: str, destination: str, search_date: date) -> List[Flight]:
    """Search SAS bonus trips for one specific date. Returns empty list if none found or on error."""
    for attempt in range(3):
        try:
            return _run_search(origin, destination, search_date)
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed for {origin}->{destination} {search_date}: {e}")
            if attempt < 2:
                time.sleep(5)
    logger.error(f"All attempts failed for {origin}->{destination} {search_date}")
    return []


def _build_stealth_context(playwright, headless: bool = True):
    """Create a browser context with anti-bot settings."""
    browser = playwright.chromium.launch(
        headless=headless,
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
    )
    context = browser.new_context(
        locale="sv-SE",
        viewport={"width": 1280, "height": 900},
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        extra_http_headers={"Accept-Language": "sv-SE,sv;q=0.9,en;q=0.8"},
    )
    context.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
    )
    return browser, context


def _load_session_cookies(context) -> bool:
    """Load saved session cookies if they exist. Returns True if loaded."""
    if os.path.exists(SESSION_COOKIE_PATH):
        try:
            with open(SESSION_COOKIE_PATH) as f:
                cookies = json.load(f)
            context.add_cookies(cookies)
            logger.debug(f"Loaded {len(cookies)} session cookies from {SESSION_COOKIE_PATH}")
            return True
        except Exception as e:
            logger.warning(f"Failed to load session cookies: {e}")
    return False


def _save_session_cookies(context) -> None:
    """Save current session cookies for reuse."""
    try:
        cookies = context.cookies()
        with open(SESSION_COOKIE_PATH, "w") as f:
            json.dump(cookies, f)
        logger.debug(f"Saved {len(cookies)} session cookies to {SESSION_COOKIE_PATH}")
    except Exception as e:
        logger.warning(f"Failed to save session cookies: {e}")


def _accept_cookies(page) -> None:
    """Accept cookie banner if present. Handles both old and new SAS cookie dialogs."""
    # New Next.js style (award-finder page) - uses a <dialog> element
    for selector in [
        "button:has-text('Acceptera alla')",
        "button:has-text('ACCEPTERA')",
        "button:has-text('Acceptera')",
        "button:has-text('Accept all')",
        "[data-testid='accept-all-cookies']",
        "button:has-text('Godkänn')",
    ]:
        try:
            btn = page.locator(selector)
            if btn.count() > 0 and btn.first.is_visible():
                btn.first.click(timeout=3000)
                page.wait_for_timeout(1000)
                logger.debug(f"Accepted cookies via: {selector}")
                return
        except PlaywrightTimeout:
            pass

    # Try force-clicking any visible cookie button via JS
    page.evaluate("""() => {
        const texts = ['Acceptera alla', 'ACCEPTERA', 'Acceptera', 'Accept all'];
        for (const text of texts) {
            const btns = Array.from(document.querySelectorAll('button'));
            for (const btn of btns) {
                if (btn.textContent.trim().toLowerCase().includes(text.toLowerCase())) {
                    btn.click();
                    return text;
                }
            }
        }
        return null;
    }""")
    page.wait_for_timeout(500)


def _login(page) -> bool:
    """
    Log in to SAS using SAS_USERNAME and SAS_PASSWORD env vars.
    Returns True if login was successful.
    """
    username = os.environ.get("SAS_USERNAME", "").strip()
    password = os.environ.get("SAS_PASSWORD", "").strip()

    if not username or not password:
        logger.warning(
            "SAS_USERNAME and/or SAS_PASSWORD not set. "
            "Cannot authenticate — flight results will be empty."
        )
        return False

    try:
        # Navigate to the auth login page
        page.wait_for_load_state("domcontentloaded")
        logger.debug(f"Login page URL: {page.url}")

        # Accept cookies on auth page if needed
        _accept_cookies(page)

        # Fill username (email/EuroBonus number)
        # The auth0 login page has an input with name="username" or id="username"
        username_input = page.locator(
            "input[name='username'], input[id='username'], input[type='email'], input[type='text']"
        ).first
        username_input.fill(username, timeout=10000)
        page.wait_for_timeout(300)

        # Click Continue/Next
        for selector in [
            "button[type='submit']",
            "button:has-text('Fortsätt')",
            "button:has-text('Continue')",
            "button:has-text('Nästa')",
        ]:
            btn = page.locator(selector)
            if btn.count() > 0 and btn.first.is_visible():
                btn.first.click()
                page.wait_for_timeout(1500)
                break

        # Fill password
        password_input = page.locator(
            "input[name='password'], input[type='password']"
        ).first
        password_input.fill(password, timeout=10000)
        page.wait_for_timeout(300)

        # Submit login
        for selector in [
            "button[type='submit']",
            "button:has-text('Logga in')",
            "button:has-text('Log in')",
            "button:has-text('Login')",
            "button:has-text('Sign in')",
        ]:
            btn = page.locator(selector)
            if btn.count() > 0 and btn.first.is_visible():
                btn.first.click()
                break

        # Wait for navigation away from auth page
        page.wait_for_url(
            lambda url: "auth.flysas.com" not in url,
            timeout=15000,
        )
        logger.info("Login successful")
        return True

    except PlaywrightTimeout as e:
        logger.warning(f"Login timed out: {e}")
        return False
    except Exception as e:
        logger.warning(f"Login failed: {e}")
        return False


def _navigate_to_date_tab(page, table_testid: str, search_date: date) -> bool:
    """
    Navigate the 3-day date slider to find and click the tab for search_date.
    The slider shows 3 dates at a time; we may need to click prev/next arrows.

    Returns True if the date tab was found and clicked, False otherwise.
    """
    target_label = _format_swedish_date(search_date)
    logger.debug(f"Looking for date tab: {target_label!r} in {table_testid}")

    table = page.locator(f'[data-testid="{table_testid}"]')

    for _ in range(30):  # Max 30 slider navigations (~30 days forward)
        # Look for a tab containing the target label text
        # Tabs are <li> elements inside a <ul> inside the table
        tabs = table.locator("ul li")
        for i in range(tabs.count()):
            tab = tabs.nth(i)
            try:
                tab_text = tab.inner_text().strip()
                if target_label.lower() in tab_text.lower():
                    logger.debug(f"Found date tab: {tab_text!r}")
                    tab.click()
                    page.wait_for_timeout(1000)
                    return True
            except Exception:
                pass

        # Date not visible — try clicking the next arrow
        # The arrows are typically SVG buttons near the date tabs
        # Look for buttons with aria-label containing "nästa" or "next" in the table
        next_btn = None
        for aria_label in ["nästa", "next", "fram", ">>"]:
            btn = table.locator(f"button[aria-label*='{aria_label}' i]")
            if btn.count() > 0:
                next_btn = btn.first
                break

        # Also try structural selectors - last li in the date nav should have a "next" button
        if next_btn is None:
            # Try to find prev/next in the date nav ul
            nav_ul = table.locator("ul")
            # Get buttons around the ul (siblings)
            all_btns = table.locator("button").all()
            # The next button is often to the right of the ul
            for btn in all_btns:
                try:
                    aria = btn.get_attribute("aria-label") or ""
                    btn_text = btn.inner_text().strip()
                    if not btn_text and not aria:
                        next_btn = btn
                except Exception:
                    pass

        if next_btn is None:
            logger.debug("No next button found in date slider")
            break

        try:
            next_btn.click(timeout=3000)
            page.wait_for_timeout(800)
        except PlaywrightTimeout:
            break

    logger.warning(f"Date tab {target_label!r} not found after navigation")
    return False


def _extract_flights(page, table_testid: str, search_date: date) -> List[Flight]:
    """
    Extract flight data from the outbound or inbound flights table.
    Returns a list of Flight objects (may be empty).
    """
    flights = []
    table = page.locator(f'[data-testid="{table_testid}"]')
    if table.count() == 0:
        return flights

    # Check for "no results" message
    table_text = table.inner_text()
    if "Vi kunde inte hitta några flygningar" in table_text:
        logger.debug(f"No flights found in {table_testid}")
        return flights

    # Look for flight cards/rows in the table
    # Based on DOM inspection: flight cards are inside the table's content div
    # after the date tabs (ul). We look for structural elements that represent flights.

    # Strategy 1: Look for any elements with points/poäng text pattern
    # Strategy 2: Look for child divs/articles/sections that contain airline + point info

    # Try data-testid attributes on flight cards (if any)
    for testid_suffix in ["flight-card", "flight-row", "flight-item", "flight"]:
        cards = table.locator(f'[data-testid*="{testid_suffix}"]').all()
        if cards:
            logger.debug(f"Found {len(cards)} flight cards with testid={testid_suffix!r}")
            for card in cards:
                flight = _parse_flight_card(card, search_date)
                if flight:
                    flights.append(flight)
            if flights:
                return flights

    # Fallback: look for li elements inside the results area (below the date tab ul)
    # The table has: ul (date tabs) + div (results)
    # Get the div after the ul
    result_div = table.locator("ul + div, ul ~ div").first
    if result_div.count() > 0:
        # Look for flight-like children
        children = result_div.locator("> *, li, article, section").all()
        for child in children:
            try:
                text = child.inner_text().strip()
                if not text or "Vi kunde inte hitta" in text:
                    continue
                flight = _parse_flight_text(text, search_date)
                if flight:
                    flights.append(flight)
            except Exception:
                pass

    logger.debug(f"Extracted {len(flights)} flights from {table_testid}")
    return flights


def _parse_flight_card(element, search_date: date) -> Optional[Flight]:
    """Parse a single flight card element into a Flight dataclass."""
    try:
        text = element.inner_text()
        return _parse_flight_text(text, search_date)
    except Exception:
        return None


def _parse_flight_text(text: str, search_date: date) -> Optional[Flight]:
    """
    Parse flight text to extract airline, cabin, and points.
    Expected format varies but typically contains:
    - Airline name (e.g., "Lufthansa", "Swiss", "Air France")
    - Cabin class (e.g., "Economy", "Business", "Go", "Plus")
    - Points amount (e.g., "45 000 poäng" or "45,000")
    - Optional via city (e.g., "via Frankfurt")
    """
    import re

    text = text.strip()
    if not text:
        return None

    # Extract points — look for numbers followed by "poäng" or "p"
    # SAS uses space-separated thousands: "45 000 poäng" or "45 000p"
    points_match = re.search(
        r'(\d[\d\s ]+)\s*(?:poäng|p\b)',
        text,
        re.IGNORECASE,
    )
    if not points_match:
        # Try plain number patterns like "45000" or "45,000"
        points_match = re.search(r'(\d{4,6}(?:[,\s]\d{3})*)', text)

    points = 0
    if points_match:
        raw = points_match.group(1).replace(' ', '').replace(' ', '').replace(',', '')
        try:
            points = int(raw)
        except ValueError:
            pass

    if points == 0:
        return None  # Can't parse flight without point info

    # Extract cabin class
    cabin = "Economy"  # default
    cabin_patterns = {
        "Business": ["business", "business class"],
        "Premium": ["premium", "plus"],
        "Go": ["go light", "go"],
        "Economy": ["economy", "eco"],
    }
    text_lower = text.lower()
    for cabin_name, patterns in cabin_patterns.items():
        if any(p in text_lower for p in patterns):
            cabin = cabin_name
            break

    # Extract airline — look for known airline names
    airline = "Unknown"
    known_airlines = [
        "Lufthansa", "Swiss", "Air France", "KLM", "British Airways",
        "Iberia", "TAP", "Finnair", "Austrian", "Brussels", "Eurowings",
        "Singapore Airlines", "Thai", "United", "Delta", "American",
        "Star Alliance", "SkyTeam", "Oneworld", "SAS",
    ]
    for name in known_airlines:
        if name.lower() in text_lower:
            airline = name
            break

    # Extract via city
    via = None
    via_match = re.search(r'via\s+([A-Za-zÀ-ÖØ-öø-ÿ\s]+?)(?:\n|,|$)', text, re.IGNORECASE)
    if via_match:
        via = via_match.group(1).strip()
        if len(via) > 40:  # Sanity check
            via = None

    return Flight(
        date=search_date,
        airline=airline,
        cabin=cabin,
        points=points,
        via=via,
    )


def _run_search(origin: str, destination: str, search_date: date) -> List[Flight]:
    """
    Navigate to SAS award-finder, authenticate if needed, and extract flights.

    URL format: https://www.sas.se/award-finder?fromCity=ARN&toCity=GIG&departure=YYYY-MM-DD&tripType=ROUNDTRIP
    """
    date_str = search_date.strftime("%Y-%m-%d")
    search_url = (
        f"{AWARD_FINDER_URL}"
        f"?fromCity={origin}&toCity={destination}"
        f"&departure={date_str}&tripType=ROUNDTRIP"
    )

    with sync_playwright() as p:
        browser, context = _build_stealth_context(p, headless=True)

        try:
            # Load saved session cookies to avoid re-login
            _load_session_cookies(context)

            page = context.new_page()

            logger.info(f"Navigating to {search_url}")
            page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)

            # Accept cookie banner
            _accept_cookies(page)
            page.wait_for_timeout(500)

            # Check if we got redirected to login
            if "auth.flysas.com" in page.url or "/login" in page.url.lower():
                logger.info("Login required — attempting authentication")
                if not _login(page):
                    logger.warning("Login failed — returning empty results")
                    return []
                # After login, should redirect back to search URL
                page.wait_for_timeout(2000)
                _save_session_cookies(context)

                # Navigate to search URL if we're not already there
                if "award-finder" not in page.url:
                    logger.debug(f"Navigating back to: {search_url}")
                    page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(3000)
                    _accept_cookies(page)

            # Wait for the outbound flights table
            outbound_testid = "flights-table-outbound"
            try:
                page.wait_for_selector(
                    f'[data-testid="{outbound_testid}"]',
                    timeout=20000,
                    state="visible",
                )
            except PlaywrightTimeout:
                logger.warning(
                    f"Outbound flights table not found for {origin}->{destination} {date_str}. "
                    f"Page title: {page.title()!r}, URL: {page.url}"
                )
                # Save debug HTML
                try:
                    debug_html = page.content()
                    debug_path = f"/tmp/sas_debug_{origin}_{destination}_{date_str}.html"
                    with open(debug_path, "w") as f:
                        f.write(debug_html)
                    logger.debug(f"Debug HTML saved to {debug_path}")
                except Exception:
                    pass
                return []

            # The page might load showing the nearest available date, not our target.
            # Navigate the date slider to get to search_date.
            _navigate_to_date_tab(page, outbound_testid, search_date)

            # Check for "no results" in outbound table
            outbound_table = page.locator(f'[data-testid="{outbound_testid}"]')
            if outbound_table.count() == 0:
                return []

            outbound_text = outbound_table.inner_text()
            if "Vi kunde inte hitta några flygningar" in outbound_text:
                logger.info(f"No flights found for {origin}->{destination} on {date_str}")
                time.sleep(3)  # Polite delay
                return []

            # Extract flights
            flights = _extract_flights(page, outbound_testid, search_date)
            logger.info(f"Found {len(flights)} flights for {origin}->{destination} on {date_str}")

            time.sleep(3)  # Polite delay to server
            return flights

        finally:
            browser.close()
