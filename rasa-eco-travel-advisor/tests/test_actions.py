"""Unit tests for action helpers."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from actions.climate_api import calculate_carbon
from actions.ranking import rank_options
from actions.amadeus_api import fetch_hotels


def test_calculate_carbon_fallback():
    r = calculate_carbon("london", "paris", "train")
    assert r["co2e"] > 0
    assert r["source"] in ("climatiq", "fallback")


def test_rank_options_high_sustainability():
    opts = [
        {"name": "A", "price": 200, "eco_rating": 5, "carbon_kg": 10},
        {"name": "B", "price": 100, "eco_rating": 2, "carbon_kg": 50},
    ]
    ranked = rank_options(opts, "high")
    assert ranked[0]["name"] == "A"  # low-carbon wins when eco-first


def test_rank_options_low_sustainability():
    opts = [
        {"name": "A", "price": 200, "eco_rating": 5, "carbon_kg": 10},
        {"name": "B", "price": 100, "eco_rating": 2, "carbon_kg": 50},
    ]
    ranked = rank_options(opts, "low")
    assert ranked[0]["name"] == "B"  # cheap wins when price-first


def test_fetch_hotels_mock():
    hotels = fetch_hotels("paris")
    assert len(hotels) > 0
    assert "name" in hotels[0]
