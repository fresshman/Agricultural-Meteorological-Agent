import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def _region_index() -> dict:
    data_path = Path(__file__).with_name("china_regions.json")
    data = json.loads(data_path.read_text(encoding="utf-8"))
    return {province["name"]: province for province in data["regions"]}


def get_provinces() -> list:
    return list(_region_index())


def get_cities(province: str) -> list:
    province_data = _region_index().get(province)
    if not province_data:
        return []
    return [city["name"] for city in province_data["cities"]]


def get_districts(province: str, city: str) -> list:
    province_data = _region_index().get(province)
    if not province_data:
        return []
    city_data = next((item for item in province_data["cities"] if item["name"] == city), None)
    if not city_data:
        return []
    return [district["name"] for district in city_data["districts"]]


def find_coordinates(province: str, city: str = "", district: str = "") -> dict | None:
    selected = _region_index().get(province)
    if not selected or (district and not city):
        return None

    if city:
        selected = next((item for item in selected["cities"] if item["name"] == city), None)
        if not selected:
            return None

    if district:
        selected = next((item for item in selected["districts"] if item["name"] == district), None)
        if not selected:
            return None

    center = selected.get("center")
    if not center:
        return None

    names = [province]
    for name in (city, district):
        if name and name != names[-1]:
            names.append(name)

    return {
        "longitude": center[0],
        "latitude": center[1],
        "formatted_address": "".join(names),
    }
