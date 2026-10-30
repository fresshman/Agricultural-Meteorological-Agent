# -*- coding: utf-8 -*-
"""预警分析请求/响应模型"""
from typing import List, Optional
from pydantic import BaseModel, Field


class DisasterWarningRequest(BaseModel):
    crop_type: str = Field("玉米", description="作物类型")
    growth_stage: Optional[str] = Field(None, description="生长阶段")
    latitude: float = Field(34.75)
    longitude: float = Field(113.65)
    province: str = Field("")
    city: str = Field("")


class PestWarningRequest(BaseModel):
    crop_type: str = Field("玉米")
    growth_stage: Optional[str] = None
    latitude: float = Field(34.75)
    longitude: float = Field(113.65)
    province: str = Field("")
    city: str = Field("")


class SuitabilityRequest(BaseModel):
    operation_type: str = Field("播种", description="农事操作：播种/移栽/授粉/喷药/追肥/采收/灌溉")
    crop_type: Optional[str] = None
    latitude: float = Field(34.75)
    longitude: float = Field(113.65)
    province: str = Field("")
    city: str = Field("")


class WarningItem(BaseModel):
    type: str
    risk_level: str
    details: dict = {}


class WarningResponse(BaseModel):
    status: bool
    message: str = ""
    warnings: list[WarningItem] = []
    raw: Optional[dict] = None
