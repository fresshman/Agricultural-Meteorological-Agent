# -*- coding: utf-8 -*-
"""
设施农业专项工具集
实现温室调控建议、大棚环境分析
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from src.models import (
    GreenhouseEnvironment, GreenhouseControlAdvice,
    FacilityType, RiskLevel
)


class GreenhouseControlTool:
    """温室大棚环境调控工具"""
    
    def __init__(self):
        self.name = "greenhouse_control"
        self.description = "温室大棚环境调控建议"
        
        self.optimal_ranges = {
            "temperature": {"day": (20, 28), "night": (12, 18)},
            "humidity": {"day": (60, 80), "night": (70, 90)},
            "light": {"min": 10000, "max": 50000},
            "co2": {"min": 400, "max": 1200}
        }
        
        self.control_thresholds = {
            "ventilation_temp_high": 28,
            "ventilation_humidity_high": 85,
            "shading_temp_high": 32,
            "shading_light_high": 45000,
            "heating_temp_low": 10,
            "dehumidification_humidity_high": 90
        }
    
    def analyze_environment(
        self,
        environment: GreenhouseEnvironment
    ) -> GreenhouseControlAdvice:
        """
        分析温室环境并给出调控建议
        
        Args:
            environment: 温室环境数据
        
        Returns:
            调控建议
        """
        ventilation_needed = False
        ventilation_timing = None
        shading_needed = False
        shading_timing = None
        heating_needed = False
        heating_timing = None
        dehumidification_needed = False
        dehumidification_timing = None
        irrigation_adjustment = None
        risk_warnings = []
        
        temp_range = self.optimal_ranges["temperature"]["day"] if environment.is_daytime else self.optimal_ranges["temperature"]["night"]
        humidity_range = self.optimal_ranges["humidity"]["day"] if environment.is_daytime else self.optimal_ranges["humidity"]["night"]
        
        if environment.indoor_temperature > self.control_thresholds["ventilation_temp_high"]:
            ventilation_needed = True
            ventilation_timing = "立即通风降温"
            risk_warnings.append(f"室内温度{environment.indoor_temperature}°C过高，需通风降温")
        
        if environment.indoor_humidity > self.control_thresholds["ventilation_humidity_high"]:
            ventilation_needed = True
            if not ventilation_timing:
                ventilation_timing = "通风排湿"
            risk_warnings.append(f"室内湿度{environment.indoor_humidity}%过高，易引发病害")
        
        if environment.indoor_temperature > self.control_thresholds["shading_temp_high"]:
            shading_needed = True
            shading_timing = "中午高温时段遮阳"
            risk_warnings.append("高温强光，需遮阳防护")
        
        if environment.indoor_light and environment.indoor_light > self.control_thresholds["shading_light_high"]:
            shading_needed = True
            if not shading_timing:
                shading_timing = "光照过强时遮阳"
        
        if environment.indoor_temperature < self.control_thresholds["heating_temp_low"]:
            heating_needed = True
            heating_timing = "夜间保温或加温"
            risk_warnings.append(f"室内温度{environment.indoor_temperature}°C过低，需保温")
        
        if environment.indoor_humidity > self.control_thresholds["dehumidification_humidity_high"]:
            dehumidification_needed = True
            dehumidification_timing = "通风除湿或使用除湿设备"
            risk_warnings.append("高湿结露风险，需除湿")
        
        if environment.indoor_temperature > 30 and environment.indoor_humidity < 50:
            irrigation_adjustment = "高温低湿，建议增加灌溉频次"
        elif environment.indoor_humidity > 85:
            irrigation_adjustment = "高湿环境，减少灌溉频次"
        
        detailed_advice = self._build_detailed_advice(
            ventilation_needed, ventilation_timing,
            shading_needed, shading_timing,
            heating_needed, heating_timing,
            dehumidification_needed, dehumidification_timing,
            irrigation_adjustment
        )
        
        return GreenhouseControlAdvice(
            facility_id=environment.facility_id,
            ventilation_needed=ventilation_needed,
            ventilation_timing=ventilation_timing,
            shading_needed=shading_needed,
            shading_timing=shading_timing,
            heating_needed=heating_needed,
            heating_timing=heating_timing,
            dehumidification_needed=dehumidification_needed,
            dehumidification_timing=dehumidification_timing,
            irrigation_adjustment=irrigation_adjustment,
            risk_warnings=risk_warnings,
            detailed_advice=detailed_advice
        )
    
    def _build_detailed_advice(
        self,
        ventilation_needed: bool,
        ventilation_timing: Optional[str],
        shading_needed: bool,
        shading_timing: Optional[str],
        heating_needed: bool,
        heating_timing: Optional[str],
        dehumidification_needed: bool,
        dehumidification_timing: Optional[str],
        irrigation_adjustment: Optional[str]
    ) -> str:
        """构建详细调控建议"""
        advice_parts = []
        
        if ventilation_needed:
            advice_parts.append(f"通风管理：{ventilation_timing}")
        
        if shading_needed:
            advice_parts.append(f"遮阳管理：{shading_timing}")
        
        if heating_needed:
            advice_parts.append(f"保温管理：{heating_timing}")
        
        if dehumidification_needed:
            advice_parts.append(f"除湿管理：{dehumidification_timing}")
        
        if irrigation_adjustment:
            advice_parts.append(f"灌溉调整：{irrigation_adjustment}")
        
        if not advice_parts:
            advice_parts.append("当前环境参数适宜，维持现状即可")
        
        return "；".join(advice_parts)
    
    def get_daily_management_schedule(
        self,
        environment: GreenhouseEnvironment
    ) -> Dict[str, List[str]]:
        """
        获取日管理计划
        
        Args:
            environment: 温室环境数据
        
        Returns:
            分时段管理计划
        """
        schedule = {
            "早晨(6:00-9:00)": [],
            "上午(9:00-12:00)": [],
            "中午(12:00-14:00)": [],
            "下午(14:00-18:00)": [],
            "傍晚(18:00-20:00)": [],
            "夜间(20:00-次日6:00)": []
        }
        
        if environment.indoor_humidity > 80:
            schedule["早晨(6:00-9:00)"].append("开风口通风排湿")
        
        if environment.indoor_temperature > 25:
            schedule["上午(9:00-12:00)"].append("逐步加大通风")
        
        if environment.indoor_temperature > 30:
            schedule["中午(12:00-14:00)"].append("覆盖遮阳网")
            schedule["中午(12:00-14:00)"].append("加大通风降温")
        
        schedule["下午(14:00-18:00)"].append("逐步减小通风")
        
        if environment.indoor_temperature < 15:
            schedule["傍晚(18:00-20:00)"].append("关闭风口保温")
            schedule["夜间(20:00-次日6:00)"].append("覆盖保温被")
        
        return schedule


class FacilityEnvironmentMonitor:
    """设施环境监测工具"""
    
    def __init__(self):
        self.name = "facility_monitor"
        self.description = "设施农业环境监测"
        
        self.facilities: Dict[str, GreenhouseEnvironment] = {}
    
    def update_environment(
        self,
        facility_id: str,
        facility_type: str,
        field_id: str,
        indoor_temperature: float,
        indoor_humidity: float,
        outdoor_temperature: float,
        outdoor_humidity: float,
        wind_speed: float,
        indoor_light: Optional[float] = None,
        indoor_co2: Optional[float] = None
    ) -> GreenhouseEnvironment:
        """
        更新设施环境数据
        
        Args:
            facility_id: 设施ID
            facility_type: 设施类型
            field_id: 地块ID
            indoor_temperature: 室内温度
            indoor_humidity: 室内湿度
            outdoor_temperature: 室外温度
            outdoor_humidity: 室外湿度
            wind_speed: 风速
            indoor_light: 室内光照
            indoor_co2: 室内CO2浓度
        
        Returns:
            温室环境数据
        """
        now = datetime.now()
        is_daytime = 6 <= now.hour < 18
        
        environment = GreenhouseEnvironment(
            facility_id=facility_id,
            facility_type=FacilityType(facility_type),
            field_id=field_id,
            indoor_temperature=indoor_temperature,
            indoor_humidity=indoor_humidity,
            indoor_light=indoor_light,
            indoor_co2=indoor_co2,
            outdoor_temperature=outdoor_temperature,
            outdoor_humidity=outdoor_humidity,
            wind_speed=wind_speed,
            is_daytime=is_daytime,
            timestamp=now
        )
        
        self.facilities[facility_id] = environment
        
        return environment
    
    def get_environment(self, facility_id: str) -> Optional[GreenhouseEnvironment]:
        """获取设施环境数据"""
        return self.facilities.get(facility_id)
    
    def compare_indoor_outdoor(
        self,
        facility_id: str
    ) -> Dict[str, Any]:
        """
        对比室内外环境
        
        Args:
            facility_id: 设施ID
        
        Returns:
            对比结果
        """
        env = self.facilities.get(facility_id)
        if not env:
            return {"error": "设施不存在"}
        
        temp_diff = env.indoor_temperature - env.outdoor_temperature
        humidity_diff = env.indoor_humidity - env.outdoor_humidity
        
        return {
            "facility_id": facility_id,
            "temperature_difference": f"{temp_diff:+.1f}°C",
            "humidity_difference": f"{humidity_diff:+.1f}%",
            "indoor_advantage": self._assess_indoor_advantage(temp_diff, humidity_diff),
            "recommendation": self._get_comparison_recommendation(temp_diff, humidity_diff)
        }
    
    def _assess_indoor_advantage(
        self,
        temp_diff: float,
        humidity_diff: float
    ) -> str:
        """评估室内优势"""
        if temp_diff > 5 and humidity_diff > 10:
            return "保温保湿效果显著"
        elif temp_diff > 3:
            return "保温效果良好"
        elif humidity_diff > 5:
            return "保湿效果良好"
        else:
            return "室内外差异较小"
    
    def _get_comparison_recommendation(
        self,
        temp_diff: float,
        humidity_diff: float
    ) -> str:
        """获取对比建议"""
        if temp_diff < 3:
            return "保温效果不足，检查设施密闭性"
        elif temp_diff > 10:
            return "室内温度过高，注意通风降温"
        elif humidity_diff > 20:
            return "湿度过高，注意通风排湿"
        else:
            return "设施环境调控合理"

