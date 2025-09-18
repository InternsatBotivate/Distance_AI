import os
import requests
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Coordinates:
    latitude: str
    longitude: str

def geocode(address: str, api_key: str = None) -> Coordinates:
    """
    Drop-in replacement for your old geocode() function.
    Uses Positionstack API instead of OpenCage / geopy.
    Returns a Coordinates object with .latitude and .longitude.
    If not found, both are set to "Not found".
    """
    if api_key is None:
        api_key = os.getenv("POSITIONSTACK_API_KEY")

    url = "http://api.positionstack.com/v1/forward"
    params = {"access_key": api_key, "query": address, "limit": 1}

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get("data"):
            loc = data["data"][0]
            return Coordinates(str(loc["latitude"]), str(loc["longitude"]))
    except Exception as e:
        print(f"Geocode error for {address}: {e}")

    return Coordinates("Not found", "Not found")
