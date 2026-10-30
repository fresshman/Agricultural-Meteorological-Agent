# -*- coding: utf-8 -*-
"""地理编码路由：高德 API + 中国行政区划"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from ..deps import get_amap
from ..schemas.location import (
    CoordinatesRequest, CoordinatesResponse,
    ProvincesResponse, CitiesResponse, DistrictsResponse,
)

router = APIRouter()
logger = logging.getLogger("agri-backend.location")


@router.post("/coordinates", response_model=CoordinatesResponse)
async def get_coordinates(req: CoordinatesRequest, amap=Depends(get_amap)):
    """地址转经纬度（高德地理编码）"""
    if not amap:
        return CoordinatesResponse(
            status=False,
            latitude=34.75, longitude=113.65,
            formatted_address=f"{req.province}{req.city}{req.district}",
            message="高德 API 未配置，返回默认坐标",
        )

    address = req.province + req.city + req.district
    result = amap.get_coordinates_by_address(address)

    if result.get("status"):
        return CoordinatesResponse(
            status=True,
            latitude=result.get("latitude", 34.75),
            longitude=result.get("longitude", 113.65),
            formatted_address=result.get("formatted_address", address),
        )
    return CoordinatesResponse(
        status=False,
        message=result.get("message", "获取失败"),
    )


@router.get("/provinces", response_model=ProvincesResponse)
async def get_provinces():
    """获取省份列表"""
    from src.utils.china_regions import get_provinces as _get_provinces
    return ProvincesResponse(provinces=_get_provinces())


@router.get("/cities", response_model=CitiesResponse)
async def get_cities(province: str = Query(..., description="省份")):
    """获取城市列表"""
    from src.utils.china_regions import get_cities as _get_cities
    return CitiesResponse(cities=_get_cities(province))


@router.get("/districts", response_model=DistrictsResponse)
async def get_districts(
    province: str = Query(..., description="省份"),
    city: str = Query(..., description="城市"),
    amap=Depends(get_amap),
):
    """获取区县列表（优先高德 API，降级静态数据）"""
    if amap:
        try:
            keywords = city if city else province
            municipalities = ["北京市", "天津市", "上海市", "重庆市"]
            is_muni = keywords in municipalities
            subdistrict_level = 2 if is_muni else 1

            result = amap.get_districts(keywords=keywords, subdistrict=subdistrict_level)
            if result.get("status") and result.get("districts"):
                districts_data = result["districts"]
                district_names = []
                if districts_data:
                    first_district = districts_data[0]
                    sub_districts = first_district.get("districts", [])
                    if is_muni and sub_districts:
                        first_sub = sub_districts[0]
                        district_names = [d.get("name", "") for d in first_sub.get("districts", []) if d.get("name")]
                    else:
                        district_names = [d.get("name", "") for d in sub_districts if d.get("name")]
                if district_names:
                    return DistrictsResponse(districts=district_names)
        except Exception as e:
            logger.warning(f"高德获取区县失败，降级静态数据: {e}")

    from src.utils.china_regions import get_districts as _get_districts
    return DistrictsResponse(districts=_get_districts(province, city))
