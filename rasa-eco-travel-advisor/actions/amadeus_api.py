"""Wrapper for Amadeus for Developers sandbox (hotels)."""
import os
import logging
import requests

logger = logging.getLogger(__name__)

AMADEUS_TOKEN_URL  = "https://test.api.amadeus.com/v1/security/oauth2/token"
AMADEUS_HOTELS_URL = "https://test.api.amadeus.com/v1/reference-data/locations/hotels/by-city"

MOCK_HOTELS = {
    "paris": [
        {"name": "Green Paris Hotel",  "price": 180, "eco_rating": 5, "carbon_kg": 12, "city": "Paris"},
        {"name": "Eco Stay Marais",    "price": 140, "eco_rating": 4, "carbon_kg": 18, "city": "Paris"},
        {"name": "Budget Inn Paris",   "price": 90,  "eco_rating": 2, "carbon_kg": 35, "city": "Paris"},
    ],
    "bali": [
        {"name": "Ubud Eco Retreat",   "price": 200, "eco_rating": 5, "carbon_kg": 10, "city": "Bali"},
        {"name": "Beachside Bamboo",   "price": 150, "eco_rating": 4, "carbon_kg": 15, "city": "Bali"},
    ],
    "berlin": [
        {"name": "Berlin Green Hostel","price": 70,  "eco_rating": 4, "carbon_kg": 8,  "city": "Berlin"},
        {"name": "Eco Loft Mitte",     "price": 160, "eco_rating": 5, "carbon_kg": 11, "city": "Berlin"},
    ],
    "tokyo": [
        {"name": "Sakura Eco Inn",     "price": 190, "eco_rating": 5, "carbon_kg": 14, "city": "Tokyo"},
        {"name": "Tokyo Green Capsule","price": 60,  "eco_rating": 4, "carbon_kg": 9,  "city": "Tokyo"},
    ],
    "nairobi": [
        {"name": "Karura Forest Lodge","price": 130, "eco_rating": 5, "carbon_kg": 7,  "city": "Nairobi"},
        {"name": "Nairobi Eco Hostel", "price": 55,  "eco_rating": 4, "carbon_kg": 11, "city": "Nairobi"},
    ],
    "london": [
        {"name": "London Green Pod",   "price": 210, "eco_rating": 5, "carbon_kg": 13, "city": "London"},
    ],
    "amsterdam": [
        {"name": "Amsterdam Eco Boat", "price": 175, "eco_rating": 5, "carbon_kg": 9,  "city": "Amsterdam"},
    ],
    "rome": [
        {"name": "Roma Eco Suites",    "price": 165, "eco_rating": 4, "carbon_kg": 12, "city": "Rome"},
    ],
}


def _get_token():
    cid    = os.getenv("AMADEUS_CLIENT_ID")
    secret = os.getenv("AMADEUS_CLIENT_SECRET")
    if not (cid and secret):
        return None
    try:
        r = requests.post(
            AMADEUS_TOKEN_URL,
            data={"grant_type": "client_credentials",
                  "client_id": cid, "client_secret": secret},
            timeout=5,
        )
        r.raise_for_status()
        return r.json()["access_token"]
    except Exception as e:
        logger.warning("Amadeus auth failed: %s", e)
        return None


def fetch_hotels(city: str) -> list:
    """Return list of hotel dicts. Falls back to mock data if API unavailable."""
    city_key = (city or "paris").lower().strip()

    token = _get_token()
    if token:
        try:
            r = requests.get(
                AMADEUS_HOTELS_URL,
                headers={"Authorization": f"Bearer {token}"},
                params={"cityCode": city_key[:3].upper(), "radius": 5, "radiusUnit": "KM"},
                timeout=5,
            )
            r.raise_for_status()
            raw = r.json().get("data", [])
            hotels = []
            for h in raw[:5]:
                hotels.append({
                    "name": h.get("name", "Unknown"),
                    "price": 150,
                    "eco_rating": 3,
                    "carbon_kg": 20,
                    "city": city,
                })
            if hotels:
                return hotels
        except Exception as e:
            logger.warning("Amadeus fetch failed: %s — using mock", e)

    return MOCK_HOTELS.get(city_key, MOCK_HOTELS["paris"])