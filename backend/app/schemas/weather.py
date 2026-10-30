# -*- coding: utf-8 -*-
"""气象数据请求/响应模型"""
from typing import Optional
from pydantic import BaseModel, Field


class WeatherQuery(BaseModel):
    latitude: float = Field(..., description="纬度")
    longitude: float = Field(..., description="经度")
    province: str = Field("", description="省份")
    city: str = Field("", description="城市")
    hours: int = Field(1, ge=1, le=168, description="查询未来小时数")


class WeatherDataItem(BaseModel):
    timestamp: str
    temperature: float
    max_temperature: Optional[float] = None
    min_temperature: Optional[float] = None
    humidity: float
    precipitation: float
    wind_speed: float
    wind_direction: Optional[str] = None
    sunshine_hours: Optional[float] = None
    pressure: Optional[float] = None


class WeatherResponse(BaseModel):
    status: bool
    message: str = ""
    data: list[WeatherDataItem] = []
    summary: Optional[str] = None
    is_mock: bool = False
