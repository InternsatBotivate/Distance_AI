from geopy.geocoders import Nominatim
from typing import List, Dict

geolocator = Nominatim(user_agent="my_geocoder")
results: Dict[str, List[str]] = {}
address = "Ambuja Mall, Raipur"

try:
    location = geolocator.geocode(address)
    if location:
        results[address] = [str(location.latitude), str(location.longitude)]
    else:
        results[address] = ["Not found", "Not found"]
except Exception as e:
    results[address] = ["Error", str(e)]

print(results)