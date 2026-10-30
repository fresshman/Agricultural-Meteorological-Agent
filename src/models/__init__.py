# -*- coding: utf-8 -*-
"""
核心数据模型
"""
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple, Any
from pydantic import BaseModel, Field
from enum import Enum


class CropType(str, Enum):
    # 大田作物
    CORN = "玉米"
    WHEAT = "小麦"
    RICE = "水稻"
    SOYBEAN = "大豆"
    POTATO = "马铃薯"
    
    # 蔬菜作物
    TOMATO = "番茄"
    CUCUMBER = "黄瓜"
    PEPPER = "辣椒"
    CABBAGE = "白菜"
    SPINACH = "菠菜"
    CARROT = "胡萝卜"
    
    # 果树作物
    APPLE = "苹果"
    PEAR = "梨"
    PEACH = "桃"
    GRAPE = "葡萄"
    CITRUS = "柑橘"
    
    # 花卉作物
    ROSE = "月季"
    CHRYSANTHEMUM = "菊花"
    LILY = "百合"
    ORCHID = "兰花"
    SUCCULENT = "多肉植物"


class GrowthStage(str, Enum):
    SOWING = "播种期"
    SEEDLING = "出苗期"
    TILLERING = "分蘖期"
    JOINTING = "拔节期"
    HEADING = "抽穗期"
    FLOWERING = "开花期"
    FILLING = "灌浆期"
    MATURITY = "成熟期"


class OperationType(str, Enum):
    SOWING = "播种"
    IRRIGATION = "灌溉"
    FERTILIZATION = "施肥"
    PEST_CONTROL = "植保"
    HARVEST = "收获"
    STORAGE = "仓储"


class DisasterType(str, Enum):
    FROST = "霜冻"
    LATE_SPRING_COLD = "倒春寒"
    RAINSTORM = "暴雨"
    CONTINUOUS_RAIN = "连阴雨"
    HEAT_WAVE = "高温热害"
    DRY_HOT_WIND = "干热风"
    STRONG_WIND = "大风"
    TYPHOON = "台风"
    HAIL = "冰雹"
    WATERLOGGING = "内涝"


class RiskLevel(str, Enum):
    LOW = "低风险"
    MEDIUM = "中风险"
    HIGH = "高风险"
    CRITICAL = "极高风险"


class UserType(str, Enum):
    FARMER = "普通农户"
    LARGE_FARMER = "种植大户"
    TECHNICIAN = "农技人员"


class WeatherData(BaseModel):
    timestamp: datetime
    temperature: float
    max_temperature: float
    min_temperature: float
    humidity: float
    precipitation: float
    wind_speed: float
    wind_direction: str
    sunshine_hours: float
    pressure: float
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AgriculturalWeatherData(BaseModel):
    base_weather: WeatherData
    active_accumulated_temperature: float = Field(description="活动积温")
    effective_accumulated_temperature: float = Field(description="有效积温")
    precipitation_anomaly: float = Field(description="降水距平")
    drought_index: Optional[float] = Field(None, description="干旱指数SPI/SPEI")
    irrigation_demand_index: float = Field(description="灌溉需求指数")
    disaster_stress_index: float = Field(description="灾害胁迫指数")
    drying_index: float = Field(description="晾晒指数")


class Location(BaseModel):
    province: str
    city: str
    district: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    agricultural_region: Optional[str] = Field(None, description="农业气候区")


class FieldInfo(BaseModel):
    field_id: str
    location: Location
    area: float = Field(description="地块面积（亩）")
    soil_type: str
    crop_type: CropType
    variety: Optional[str] = None
    sowing_date: Optional[date] = None
    expected_harvest_date: Optional[date] = None
    irrigation_system: Optional[str] = None


class GrowthStatus(BaseModel):
    crop_type: CropType
    current_stage: GrowthStage
    days_after_sowing: int
    accumulated_temperature: float
    growth_progress: float = Field(description="生长进度百分比")
    health_status: str = Field(description="健康状况评估")
    expected_yield: Optional[float] = Field(None, description="预期产量（kg/亩）")


class OperationRecommendation(BaseModel):
    operation_type: OperationType
    suitability_level: RiskLevel
    optimal_time: datetime
    time_window: Tuple[datetime, datetime]
    operation_details: str
    precautions: List[str]
    risk_warnings: List[str]
    evidence: str = Field(description="决策依据")


class DisasterWarning(BaseModel):
    disaster_type: DisasterType
    risk_level: RiskLevel
    occur_time: datetime
    duration: int = Field(description="持续时间（小时）")
    intensity: str
    affected_area: Optional[float] = None
    defense_measures: List[str]
    emergency_actions: List[str]


