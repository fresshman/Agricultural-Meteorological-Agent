# -*- coding: utf-8 -*-
"""地理编码请求/响应模型"""
from typing import Optional
from pydantic import BaseModel, Field


class CoordinatesRequest(BaseModel):
    province: str = Field(..., description="省份")
    city: str = Field("", description="城市")
    district: str = Field("", description="区县")


class CoordinatesResponse(BaseModel):
    status: bool
    latitude: float = 34.75
    longitude: float = 113.65
    formatted_address: str = ""
    message: str = ""


class ProvincesResponse(BaseModel):
    provinces: list[str]


class CitiesResponse(BaseModel):
    cities: list[str]


class DistrictsResponse(BaseModel):
    districts: list[str]
