# -*- coding: utf-8 -*-
"""
产量成本经营工具集
实现情景模拟、采收窗口、成本分析
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date, timedelta
from src.models import (
    CropType, RiskLevel, ScenarioType,
    ScenarioSimulation, HarvestWindow, CostRiskAssessment
)


class ScenarioSimulationTool:
    """气象情景模拟工具"""
    
    def __init__(self):
        self.name = "scenario_simulation"
        self.description = "气象情景模拟与决策辅助"
        
        self.scenario_impacts = {
            ScenarioType.DROUGHT: {
                "yield_impact": -15,
                "affected_stages": ["开花期", "灌浆期"],
                "mitigation": ["增加灌溉", "覆盖保墒", "喷施抗旱剂"]
            },
            ScenarioType.EXCESSIVE_RAIN: {
                "yield_impact": -10,
                "affected_stages": ["成熟期", "收获期"],
                "mitigation": ["及时排水", "抢收成熟作物", "防治病害"]
            },
            ScenarioType.HIGH_TEMPERATURE: {
                "yield_impact": -12,
                "affected_stages": ["开花期", "灌浆期"],
                "mitigation": ["增加灌溉", "遮阳降温", "避开高温时段作业"]
            },
            ScenarioType.LOW_TEMPERATURE: {
                "yield_impact": -8,
                "affected_stages": ["苗期", "花期"],
                "mitigation": ["覆盖保温", "熏烟防霜", "推迟播种"]
            },
            ScenarioType.EARLY_FROST: {
                "yield_impact": -20,
                "affected_stages": ["成熟期"],
                "mitigation": ["提前收获", "覆盖防霜", "喷施防冻剂"]
            },
            ScenarioType.LATE_SOWING: {
                "yield_impact": -5,
                "affected_stages": ["全生育期"],
                "mitigation": ["选择早熟品种", "增加密度", "加强管理"]
            }
        }
    
    def simulate_scenario(
        self,
        scenario_type: ScenarioType,
        duration_days: int,
        affected_crops: List[CropType],
        severity: str = "中等"
    ) -> ScenarioSimulation:
        """
        模拟气象情景
        
        Args:
            scenario_type: 情景类型
            duration_days: 持续天数
            affected_crops: 受影响作物
            severity: 严重程度
        
        Returns:
            情景模拟结果
        """
        scenario_id = f"{scenario_type.value}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        base_impact = self.scenario_impacts[scenario_type]
        
        severity_multiplier = {
            "轻微": 0.5,
            "中等": 1.0,
            "严重": 1.5,
            "极严重": 2.0
        }.get(severity, 1.0)
        
        yield_impact = {}
        for crop in affected_crops:
            impact = base_impact["yield_impact"] * severity_multiplier
            if duration_days > 7:
                impact *= 1.2
            yield_impact[crop.value] = round(impact, 1)
        
        risk_level = RiskLevel.MEDIUM
        if severity in ["严重", "极严重"] or duration_days > 10:
            risk_level = RiskLevel.HIGH
        elif severity == "轻微" and duration_days <= 3:
            risk_level = RiskLevel.LOW
        
        mitigation_measures = base_impact["mitigation"].copy()
        if severity in ["严重", "极严重"]:
            mitigation_measures.append("考虑农业保险理赔")
        
        cost_implications = {
            "额外灌溉成本": duration_days * 5 if scenario_type == ScenarioType.DROUGHT else 0,
            "防灾减灾成本": duration_days * 3,
            "潜在产量损失": sum(abs(v) for v in yield_impact.values()) * 10
        }
        
        return ScenarioSimulation(
            scenario_id=scenario_id,
            scenario_type=scenario_type,
            scenario_description=f"{scenario_type.value}持续{duration_days}天，严重程度{severity}",
            duration_days=duration_days,
            affected_crops=affected_crops,
            yield_impact=yield_impact,
            risk_level=risk_level,
            mitigation_measures=mitigation_measures,
            cost_implications=cost_implications,
            confidence=0.7
        )
    
    def compare_scenarios(
        self,
        scenarios: List[ScenarioSimulation]
    ) -> Dict[str, Any]:
        """
        对比多个情景
        
        Args:
            scenarios: 情景列表
        
        Returns:
            对比结果
        """
        if not scenarios:
            return {"error": "无情景数据"}
        
        comparison = {
            "scenarios": [],
            "best_scenario": None,
            "worst_scenario": None,
            "recommendation": ""
        }
        
        for scenario in scenarios:
            avg_impact = sum(abs(v) for v in scenario.yield_impact.values()) / len(scenario.yield_impact) if scenario.yield_impact else 0
            
            comparison["scenarios"].append({
                "type": scenario.scenario_type.value,
                "avg_yield_impact": f"{avg_impact:.1f}%",
                "risk_level": scenario.risk_level.value,
                "duration": f"{scenario.duration_days}天"
            })
        
        sorted_scenarios = sorted(scenarios, key=lambda s: sum(abs(v) for v in s.yield_impact.values()))
        
        comparison["best_scenario"] = sorted_scenarios[0].scenario_type.value
        comparison["worst_scenario"] = sorted_scenarios[-1].scenario_type.value
        
        comparison["recommendation"] = f"建议优先防范{comparison['worst_scenario']}，采取相应缓解措施"
        
        return comparison


class HarvestWindowTool:
    """采收窗口期工具"""
    
    def __init__(self):
        self.name = "harvest_window"
        self.description = "采收窗口期与品质提示"
        
        self.harvest_conditions = {
            CropType.WHEAT: {
                "optimal_moisture": (12, 14),
                "avoid_rain": True,
                "quality_factors": ["籽粒饱满度", "蛋白质含量"]
            },
            CropType.CORN: {
                "optimal_moisture": (14, 18),
                "avoid_rain": True,
                "quality_factors": ["籽粒含水量", "淀粉含量"]
            },
            CropType.TOMATO: {
                "optimal_temp_range": (15, 25),
                "avoid_rain": True,
                "quality_factors": ["糖分含量", "着色度", "硬度"]
            },
            CropType.GRAPE: {
                "optimal_sugar_content": 18,
                "avoid_rain": True,
                "quality_factors": ["糖分", "酸度", "着色"]
            }
        }
    
    def determine_harvest_window(
        self,
        crop_type: CropType,
        expected_maturity_date: date,
        weather_forecast: List[Dict[str, Any]],
        variety: Optional[str] = None
    ) -> HarvestWindow:
        """
        确定采收窗口期
        
        Args:
            crop_type: 作物类型
            expected_maturity_date: 预期成熟日期
            weather_forecast: 天气预报
            variety: 品种
        
        Returns:
            采收窗口期
        """
        conditions = self.harvest_conditions.get(crop_type, {})
        
        optimal_start = expected_maturity_date - timedelta(days=3)
        optimal_end = expected_maturity_date + timedelta(days=5)
        
        quality_factors = {}
        for factor in conditions.get("quality_factors", ["成熟度"]):
            quality_factors[factor] = "受气象条件影响"
        
        if crop_type == CropType.TOMATO:
            quality_factors["糖分"] = "晴天多则糖分高"
            quality_factors["着色"] = "光照充足着色好"
        elif crop_type == CropType.GRAPE:
            quality_factors["糖分"] = "成熟期晴天多则糖分高"
            quality_factors["着色"] = "昼夜温差大着色好"
        
        weather_considerations = []
        if conditions.get("avoid_rain"):
            weather_considerations.append("避开降雨时段采收")
        
        weather_considerations.append("选择晴朗天气采收")
        weather_considerations.append("避开露水重的早晨")
        
        risks = []
        if conditions.get("avoid_rain"):
            risks.append("雨后采收易腐烂")
        
        risks.append("过晚采收品质下降")
        risks.append("过早采收产量降低")
        
        storage_recommendation = self._get_storage_recommendation(crop_type)
        
        return HarvestWindow(
            crop_type=crop_type,
            variety=variety,
            optimal_harvest_start=optimal_start,
            optimal_harvest_end=optimal_end,
            quality_factors=quality_factors,
            weather_considerations=weather_considerations,
            risks=risks,
            storage_recommendation=storage_recommendation,
            confidence=0.8
        )
    
    def _get_storage_recommendation(self, crop_type: CropType) -> str:
        """获取仓储建议"""
        recommendations = {
            CropType.WHEAT: "收获后及时晾晒，水分降至13%以下入库",
            CropType.CORN: "收获后及时脱水，水分降至14%以下仓储",
            CropType.RICE: "收获后及时晾晒，水分降至13.5%以下入库",
            CropType.TOMATO: "采收后及时预冷，低温运输销售",
            CropType.GRAPE: "采收后低温保鲜，尽快销售或冷藏"
        }
        return recommendations.get(crop_type, "采收后妥善储存")


class CostRiskAssessmentTool:
    """成本风险评估工具"""
    
    def __init__(self):
        self.name = "cost_risk_assessment"
        self.description = "农事成本与风险提示"
        
        self.base_costs = {
            CropType.WHEAT: {"seed": 30, "fertilizer": 150, "pesticide": 50, "irrigation": 40, "labor": 100},
            CropType.CORN: {"seed": 40, "fertilizer": 180, "pesticide": 60, "irrigation": 50, "labor": 120},
            CropType.RICE: {"seed": 35, "fertilizer": 200, "pesticide": 80, "irrigation": 60, "labor": 150}
        }
    
    def assess_cost_risk(
        self,
        field_id: str,
        crop_type: CropType,
        area: float,
        risk_factors: List[str]
    ) -> CostRiskAssessment:
        """
        评估成本与风险
        
        Args:
            field_id: 地块ID
            crop_type: 作物类型
            area: 面积
            risk_factors: 风险因素
        
        Returns:
            成本风险评估
        """
        base_cost = self.base_costs.get(crop_type, {"seed": 30, "fertilizer": 150, "pesticide": 50, "irrigation": 40, "labor": 100})
        
        cost_breakdown = {
            "种子": base_cost["seed"] * area,
            "肥料": base_cost["fertilizer"] * area,
            "农药": base_cost["pesticide"] * area,
            "灌溉": base_cost["irrigation"] * area,
            "人工": base_cost["labor"] * area
        }
        
        total_cost = sum(cost_breakdown.values())
        
        potential_loss = 0
        for factor in risk_factors:
            if "干旱" in factor:
                potential_loss += total_cost * 0.15
            elif "病虫害" in factor:
                potential_loss += total_cost * 0.10
            elif "倒伏" in factor:
                potential_loss += total_cost * 0.20
            elif "冻害" in factor:
                potential_loss += total_cost * 0.25
        
        insurance_recommendation = None
        if potential_loss > total_cost * 0.3:
            insurance_recommendation = "建议购买农业保险，降低灾害损失风险"
        
        mitigation_cost = potential_loss * 0.3 if potential_loss > 0 else 0
        
        return CostRiskAssessment(
            field_id=field_id,
            crop_type=crop_type,
            total_estimated_cost=total_cost,
            cost_breakdown=cost_breakdown,
            risk_factors=risk_factors,
            potential_loss=potential_loss,
            insurance_recommendation=insurance_recommendation,
            mitigation_cost=mitigation_cost
        )

