# -*- coding: utf-8 -*-
"""农场管理请求/响应模型"""
from typing import List, Optional
from pydantic import BaseModel, Field


class FieldCreate(BaseModel):
    name: str = Field(..., description="地块名称")
    crop: str = Field("玉米", description="作物")
    stage: str = Field("播种期", description="生长阶段")
    area: float = Field(1.0, gt=0, description="面积（亩）")


class FieldItem(BaseModel):
    field_id: str
    name: str
    crop: str
    stage: str
    area: float
    health: int = 100
    water: int = 70
    growth: int = 0
    is_empty: bool = False
    actions: list = []
    created_at: Optional[str] = None
    planted_at: Optional[str] = None
    last_updated: Optional[str] = None


class FieldListResponse(BaseModel):
    fields: list[FieldItem]
    total: int


class FieldActionResponse(BaseModel):
    success: bool
    message: str
    field: Optional[FieldItem] = None


class FarmAlertItem(BaseModel):
    field_name: str
    crop: str
    alerts: list[str]


class FarmAlertsResponse(BaseModel):
    alerts: list[FarmAlertItem]