class DiseaseRisk(BaseModel):
    disease_name: str
    risk_level: RiskLevel
    occur_probability: float = Field(description="发生概率")
    optimal_control_window: Tuple[datetime, datetime]
    control_measures: List[str]
    prevention_methods: List[str]


class UserProfile(BaseModel):
    user_id: str
    user_type: UserType
    name: str
    phone: Optional[str] = None
    fields: List[FieldInfo] = []
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ConversationHistory(BaseModel):
    session_id: str
    user_id: str
    messages: List[Dict[str, str]] = []
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AgentResponse(BaseModel):
    content: str
    operation_recommendations: List[OperationRecommendation] = []
    disaster_warnings: List[DisasterWarning] = []
    disease_risks: List[DiseaseRisk] = []
    weather_data: Optional[AgriculturalWeatherData] = None
    evidence: str = ""
    confidence: float = Field(description="置信度", ge=0, le=1)


# ==================== 新增数据模型 ====================

# 一、气象风险预警相关

class OperationWindow(str, Enum):
    SOWING = "播种"
    TRANSPLANTING = "移栽"
    POLLINATION = "授粉"
    SPRAYING = "喷药"
    FERTILIZING = "追肥"
    HARVESTING = "采收"
    IRRIGATION = "灌溉"


class WeatherSuitabilityScore(BaseModel):
    operation_type: OperationWindow
    suitability_score: float = Field(description="适宜度评分(0-100)")
    risk_level: RiskLevel
    optimal_dates: List[date] = Field(description="最佳作业日期")
    optimal_periods: List[str] = Field(description="最佳时段，如['10月07日 上午', '10月07日 下午']")
    unsuitable_reasons: List[str] = Field(description="不适宜原因")
    weather_forecast: str = Field(description="天气预报摘要")
    confidence: float = Field(description="置信度", ge=0, le=1)


class PestDiseaseType(str, Enum):
    DOWNY_MILDEW = "霜霉病"
    POWDERY_MILDEW = "白粉病"
    RUST = "锈病"
    RICE_BLAST = "稻瘟病"
    SHEATH_BLIGHT = "纹枯病"
    BACTERIAL_LEAF_BLIGHT = "白叶枯病"
    EAR_BLIGHT = "穗枯病"
    ROOT_ROT = "根腐病"
    APHID = "蚜虫"
    RED_SPIDER = "红蜘蛛"
    ARMYWORM = "粘虫"
    BORER = "螟虫"


class PestDiseaseRisk(BaseModel):
    pest_disease_type: PestDiseaseType
    risk_level: RiskLevel
    occur_probability: float = Field(description="发生概率(0-1)")
    trigger_conditions: Dict[str, Any] = Field(description="触发条件(温度、湿度、结露时长等)")
    risk_period: Tuple[datetime, datetime] = Field(description="高风险时段")
    prevention_measures: List[str] = Field(description="预防措施")
    control_measures: List[str] = Field(description="防治措施")
    chemical_recommendations: List[str] = Field(description="化学防治推荐")
    confidence: float = Field(description="置信度", ge=0, le=1)


# 二、农事周期规划相关

class CropCalendarEvent(BaseModel):
    event_id: str
    event_name: str
    event_type: str = Field(description="事件类型：播种、施肥、灌溉、植保、收获等")
    planned_date: date
    adjusted_date: Optional[date] = Field(None, description="气象调整后的日期")
    adjustment_reason: Optional[str] = Field(None, description="调整原因")
    is_completed: bool = False
    actual_date: Optional[date] = None
    notes: Optional[str] = None


class CropCalendar(BaseModel):
    calendar_id: str
    crop_type: CropType
    variety: Optional[str] = None
    sowing_date: date
    expected_harvest_date: date
    location: Location
    events: List[CropCalendarEvent] = []
    growth_stages: Dict[str, date] = Field(description="各生长阶段预计日期")
    weather_adjustments: List[Dict[str, Any]] = Field(description="气象调整记录")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class SowingWindowRecommendation(BaseModel):
    crop_type: CropType
    target_harvest_date: date
    recommended_windows: List[Tuple[date, date]] = Field(description="推荐播种窗口")
    optimal_window: Tuple[date, date] = Field(description="最优播种窗口")
    risk_assessment: Dict[str, str] = Field(description="各窗口风险评估")
    historical_weather_analysis: str = Field(description="历史气象分析")
    market_consideration: Optional[str] = Field(None, description="市场行情考虑")
    confidence: float = Field(description="置信度", ge=0, le=1)


