import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen


NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"


def reverse_geocode(latitude: float, longitude: float, timeout_seconds: int = 8) -> dict:
    query = urlencode(
        {
            "format": "jsonv2",
            "lat": f"{latitude:.6f}",
            "lon": f"{longitude:.6f}",
            "addressdetails": 1,
            "accept-language": "zh-CN,zh",
        }
    )
    url = f"{NOMINATIM_REVERSE_URL}?{query}"

    req = Request(
        url,
        headers={
            "User-Agent": "local-flavor/1.0 (reverse geocode)",
        },
    )
    with urlopen(req, timeout=timeout_seconds) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    address = payload.get("address") or {}
    province = (
        address.get("state")
        or address.get("province")
        or address.get("region")
        or ""
    )
    city = (
        address.get("city")
        or address.get("town")
        or address.get("county")
        or address.get("state_district")
        or ""
    )

    province = str(province).strip()
    city = str(city).strip()
    if not province and city:
        province = city
    if not city and province:
        city = province
    return {"province": province, "city": city}
