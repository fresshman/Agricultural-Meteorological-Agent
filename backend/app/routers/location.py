from fastapi import APIRouter, Query

from src.utils.china_regions import (
    find_coordinates,
    get_cities as _get_cities,
    get_districts as _get_districts,
    get_provinces as _get_provinces,
)
from ..schemas.location import (
    CoordinatesRequest, CoordinatesResponse,
    ProvincesResponse, CitiesResponse, DistrictsResponse,
)

router = APIRouter()


@router.post("/coordinates", response_model=CoordinatesResponse)
async def get_coordinates(req: CoordinatesRequest):
    result = find_coordinates(req.province, req.city, req.district)
    if result:
        return CoordinatesResponse(status=True, **result)
    return CoordinatesResponse(
        status=False,
        message="本地数据中未找到该地区，请重新选择省市区",
    )


@router.get("/provinces", response_model=ProvincesResponse)
async def get_provinces():
    return ProvincesResponse(provinces=_get_provinces())


@router.get("/cities", response_model=CitiesResponse)
async def get_cities(province: str = Query(..., description="省份")):
    return CitiesResponse(cities=_get_cities(province))


@router.get("/districts", response_model=DistrictsResponse)
async def get_districts(
    province: str = Query(..., description="省份"),
    city: str = Query(..., description="城市"),
):
    return DistrictsResponse(districts=_get_districts(province, city))
