"""Wrapper for the Climatiq API (carbon calculations)."""
import os
import logging
import requests

logger = logging.getLogger(__name__)

CLIMATIQ_URL = "https://api.climatiq.io/data/v1/estimate"

# Fallback emission factors (kg CO2e per passenger-km)
FALLBACK_FACTORS = {
    "flight": 0.255,
    "train": 0.041,
    "bus": 0.105,
    "car": 0.171,
}

# Rough distance table (km) for common city pairs (for demo purposes)
CITY_DISTANCES = {
    ("london", "paris"): 344,
    ("london", "berlin"): 932,
    ("paris", "berlin"): 878,
    ("new york", "london"): 5570,
}


def _estimate_distance(origin: str, destination: str) -> float:
    key = tuple(sorted([origin.lower(), destination.lower()]))
    return CITY_DISTANCES.get(key, 1000.0)  # default 1000 km


def calculate_carbon(origin: str, destination: str, transport_mode: str,
                     distance_km: float | None = None) -> dict:
    """Return {'co2e': float, 'source': 'climatiq'|'fallback'}."""
    if distance_km is None:
        distance_km = _estimate_distance(origin, destination)

    api_key = os.getenv("CLIMATIQ_API_KEY")
    if api_key:
        try:
            activity_id = {
                "flight": "passenger_flight-route_type_domestic-aircraft_type_na-occupancy_na",
                "train": "passenger_train-route_type_na-fuel_type_na-occupancy_na",
                "bus": "passenger_vehicle-vehicle_type_bus-fuel_source_na",
                "car": "passenger_vehicle-vehicle_type_car-fuel_source_petrol",
            }.get(transport_mode)

            if activity_id:
                resp = requests.post(
                    CLIMATIQ_URL,
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "emission_factor": {"activity_id": activity_id},
                        "parameters": {
                            "distance": distance_km,
                            "distance_unit": "km",
                        },
                    },
                    timeout=5,
                )
                resp.raise_for_status()
                data = resp.json()
                return {"co2e": float(data["co2e"]), "source": "climatiq"}
        except Exception as e:
            logger.warning("Climatiq call failed: %s — using fallback", e)

    factor = FALLBACK_FACTORS.get(transport_mode, 0.15)
    return {"co2e": round(factor * distance_km, 2), "source": "fallback"}
