# -*- coding: utf-8 -*-
"""
农事周期规划工具集
实现生育期日历、播期模拟、水肥推荐
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date, timedelta
from src.models import (
    CropType, GrowthStage, Location,
    CropCalendar, CropCalendarEvent,
    SowingWindowRecommendation, WaterFertilizerRecommendation,
    WeatherData
)


class CropCalendarTool:
    """作物全生育期日历工具"""
    
    def __init__(self):
        self.name = "crop_calendar"
        self.description = "气象自适应作物生育期日历"
        
        self.growth_stages_config = {
            CropType.WHEAT: {
                "total_days": 240,
                "stages": [
                    ("播种期", 0, 7),
                    ("出苗期", 7, 15),
                    ("分蘖期", 15, 60),
                    ("越冬期", 60, 120),
                    ("返青期", 120, 150),
                    ("拔节期", 150, 180),
                    ("抽穗期", 180, 200),
                    ("开花期", 200, 210),
                    ("灌浆期", 210, 230),
                    ("成熟期", 230, 240)
                ]
            },
            CropType.CORN: {
                "total_days": 120,
                "stages": [
                    ("播种期", 0, 7),
                    ("出苗期", 7, 15),
                    ("拔节期", 15, 45),
                    ("抽雄期", 45, 60),
                    ("开花期", 60, 70),
                    ("灌浆期", 70, 100),
                    ("成熟期", 100, 120)
                ]
            },
            CropType.RICE: {
                "total_days": 150,
                "stages": [
                    ("播种期", 0, 7),
                    ("秧苗期", 7, 30),
                    ("移栽期", 30, 35),
                    ("分蘖期", 35, 70),
                    ("拔节期", 70, 90),
                    ("抽穗期", 90, 105),
                    ("开花期", 105, 115),
                    ("灌浆期", 115, 140),
                    ("成熟期", 140, 150)
                ]
            },
            CropType.TOMATO: {
                "total_days": 120,
                "stages": [
                    ("播种期", 0, 7),
                    ("苗期", 7, 35),
                    ("定植期", 35, 40),
                    ("开花期", 40, 60),
                    ("结果期", 60, 100),
                    ("成熟期", 100, 120)
                ]
            }
        }
    
    def generate_calendar(
        self,
        crop_type: CropType,
        sowing_date: date,
        location: Location,
        weather_adjustments: Optional[List[Dict[str, Any]]] = None
    ) -> CropCalendar:
        """
        生成作物生育期日历
        
        Args:
            crop_type: 作物类型
            sowing_date: 播种日期
            location: 地理位置信息
            weather_adjustments: 气象调整记录
        
        Returns:
            作物日历
        """
        config = self.growth_stages_config.get(crop_type, self.growth_stages_config[CropType.CORN])
        
        calendar_id = f"{crop_type.value}_{sowing_date.strftime('%Y%m%d')}_{location.city}"
        
        expected_harvest_date = sowing_date + timedelta(days=config["total_days"])
        
        events = []
        growth_stages = {}
        
        for stage_name, start_day, end_day in config["stages"]:
            start_date = sowing_date + timedelta(days=start_day)
            end_date = sowing_date + timedelta(days=end_day)
            
            adjusted_start = start_date
            adjustment_reason = None
            
            if weather_adjustments:
                for adjustment in weather_adjustments:
                    if adjustment.get("stage") == stage_name:
                        days_adjust = adjustment.get("days_adjust", 0)
                        adjusted_start = start_date + timedelta(days=days_adjust)
                        adjustment_reason = adjustment.get("reason", "")
                        break
            
            event = CropCalendarEvent(
                event_id=f"{calendar_id}_{stage_name}",
                event_name=stage_name,
                event_type=self._get_event_type(stage_name),
                planned_date=start_date,
                adjusted_date=adjusted_start if adjusted_start != start_date else None,
                adjustment_reason=adjustment_reason
            )
            events.append(event)
            
            growth_stages[stage_name] = adjusted_start
        
        return CropCalendar(
            calendar_id=calendar_id,
            crop_type=crop_type,
            sowing_date=sowing_date,
            expected_harvest_date=expected_harvest_date,
            location=location,
            events=events,
            growth_stages=growth_stages,
            weather_adjustments=weather_adjustments or []
        )
    
    def _get_event_type(self, stage_name: str) -> str:
        """根据生长阶段获取事件类型"""
        if "播种" in stage_name or "定植" in stage_name:
            return "播种"
        elif "收获" in stage_name or "成熟" in stage_name:
            return "收获"
        elif "开花" in stage_name or "抽穗" in stage_name:
            return "授粉"
        else:
            return "管理"
    
    def adjust_calendar_by_weather(
        self,
        calendar: CropCalendar,
        weather_forecast: List[WeatherData]
    ) -> CropCalendar:
        """
        根据天气预报调整日历
        
        Args:
            calendar: 原始日历
            weather_forecast: 天气预报数据
        
        Returns:
            调整后的日历
        """
        adjustments = []
        
        for weather in weather_forecast:
            if weather.temperature > 25:
                adjustments.append({
                    "stage": "出苗期",
                    "days_adjust": -2,
                    "reason": "气温偏高，出苗提前"
                })
            elif weather.temperature < 15:
                adjustments.append({
                    "stage": "出苗期",
                    "days_adjust": 3,
                    "reason": "气温偏低，出苗延迟"
                })
        
        if adjustments:
            return self.generate_calendar(
                calendar.crop_type,
                calendar.sowing_date,
                calendar.location,
                adjustments
            )
        
        return calendar


class SowingWindowTool:
    """播期模拟推荐工具"""
    
    def __init__(self):
        self.name = "sowing_window"
        self.description = "基于气象和市场的播期推荐"
        
        self.optimal_sowing_conditions = {
            CropType.WHEAT: {
                "optimal_temp_range": (15, 20),
                "avoid_frost_before": 30,
                "optimal_period": "10月上中旬"
            },
            CropType.CORN: {
                "optimal_temp_range": (12, 25),
                "avoid_frost_after": 0,
                "optimal_period": "4月下旬-5月上旬"
            },
            CropType.RICE: {
                "optimal_temp_range": (15, 25),
                "avoid_frost_after": 0,
                "optimal_period": "4月中下旬"
            }
        }
    
    def recommend_sowing_window(
        self,
        crop_type: CropType,
        target_harvest_date: date,
        location: Location,
        historical_weather: Optional[List[Dict[str, Any]]] = None
    ) -> SowingWindowRecommendation:
        """
        推荐播种窗口
        
        Args:
            crop_type: 作物类型
            target_harvest_date: 目标收获日期
            location: 地理位置
            historical_weather: 历史气象数据
        
        Returns:
            播期推荐结果
        """
        growth_days = self._estimate_growth_days(crop_type)
        
        optimal_sowing_date = target_harvest_date - timedelta(days=growth_days)
        
        windows = []
        for days_offset in [-7, -5, -3, 0, 3, 5, 7]:
            window_start = optimal_sowing_date + timedelta(days=days_offset)
            window_end = window_start + timedelta(days=3)
            windows.append((window_start, window_end))
        
        optimal_window = windows[3]
        
        risk_assessment = {}
        for i, (start, end) in enumerate(windows):
            if i < 3:
                risk_assessment[f"{start}~{end}"] = "早播风险：可能遭遇倒春寒"
            elif i > 4:
                risk_assessment[f"{start}~{end}"] = "晚播风险：生育期缩短，产量降低"
            else:
                risk_assessment[f"{start}~{end}"] = "风险适中：推荐窗口"
        
        historical_analysis = self._analyze_historical_weather(
            crop_type, optimal_sowing_date, historical_weather
        )
        
        return SowingWindowRecommendation(
            crop_type=crop_type,
            target_harvest_date=target_harvest_date,
            recommended_windows=windows,
            optimal_window=optimal_window,
            risk_assessment=risk_assessment,
            historical_weather_analysis=historical_analysis,
            confidence=0.75
        )
    
    def _estimate_growth_days(self, crop_type: CropType) -> int:
        """估算生长天数"""
        growth_days = {
            CropType.WHEAT: 240,
            CropType.CORN: 120,
            CropType.RICE: 150,
            CropType.TOMATO: 120,
            CropType.CUCUMBER: 90
        }
        return growth_days.get(crop_type, 120)
    
    def _analyze_historical_weather(
        self,
        crop_type: CropType,
        sowing_date: date,
        historical_weather: Optional[List[Dict[str, Any]]]
    ) -> str:
        """分析历史气象数据"""
        if not historical_weather:
            return "无历史气象数据，使用默认推荐"
        
        frost_risk = 0
        heat_risk = 0
        
        for weather in historical_weather:
            if weather.get("min_temp", 20) < 0:
                frost_risk += 1
            if weather.get("max_temp", 25) > 35:
                heat_risk += 1
        
        analysis = f"历史数据分析：霜冻风险{frost_risk}次，高温风险{heat_risk}次。"
        
        if frost_risk > 3:
            analysis += "建议适当推迟播期。"
        elif heat_risk > 3:
            analysis += "建议适当提前播期。"
        else:
            analysis += "推荐播期风险适中。"
        
        return analysis


class WaterFertilizerTool:
    """水肥气象动态推荐工具"""
    
    def __init__(self):
        self.name = "water_fertilizer"
        self.description = "基于气象的水肥管理推荐"
        
        self.water_requirements = {
            GrowthStage.SEEDLING: {"irrigation": 20, "frequency": 7},
            GrowthStage.TILLERING: {"irrigation": 30, "frequency": 5},
            GrowthStage.JOINTING: {"irrigation": 40, "frequency": 5},
            GrowthStage.HEADING: {"irrigation": 50, "frequency": 4},
            GrowthStage.FLOWERING: {"irrigation": 45, "frequency": 4},
            GrowthStage.FILLING: {"irrigation": 35, "frequency": 5},
            GrowthStage.MATURITY: {"irrigation": 0, "frequency": 0}
        }
        
        self.fertilizer_requirements = {
            GrowthStage.SEEDLING: {"type": "氮肥", "amount": 5, "timing": "苗期追肥"},
            GrowthStage.TILLERING: {"type": "氮肥", "amount": 10, "timing": "分蘖肥"},
            GrowthStage.JOINTING: {"type": "复合肥", "amount": 15, "timing": "拔节肥"},
            GrowthStage.HEADING: {"type": "钾肥", "amount": 8, "timing": "穗肥"},
            GrowthStage.FILLING: {"type": "叶面肥", "amount": 2, "timing": "灌浆肥"}
        }
    
    def recommend_water_fertilizer(
        self,
        crop_type: CropType,
        growth_stage: GrowthStage,
        weather_forecast: List[WeatherData],
        soil_moisture: Optional[float] = None
    ) -> WaterFertilizerRecommendation:
        """
        推荐水肥管理方案
        
        Args:
            crop_type: 作物类型
            growth_stage: 生长阶段
            weather_forecast: 天气预报数据
            soil_moisture: 土壤湿度
        
        Returns:
            水肥推荐结果
        """
        water_config = self.water_requirements.get(growth_stage, {"irrigation": 0, "frequency": 0})
        fert_config = self.fertilizer_requirements.get(growth_stage, {"type": "复合肥", "amount": 0, "timing": "适时追肥"})
        
        total_precip = sum(w.precipitation for w in weather_forecast)
        avg_temp = sum(w.temperature for w in weather_forecast) / len(weather_forecast) if weather_forecast else 25
        
        irrigation_amount = water_config["irrigation"]
        irrigation_timing = f"每{water_config['frequency']}天一次"
        
        if total_precip > 20:
            irrigation_amount = max(irrigation_amount - 15, 0)
            irrigation_timing = "近期有降雨，减少灌溉"
        elif avg_temp > 30:
            irrigation_amount += 10
            irrigation_timing = "高温天气，增加灌溉"
        
        if soil_moisture and soil_moisture > 80:
            irrigation_amount = 0
            irrigation_timing = "土壤湿度充足，暂不灌溉"
        
        fertilizer_amount = fert_config["amount"]
        fertilizer_timing = fert_config["timing"]
        
        if total_precip > 30:
            fertilizer_timing = "降雨前不宜施肥，雨后追施"
        
        weather_consideration = self._build_weather_consideration(
            total_precip, avg_temp, weather_forecast
        )
        
        precautions = self._get_precautions(growth_stage, total_precip, avg_temp)
        
        return WaterFertilizerRecommendation(
            crop_type=crop_type,
            growth_stage=growth_stage,
            irrigation_recommendation=f"建议灌溉量{irrigation_amount}立方米/亩",
            irrigation_amount=irrigation_amount,
            irrigation_timing=irrigation_timing,
            fertilizer_recommendation=f"建议施用{fert_config['type']}{fertilizer_amount}kg/亩",
            fertilizer_type=fert_config["type"],
            fertilizer_amount=fertilizer_amount,
            fertilizer_timing=fertilizer_timing,
            weather_consideration=weather_consideration,
            precautions=precautions
        )
    
    def _build_weather_consideration(
        self,
        total_precip: float,
        avg_temp: float,
        weather_forecast: List[WeatherData]
    ) -> str:
        """构建气象因素考虑"""
        considerations = []
        
        if total_precip > 20:
            considerations.append(f"未来有{total_precip:.1f}mm降雨")
        
        if avg_temp > 30:
            considerations.append("高温天气蒸发量大")
        elif avg_temp < 15:
            considerations.append("低温天气蒸发量小")
        
        if not considerations:
            considerations.append("气象条件适宜")
        
        return "，".join(considerations)
    
    def _get_precautions(
        self,
        growth_stage: GrowthStage,
        total_precip: float,
        avg_temp: float
    ) -> List[str]:
        """获取注意事项"""
        precautions = []
        
        if total_precip > 30:
            precautions.append("注意排水防涝")
            precautions.append("雨后及时追肥")
        
        if avg_temp > 32:
            precautions.append("避开中午高温时段灌溉")
            precautions.append("早晚灌溉效果更好")
        
        if growth_stage == GrowthStage.FLOWERING:
            precautions.append("花期避免大水漫灌")
        
        if growth_stage == GrowthStage.MATURITY:
            precautions.append("成熟期停止灌溉")
        
        if not precautions:
            precautions.append("按常规管理即可")
        
        return precautions

