# -*- coding: utf-8 -*-
"""
Agent工具集
实现专业化农事工具
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from src.models import (
    CropType, Location, FieldInfo,
    AgriculturalWeatherData, OperationRecommendation,
    DisasterWarning, DiseaseRisk
)
from src.data.weather_processor import WeatherProcessor
from src.core.rule_engine import RuleEngine


class WeatherQueryTool:
    """气象查询工具"""
    
    def __init__(self, weather_processor: WeatherProcessor):
        self.processor = weather_processor
        self.name = "weather_query"
        self.description = "精准查询指定地块、时段的气象原始数据与衍生农业指标"
    
    async def run(
        self,
        location: Location,
        start_time: datetime,
        end_time: datetime,
        granularity: str = "hourly"
    ) -> Dict[str, Any]:
        """
        执行气象查询
        
        Args:
            location: 地理位置信息
            start_time: 开始时间
            end_time: 结束时间
            granularity: 时间粒度
        
        Returns:
            气象数据字典
        """
        weather_data = await self.processor.fetch_weather_data(
            location, start_time, end_time, granularity
        )
        
        return {
            "location": location.dict(),
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "weather_data": [wd.dict() for wd in weather_data],
            "count": len(weather_data)
        }


class CropGrowthCalculatorTool:
    """作物生长计算工具"""
    
    def __init__(self, rule_engine: RuleEngine):
        self.engine = rule_engine
        self.name = "crop_growth_calculator"
        self.description = "结合播种日期、本地化积温参数，实时计算作物当前生育期与未来长势进度"
    
    def run(
        self,
        crop_type: CropType,
        sowing_date: datetime,
        accumulated_temperature: float
    ) -> Dict[str, Any]:
        """
        计算作物生长状态
        
        Args:
            crop_type: 作物类型
            sowing_date: 播种日期
            accumulated_temperature: 累计积温
        
        Returns:
            生长状态字典
        """
        growth_stage, days = self.engine.determine_growth_stage(
            crop_type, sowing_date, accumulated_temperature
        )
        
        progress = min(days / 120 * 100, 100)
        
        return {
            "crop_type": crop_type.value,
            "current_stage": growth_stage.value,
            "days_after_sowing": days,
            "accumulated_temperature": accumulated_temperature,
            "growth_progress": f"{progress:.1f}%",
            "estimated_maturity_days": max(120 - days, 0)
        }


class FarmOperationJudgeTool:
    """农事操作判定工具"""
    
    def __init__(self, rule_engine: RuleEngine):
        self.engine = rule_engine
        self.name = "farm_operation_judge"
        self.description = "农事操作适宜度判定，输入操作类型与气象数据，输出适宜等级、操作建议及核心依据"
    
    def run(
        self,
        operation_type: str,
        weather_data: AgriculturalWeatherData,
        crop_type: Optional[CropType] = None,
        soil_moisture: Optional[float] = None,
        growth_stage: Optional[str] = None,
        location: Optional[Location] = None
    ) -> Dict[str, Any]:
        """
        判定农事操作适宜度
        
        Args:
            operation_type: 操作类型
            weather_data: 农业气象数据
            crop_type: 作物类型
            soil_moisture: 土壤墒情
            growth_stage: 生长阶段
            location: 地理位置信息
        
        Returns:
            操作建议字典
        """
        if operation_type == "播种":
            if crop_type and location:
                recommendation = self.engine.judge_sowing_window(
                    weather_data, crop_type, location
                )
            else:
                return {"error": "播种判定需要作物类型和位置信息"}
        elif operation_type == "灌溉":
            if crop_type and soil_moisture and growth_stage:
                recommendation = self.engine.judge_irrigation_timing(
                    weather_data, soil_moisture, crop_type, growth_stage
                )
            else:
                return {"error": "灌溉判定需要作物类型、土壤墒情和生长阶段"}
        elif operation_type == "植保":
            recommendation = self.engine.judge_pest_control_timing(weather_data)
        else:
            return {"error": f"不支持的操作类型: {operation_type}"}
        
        return {
            "operation_type": recommendation.operation_type.value,
            "suitability_level": recommendation.suitability_level.value,
            "optimal_time": recommendation.optimal_time.isoformat(),
            "time_window": [
                recommendation.time_window[0].isoformat(),
                recommendation.time_window[1].isoformat()
            ],
            "operation_details": recommendation.operation_details,
            "precautions": recommendation.precautions,
            "risk_warnings": recommendation.risk_warnings,
            "evidence": recommendation.evidence
        }


class DisasterRiskAssessTool:
    """灾害风险评估工具"""
    
    def __init__(self, rule_engine: RuleEngine):
        self.engine = rule_engine
        self.name = "disaster_risk_assess"
        self.description = "基于本地化灾害阈值，完成气象灾害风险分级评估与应对方案匹配"
    
    def run(
        self,
        weather_data: AgriculturalWeatherData,
        crop_type: Optional[CropType] = None,
        growth_stage: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        评估灾害风险
        
        Args:
            weather_data: 农业气象数据
            crop_type: 作物类型
            growth_stage: 生长阶段
        
        Returns:
            灾害风险评估结果
        """
        disaster_warnings = self.engine.assess_disaster_risk(weather_data)
        
        disease_risks = []
        if crop_type and growth_stage:
            disease_risks = self.engine.assess_disease_risk(
                weather_data, crop_type, growth_stage
            )
        
        return {
            "disaster_warnings": [
                {
                    "disaster_type": w.disaster_type.value,
                    "risk_level": w.risk_level.value,
                    "occur_time": w.occur_time.isoformat(),
                    "duration": w.duration,
                    "intensity": w.intensity,
                    "defense_measures": w.defense_measures,
                    "emergency_actions": w.emergency_actions
                }
                for w in disaster_warnings
            ],
            "disease_risks": [
                {
                    "disease_name": r.disease_name,
                    "risk_level": r.risk_level.value,
                    "occur_probability": r.occur_probability,
                    "optimal_control_window": [
                        r.optimal_control_window[0].isoformat(),
                        r.optimal_control_window[1].isoformat()
                    ],
                    "control_measures": r.control_measures,
                    "prevention_methods": r.prevention_methods
                }
                for r in disease_risks
            ],
            "total_risks": len(disaster_warnings) + len(disease_risks)
        }


