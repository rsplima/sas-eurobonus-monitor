import logging
import os
import smtplib
from email.mime.text import MIMEText
from typing import List

from scraper import Flight

logger = logging.getLogger(__name__)


def format_subject(trip_name: str) -> str:
    return f"[SAS Monitor] Seats available — {trip_name}"


def format_email_body(trip_name: str, outbound: List[Flight], returns: List[Flight]) -> str:
    lines = [f"SAS Eurobonus monitor found available seats for: {trip_name}", ""]

    if outbound:
        lines.append("Outbound seats found:")
        for f in outbound:
            via = f" via {f.via}" if f.via else ""
            lines.append(f"  * {f.date.strftime('%b %d')} — {f.airline}{via} — {f.cabin} — {f.points:,} pts")

    if returns:
        lines.append("")
        lines.append("Return seats found:")
        for f in returns:
            via = f" via {f.via}" if f.via else ""
            lines.append(f"  * {f.date.strftime('%b %d')} — {f.airline}{via} — {f.cabin} — {f.points:,} pts")

    lines.append("")
    if outbound and returns:
        lines.append("-> A complete trip is bookable. Go to flysas.com to book.")
    else:
        lines.append("-> Go to flysas.com to book.")

    return "\n".join(lines)


def send_email(sender: str, recipient: str, subject: str, body: str) -> None:
    password = os.environ["SMTP_PASSWORD"]
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, recipient, msg.as_string())
        logger.info(f"Alert email sent to {recipient}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
