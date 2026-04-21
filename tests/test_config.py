import pytest
from datetime import date
from config import load_config, Config, Trip, Leg, DateRange, EmailConfig
import yaml, os, tempfile

SAMPLE_YAML = """
trips:
  - name: "ARN to GIG"
    outbound:
      origin: ARN
      destination: GIG
      date_from: 2024-12-14
      date_to: 2024-12-21
    return:
      origin: GIG
      destination: ARN
      date_from: 2025-01-10
      date_to: 2025-01-16
    alert_mode: complete_trip
email:
  sender: a@example.com
  recipient: b@example.com
"""

@pytest.fixture
def config_file(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text(SAMPLE_YAML)
    return str(p)

def test_load_config_returns_config(config_file):
    cfg = load_config(config_file)
    assert isinstance(cfg, Config)

def test_trip_name(config_file):
    cfg = load_config(config_file)
    assert cfg.trips[0].name == "ARN to GIG"

def test_outbound_leg(config_file):
    cfg = load_config(config_file)
    leg = cfg.trips[0].outbound
    assert leg.origin == "ARN"
    assert leg.destination == "GIG"
    assert leg.date_range.date_from == date(2024, 12, 14)
    assert leg.date_range.date_to == date(2024, 12, 21)

def test_return_leg(config_file):
    cfg = load_config(config_file)
    leg = cfg.trips[0].return_leg
    assert leg is not None
    assert leg.origin == "GIG"
    assert leg.date_range.date_from == date(2025, 1, 10)

def test_alert_mode(config_file):
    cfg = load_config(config_file)
    assert cfg.trips[0].alert_mode == "complete_trip"

def test_email_config(config_file):
    cfg = load_config(config_file)
    assert cfg.email.sender == "a@example.com"
    assert cfg.email.recipient == "b@example.com"

def test_date_range_yields_all_dates(config_file):
    cfg = load_config(config_file)
    dates = list(cfg.trips[0].outbound.date_range.dates())
    assert dates[0] == date(2024, 12, 14)
    assert dates[-1] == date(2024, 12, 21)
    assert len(dates) == 8

def test_no_return_leg_is_none():
    yaml_str = """
trips:
  - name: "One way"
    outbound:
      origin: ARN
      destination: CDG
      date_from: 2024-12-14
      date_to: 2024-12-14
    alert_mode: any_leg
email:
  sender: a@example.com
  recipient: b@example.com
"""
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_str)
        name = f.name
    cfg = load_config(name)
    assert cfg.trips[0].return_leg is None
    os.unlink(name)