class KnowledgeRetrievalTool:
    """知识检索工具"""
    
    def __init__(self, rag_engine):
        self.rag_engine = rag_engine
        self.name = "knowledge_retrieval"
        self.description = "RAG知识库智能检索，调取本地化农技知识、病虫害方案、耕作规范"
    
    async def run(
        self,
        query: str,
        top_k: int = 5,
        region: Optional[str] = None,
        crop_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行知识检索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            region: 区域
            crop_type: 作物类型
        
        Returns:
            检索结果
        """
        enhanced_query = query
        if region:
            enhanced_query = f"{region} {enhanced_query}"
        if crop_type:
            enhanced_query = f"{crop_type} {enhanced_query}"
        
        results = await self.rag_engine.search(enhanced_query, top_k=top_k)
        
        return {
            "query": query,
            "enhanced_query": enhanced_query,
            "results": results,
            "count": len(results)
        }


class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self.tools: Dict[str, Any] = {}
    
    def register(self, tool: Any):
        """注册工具"""
        self.tools[tool.name] = tool
    
    def get(self, name: str) -> Optional[Any]:
        """获取工具"""
        return self.tools.get(name)
    
    def list_tools(self) -> List[Dict[str, str]]:
        """列出所有工具"""
        return [
            {"name": tool.name, "description": tool.description}
            for tool in self.tools.values()
        ]


class FertilizationRecommendTool:
    """施肥窗口期推荐工具"""
    
    def __init__(self, rule_engine: RuleEngine):
        self.engine = rule_engine
        self.name = "fertilization_recommend"
        self.description = "施肥窗口期推荐，规避降雨前施肥，推荐最佳施肥时间"
    
    def run(
        self,
        weather_data: AgriculturalWeatherData,
        fertilizer_type: str = "追肥",
        crop_type: Optional[CropType] = None,
        growth_stage: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        推荐施肥窗口期
        
        Args:
            weather_data: 农业气象数据
            fertilizer_type: 肥料类型（基肥/追肥/叶面肥）
            crop_type: 作物类型
            growth_stage: 生长阶段
        
        Returns:
            施肥建议
        """
        recommendation = self.engine.judge_fertilization_timing(
            weather_data, fertilizer_type, crop_type, growth_stage
        )
        
        return {
            "fertilizer_type": fertilizer_type,
            "suitability_level": recommendation.suitability_level.value,
            "optimal_time": recommendation.optimal_time.isoformat(),
            "time_window": [
                recommendation.time_window[0].isoformat(),
                recommendation.time_window[1].isoformat()
            ],
            "operation_details": recommendation.operation_details,
            "precautions": recommendation.precautions,
            "risk_warnings": recommendation.risk_warnings,
            "evidence": recommendation.evidence
        }


class HarvestTimingTool:
    """收获期预报工具"""
    
    def __init__(self, rule_engine: RuleEngine):
        self.engine = rule_engine
        self.name = "harvest_timing"
        self.description = "最佳收获期预报，结合作物成熟度和天气趋势推荐收获窗口"
    
    def run(
        self,
        weather_data: AgriculturalWeatherData,
        crop_type: CropType,
        maturity_progress: float = 80.0,
        grain_moisture: float = 20.0
    ) -> Dict[str, Any]:
        """
        预报最佳收获期
        
        Args:
            weather_data: 农业气象数据
            crop_type: 作物类型
            maturity_progress: 成熟进度（%）
            grain_moisture: 籽粒含水率（%）
        
        Returns:
            收获建议
        """
        recommendation = self.engine.judge_harvest_timing(
            weather_data, crop_type, maturity_progress, grain_moisture
        )
        
        return {
            "crop_type": crop_type.value,
            "maturity_progress": maturity_progress,
            "grain_moisture": grain_moisture,
            "suitability_level": recommendation.suitability_level.value,
            "optimal_time": recommendation.optimal_time.isoformat(),
            "time_window": [
                recommendation.time_window[0].isoformat(),
                recommendation.time_window[1].isoformat()
            ],
            "operation_details": recommendation.operation_details,
            "precautions": recommendation.precautions,
            "risk_warnings": recommendation.risk_warnings,
            "evidence": recommendation.evidence
        }


class VarietyRecommendTool:
    """品种适配推荐工具"""
    
    def __init__(self, rule_engine: RuleEngine):
        self.engine = rule_engine
        self.name = "variety_recommend"
        self.description = "品种适配建议，基于积温、无霜期智能匹配作物品种"
    
    def run(
        self,
        location: Location,
        crop_type: CropType,
        accumulated_temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        推荐适宜品种
        
        Args:
            location: 地理位置信息
            crop_type: 作物类型
            accumulated_temperature: 区域积温
        
        Returns:
            品种推荐结果
        """
        return self.engine.recommend_variety(
            location, crop_type, accumulated_temperature
        )


class CropRotationTool:
    """茬口衔接规划工具"""
    
    def __init__(self, rule_engine: RuleEngine):
        self.engine = rule_engine
        self.name = "crop_rotation"
        self.description = "茬口衔接规划，多熟制区域茬口时间计算与衔接方案"
    
    def run(
        self,
        location: Location,
        previous_crop: CropType,
        previous_harvest_date: datetime,
        next_crop: CropType
    ) -> Dict[str, Any]:
        """
        规划茬口衔接
        
        Args:
            location: 地理位置信息
            previous_crop: 前茬作物
            previous_harvest_date: 前茬收获日期
            next_crop: 下茬作物
        
        Returns:
            茬口衔接方案
        """
        return self.engine.plan_crop_rotation(
            location, previous_crop, previous_harvest_date, next_crop
        )


class SymptomDiagnosisTool:
    """作物异常症状诊断工具"""
    
    def __init__(self, rule_engine: RuleEngine):
        self.engine = rule_engine
        self.name = "symptom_diagnosis"
        self.description = "作物异常症状诊断，结合气象变化分析诱因并给出处置方案"
    
    def run(
        self,
        symptom_description: str,
        weather_data: AgriculturalWeatherData,
        crop_type: CropType,
        growth_stage: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        诊断作物异常症状
        
        Args:
            symptom_description: 症状描述
            weather_data: 农业气象数据
            crop_type: 作物类型
            growth_stage: 生长阶段
        
        Returns:
            诊断结果
        """
        return self.engine.diagnose_crop_symptom(
            symptom_description, weather_data, crop_type, growth_stage
        )


class StorageRiskTool:
    """仓储气象风险提示工具"""
    
    def __init__(self, rule_engine: RuleEngine):
        self.engine = rule_engine
        self.name = "storage_risk"
        self.description = "仓储气象风险提示，监测仓储环境并给出风险预警"
    
    def run(
        self,
        weather_data: AgriculturalWeatherData,
        storage_type: str = "常温仓储",
        grain_moisture: float = 14.0,
        storage_duration_days: int = 30
    ) -> Dict[str, Any]:
        """
        评估仓储气象风险
        
        Args:
            weather_data: 农业气象数据
            storage_type: 仓储类型
            grain_moisture: 粮食含水率（%）
            storage_duration_days: 已存储天数
        
        Returns:
            仓储风险评估结果
        """
        return self.engine.assess_storage_risk(
            weather_data, storage_type, grain_moisture, storage_duration_days
        )


class VegetablePlantingTool:
    """蔬菜种植工具"""
    
    def __init__(self, rule_engine: RuleEngine):
        self.engine = rule_engine
        self.name = "vegetable_planting"
        self.description = "蔬菜种植决策，根据气象条件判断适宜性和管理要点"
    
    def run(
        self,
        weather_data: AgriculturalWeatherData,
        crop_type: CropType,
        season: str = "春季"
    ) -> Dict[str, Any]:
        """
        蔬菜种植决策
        
        Args:
            weather_data: 农业气象数据
            crop_type: 蔬菜类型
            season: 种植季节
        
        Returns:
            种植建议
        """
        return self.engine.judge_vegetable_planting(
            weather_data, crop_type, season
        )


class FruitTreeManagementTool:
    """果树管理工具"""
    
    def __init__(self, rule_engine: RuleEngine):
        self.engine = rule_engine
        self.name = "fruit_tree_management"
        self.description = "果树管理决策，根据生长阶段和气象条件给出管理建议"
    
    def run(
        self,
        weather_data: AgriculturalWeatherData,
        crop_type: CropType,
        growth_stage: str = "休眠期"
    ) -> Dict[str, Any]:
        """
        果树管理决策
        
        Args:
            weather_data: 农业气象数据
            crop_type: 果树类型
            growth_stage: 生长阶段
        
        Returns:
            管理建议
        """
        return self.engine.judge_fruit_tree_management(
            weather_data, crop_type, growth_stage
        )


class FlowerCareTool:
    """花卉养护工具"""
    
    def __init__(self, rule_engine: RuleEngine):
        self.engine = rule_engine
        self.name = "flower_care"
        self.description = "花卉养护决策，根据季节和气象条件给出养护建议"
    
    def run(
        self,
        weather_data: AgriculturalWeatherData,
        crop_type: CropType,
        season: str = "春季"
    ) -> Dict[str, Any]:
        """
        花卉养护决策
        
        Args:
            weather_data: 农业气象数据
            crop_type: 花卉类型
            season: 季节
        
        Returns:
            养护建议
        """
        return self.engine.judge_flower_care(
            weather_data, crop_type, season
        )


class GreenhouseEnvironmentTool:
    """保护地环境工具"""
    
    def __init__(self, rule_engine: RuleEngine):
        self.engine = rule_engine
        self.name = "greenhouse_environment"
        self.description = "保护地环境评估，监测棚室环境并给出调控建议"
    
    def run(
        self,
        weather_data: AgriculturalWeatherData,
        crop_type: CropType,
        greenhouse_type: str = "塑料大棚"
    ) -> Dict[str, Any]:
        """
        保护地环境评估
        
        Args:
            weather_data: 农业气象数据
            crop_type: 作物类型
            greenhouse_type: 保护地类型
        
        Returns:
            环境评估结果
        """
        return self.engine.assess_greenhouse_environment(
            weather_data, crop_type, greenhouse_type
        )

