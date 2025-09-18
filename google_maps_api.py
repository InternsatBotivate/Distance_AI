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
    Geocode an address using Google Maps Geocoding API.
    Returns a Coordinates object with .latitude and .longitude.
    If not found, both are set to "Not found".
    """
    if api_key is None:
        api_key = os.getenv("GOOGLE_MAPS_API_KEY")

    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": api_key}

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") == "OK":
            loc = data["results"][0]["geometry"]["location"]
            return Coordinates(str(loc["lat"]), str(loc["lng"]))
        else:
            print(f"Geocode error: {data.get('status')} - {data.get('error_message')}")
    except Exception as e:
        print(f"Geocode error for {address}: {e}")

    return Coordinates("Not found", "Not found")