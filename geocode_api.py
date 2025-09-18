import os
import requests
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Coordinates:
    latitude: str
    longitude: str

def geocode(address: str, api_key: str = "YOUR_OPENCAGE_API_KEY") -> Coordinates:
    """
    Drop-in replacement for your old geocode() function.
    Uses OpenCage API instead of geopy / Nominatim.
    Returns a Coordinates object with .latitude and .longitude.
    If not found, both are set to "Not found".
    """
    url = "https://api.opencagedata.com/geocode/v1/json"
    params = {"q": address, "key": os.getenv("OPENCAGE_API_KEY")}

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get("results"):
            loc = data["results"][0]["geometry"]
            return Coordinates(str(loc["lat"]), str(loc["lng"]))
    except Exception as e:
        print(f"Geocode error for {address}: {e}")

    return Coordinates("Not found", "Not found")
