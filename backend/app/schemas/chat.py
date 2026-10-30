# -*- coding: utf-8 -*-
"""智能问答请求/响应模型"""
from typing import List, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(..., description="用户问题")
    user_type: str = Field("普通农户", description="用户类型：普通农户/种植大户/农技人员")
    crop_type: str = Field("玉米", description="作物类型：玉米/小麦/水稻/大豆/马铃薯")
    latitude: float = Field(34.75, description="纬度")
    longitude: float = Field(113.65, description="经度")
    province: str = Field("", description="省份")
    city: str = Field("", description="城市")
    district: str = Field("", description="区县")
    user_id: str = Field("api_user", description="用户ID（用于会话记忆）")
    session_id: str = Field("", description="会话ID（空则自动生成）")


class DisasterWarningItem(BaseModel):
    disaster_type: str
    risk_level: str
    occur_time: Optional[str] = None
    duration: Optional[int] = None
    intensity: Optional[str] = None
    defense_measures: List[str] = []
    emergency_actions: List[str] = []


class DiseaseRiskItem(BaseModel):
    disease_name: str
    risk_level: str
    occur_probability: Optional[float] = None
    control_measures: List[str] = []
    prevention_methods: List[str] = []


class ComplianceInfo(BaseModel):
    advice_level: str = ""
    disclaimer: Optional[str] = None
    requires_local_consultation: bool = False
    regulatory_notes: List[str] = []


class UncertaintyInfo(BaseModel):
    level: str = ""
    confidence_score: float = 0.0


class ChatResponse(BaseModel):
    session_id: str = ""
    content: str
    evidence: str = ""
    confidence: float = 0.0
    disaster_warnings: List[DisasterWarningItem] = []
    disease_risks: List[DiseaseRiskItem] = []
    compliance: Optional[ComplianceInfo] = None
    uncertainty: Optional[UncertaintyInfo] = None
    nowcast_alert: Optional[str] = None


class FeedbackRequest(BaseModel):
    message_id: str = Field(..., description="反馈对象ID")
    session_id: str = Field("", description="会话ID")
    rating: str = Field(..., description="采纳: accepted / 不采纳: rejected / 部分: partial")
    reason: str = Field("", description="不采纳原因（可选）")


class FeedbackResponse(BaseModel):
    status: bool
    message: str = ""


class FeedbackStatsResponse(BaseModel):
    total: int = 0
    accepted: int = 0
    rejected: int = 0
    partial: int = 0
    acceptance_rate: float = 0.0