class WaterFertilizerRecommendation(BaseModel):
    crop_type: CropType
    growth_stage: GrowthStage
    irrigation_recommendation: str
    irrigation_amount: Optional[float] = Field(None, description="灌溉量(立方米/亩)")
    irrigation_timing: str = Field(description="灌溉时机")
    fertilizer_recommendation: str
    fertilizer_type: Optional[str] = None
    fertilizer_amount: Optional[float] = Field(None, description="施肥量(kg/亩)")
    fertilizer_timing: str = Field(description="施肥时机")
    weather_consideration: str = Field(description="气象因素考虑")
    precautions: List[str] = Field(description="注意事项")


# 三、田间数据闭环相关

class RecordType(str, Enum):
    IRRIGATION = "灌溉"
    FERTILIZATION = "施肥"
    PEST_CONTROL = "植保"
    PRUNING = "修剪"
    HARVEST = "收获"
    DISEASE_OCCURRENCE = "病害发生"
    PEST_OCCURRENCE = "虫害发生"
    WEATHER_EVENT = "气象事件"
    OTHER = "其他"


class FieldRecord(BaseModel):
    record_id: str
    field_id: str
    record_type: RecordType
    record_date: date
    operation_details: str
    inputs_used: Optional[Dict[str, float]] = Field(None, description="投入品及用量")
    cost: Optional[float] = Field(None, description="成本(元)")
    weather_condition: Optional[str] = None
    effect_evaluation: Optional[str] = None
    photos: List[str] = Field(default_factory=list, description="照片路径")
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)


class SensorType(str, Enum):
    SOIL_TEMPERATURE = "土壤温度"
    SOIL_MOISTURE = "土壤湿度"
    AIR_TEMPERATURE = "空气温度"
    AIR_HUMIDITY = "空气湿度"
    LIGHT_INTENSITY = "光照强度"
    CO2_CONCENTRATION = "CO2浓度"
    WIND_SPEED = "风速"
    RAINFALL = "降雨量"


class SensorData(BaseModel):
    sensor_id: str
    sensor_type: SensorType
    field_id: str
    value: float
    unit: str
    timestamp: datetime
    location_description: Optional[str] = None
    is_anomaly: bool = False
    anomaly_reason: Optional[str] = None


# 四、设施农业相关

class FacilityType(str, Enum):
    OPEN_FIELD = "露天"
    PLASTIC_TUNNEL = "塑料大棚"
    GLASSHOUSE = "玻璃温室"
    SOLAR_GREENHOUSE = "日光温室"
    MULTI_SPAN_GREENHOUSE = "连栋温室"
    NET_HOUSE = "防虫网室"


class GreenhouseEnvironment(BaseModel):
    facility_id: str
    facility_type: FacilityType
    field_id: str
    indoor_temperature: float
    indoor_humidity: float
    indoor_light: Optional[float] = None
    indoor_co2: Optional[float] = None
    outdoor_temperature: float
    outdoor_humidity: float
    wind_speed: float
    is_daytime: bool
    timestamp: datetime


class GreenhouseControlAdvice(BaseModel):
    facility_id: str
    ventilation_needed: bool = Field(description="是否需要通风")
    ventilation_timing: Optional[str] = Field(None, description="通风时机")
    shading_needed: bool = Field(description="是否需要遮阳")
    shading_timing: Optional[str] = Field(None, description="遮阳时机")
    heating_needed: bool = Field(description="是否需要保温")
    heating_timing: Optional[str] = Field(None, description="保温时机")
    dehumidification_needed: bool = Field(description="是否需要除湿")
    dehumidification_timing: Optional[str] = Field(None, description="除湿时机")
    irrigation_adjustment: Optional[str] = Field(None, description="灌溉调整建议")
    risk_warnings: List[str] = Field(description="风险预警")
    detailed_advice: str = Field(description="详细调控建议")


# 五、产量成本经营相关

class ScenarioType(str, Enum):
    DROUGHT = "持续干旱"
    EXCESSIVE_RAIN = "连续降雨"
    HIGH_TEMPERATURE = "持续高温"
    LOW_TEMPERATURE = "持续低温"
    EARLY_FROST = "早霜"
    LATE_SOWING = "晚播"
    EARLY_SOWING = "早播"


class ScenarioSimulation(BaseModel):
    scenario_id: str
    scenario_type: ScenarioType
    scenario_description: str
    duration_days: int = Field(description="持续天数")
    affected_crops: List[CropType]
    yield_impact: Dict[str, float] = Field(description="产量影响百分比")
    risk_level: RiskLevel
    mitigation_measures: List[str] = Field(description="缓解措施")
    cost_implications: Optional[Dict[str, float]] = Field(None, description="成本影响")
    confidence: float = Field(description="置信度", ge=0, le=1)


