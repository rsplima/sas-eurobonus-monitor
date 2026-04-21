# SAS Eurobonus Monitor

Monitors flysas.com for bonus flight availability and emails you when seats appear on configured routes.

## Prerequisites

- Python 3.11+
- A Gmail account with [App Password](https://myaccount.google.com/apppasswords) enabled
- SAS EuroBonus account credentials (required to log in to the award-finder)

## Installation

```bash
git clone https://github.com/rsplima/sas-eurobonus-monitor.git
cd sas-eurobonus-monitor
pip install -r requirements.txt
playwright install chromium
```

## Configuration

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml`:

- Set `sender` and `recipient` to your Gmail address
- Edit the `trips` section with your routes and date ranges
- Set `alert_mode` to `complete_trip` or `any_leg` (see below)

`config.yaml` is gitignored — your email address stays local.

## Running Manually

```bash
SAS_USERNAME=your@email.com \
SAS_PASSWORD=your_eurobonus_password \
SMTP_PASSWORD=your_gmail_app_password \
python monitor.py
```

The first run opens a browser session and saves session cookies to `~/.sas_session.json`. Subsequent runs reuse them and skip the login step.

## Scheduling (macOS cron)

Run once daily at 08:00:

```bash
crontab -e
```

Add this line (replace paths and credentials):

```
0 8 * * * cd /Users/yourname/sas-eurobonus-monitor && SAS_USERNAME=you@email.com SAS_PASSWORD=yourpass SMTP_PASSWORD=yourapppassword /usr/bin/python3 monitor.py >> /tmp/sas-monitor.log 2>&1
```

## Alert Modes

| Mode | Triggers when |
|------|--------------|
| `complete_trip` | At least one outbound date AND one return date have seats |
| `any_leg` | Any seat found on any searched date |

## Notes

- The scraper navigates flysas.com with a stealth Playwright context (Swedish locale, real user-agent)
- A 3-second polite delay is applied between each date search
- Failed searches are retried up to 3 times before being skipped
- If a session cookie expires, the script re-authenticates automatically