class HarvestWindow(BaseModel):
    crop_type: CropType
    variety: Optional[str] = None
    optimal_harvest_start: date
    optimal_harvest_end: date
    quality_factors: Dict[str, str] = Field(description="品质因素(糖分、着色等)")
    weather_considerations: List[str] = Field(description="气象考虑因素")
    risks: List[str] = Field(description="采收风险")
    storage_recommendations: str = Field(description="仓储建议")
    confidence: float = Field(description="置信度", ge=0, le=1)


class CostRiskAssessment(BaseModel):
    field_id: str
    crop_type: CropType
    total_estimated_cost: float = Field(description="总预估成本(元)")
    cost_breakdown: Dict[str, float] = Field(description="成本明细")
    risk_factors: List[str] = Field(description="风险因素")
    potential_loss: float = Field(description="潜在损失(元)")
    insurance_recommendation: Optional[str] = Field(None, description="保险建议")
    mitigation_cost: Optional[float] = Field(None, description="防灾成本")


# 六、工具交互服务相关

class TaskType(str, Enum):
    SPRAYING_REMINDER = "喷药提醒"
    IRRIGATION_REMINDER = "灌溉提醒"
    FROST_WARNING = "霜冻预警"
    HARVEST_REMINDER = "收获提醒"
    FERTILIZATION_REMINDER = "施肥提醒"
    PEST_WARNING = "病虫害预警"


class TaskReminder(BaseModel):
    task_id: str
    task_type: TaskType
    field_id: str
    scheduled_time: datetime
    task_description: str
    priority: RiskLevel
    is_completed: bool = False
    completed_time: Optional[datetime] = None
    weather_condition: Optional[str] = None
    notes: Optional[str] = None


class ImageRecognitionResult(BaseModel):
    image_id: str
    recognition_type: str = Field(description="识别类型：病害、虫害、草害")
    detected_object: str = Field(description="检测对象")
    confidence: float = Field(description="置信度", ge=0, le=1)
    severity: Optional[str] = Field(None, description="严重程度")
    weather_correlation: Optional[str] = Field(None, description="气象相关性分析")
    control_recommendation: str = Field(description="防治建议")
    chemical_options: List[str] = Field(description="化学防治选项")
    prevention_measures: List[str] = Field(description="预防措施")


class HistoricalReview(BaseModel):
    review_id: str
    field_id: str
    review_period: Tuple[date, date]
    review_type: str = Field(description="复盘类型：季度、生长季、年度")
    weather_summary: str = Field(description="气象总结")
    weather_anomalies: List[str] = Field(description="气象异常点")
    operation_summary: str = Field(description="农事总结")
    successful_operations: List[str] = Field(description="成功操作")
    failed_operations: List[str] = Field(description="失败操作")
    lessons_learned: List[str] = Field(description="经验教训")
    recommendations: List[str] = Field(description="未来建议")
    created_at: datetime = Field(default_factory=datetime.now)


# 七、合规与边界相关

class AdviceLevel(str, Enum):
    REFERENCE = "参考建议"
    PROFESSIONAL = "专业建议"
    HIGH_RISK = "高危操作"
    REGULATED = "法规限制"


class UncertaintyLevel(str, Enum):
    HIGH_CONFIDENCE = "高置信度(1-3天)"
    MEDIUM_CONFIDENCE = "中等置信度(4-7天)"
    LOW_CONFIDENCE = "低置信度(8-15天)"
    VERY_LOW_CONFIDENCE = "极低置信度(>15天)"


class AdviceClassification(BaseModel):
    advice_id: str
    advice_level: AdviceLevel
    content: str
    uncertainty: UncertaintyLevel
    confidence_score: float = Field(description="置信度评分", ge=0, le=1)
    disclaimer: Optional[str] = Field(None, description="免责声明")
    requires_local_consultation: bool = Field(description="是否需要咨询本地农技员")
    regulatory_notes: Optional[List[str]] = Field(None, description="法规注意事项")
    valid_period: Optional[Tuple[date, date]] = Field(None, description="有效期间")


# 扩展FieldInfo，添加设施类型
class FieldInfoExtended(FieldInfo):
    facility_type: Optional[FacilityType] = Field(None, description="设施类型")
    sensors: List[str] = Field(default_factory=list, description="传感器ID列表")
    records: List[str] = Field(default_factory=list, description="农事记录ID列表")

