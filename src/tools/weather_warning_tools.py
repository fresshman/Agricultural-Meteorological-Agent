# -*- coding: utf-8 -*-
"""
气象风险预警工具集
实现灾害预警、病虫害预测、气象适宜度评分
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date, timedelta
from src.models import (
    DisasterType, RiskLevel, CropType, GrowthStage,
    DisasterWarning, PestDiseaseRisk, WeatherSuitabilityScore,
    OperationWindow, PestDiseaseType, WeatherData
)


class DisasterWarningTool:
    """灾害预警工具"""
    
    def __init__(self):
        self.name = "disaster_warning"
        self.description = "气象灾害预警与应急农事对策"
        
        self.disaster_thresholds = {
            DisasterType.FROST: {
                "min_temp": 0,
                "risk_levels": {
                    RiskLevel.LOW: 0,
                    RiskLevel.MEDIUM: -2,
                    RiskLevel.HIGH: -5,
                    RiskLevel.CRITICAL: -10
                }
            },
            DisasterType.LATE_SPRING_COLD: {
                "min_temp": 5,
                "risk_levels": {
                    RiskLevel.LOW: 5,
                    RiskLevel.MEDIUM: 2,
                    RiskLevel.HIGH: 0,
                    RiskLevel.CRITICAL: -3
                }
            },
            DisasterType.HEAT_WAVE: {
                "max_temp": 35,
                "risk_levels": {
                    RiskLevel.LOW: 35,
                    RiskLevel.MEDIUM: 38,
                    RiskLevel.HIGH: 40,
                    RiskLevel.CRITICAL: 42
                }
            },
            DisasterType.RAINSTORM: {
                "precipitation": 50,
                "risk_levels": {
                    RiskLevel.LOW: 50,
                    RiskLevel.MEDIUM: 80,
                    RiskLevel.HIGH: 100,
                    RiskLevel.CRITICAL: 150
                }
            },
            DisasterType.DRY_HOT_WIND: {
                "max_temp": 30,
                "humidity": 30,
                "wind_speed": 3,
                "risk_levels": {
                    RiskLevel.LOW: 30,
                    RiskLevel.MEDIUM: 32,
                    RiskLevel.HIGH: 35,
                    RiskLevel.CRITICAL: 38
                }
            },
            DisasterType.TYPHOON: {
                "wind_speed": 17.2,
                "risk_levels": {
                    RiskLevel.LOW: 17.2,
                    RiskLevel.MEDIUM: 24.5,
                    RiskLevel.HIGH: 32.7,
                    RiskLevel.CRITICAL: 41.5
                }
            },
            DisasterType.HAIL: {
                "risk_conditions": {
                    "temp_drop": 10,
                    "instability": "high"
                }
            }
        }
        
        self.emergency_actions = {
            DisasterType.FROST: {
                "defense_measures": [
                    "熏烟防霜：在上风口点燃湿柴草产生烟雾",
                    "灌水防霜：霜冻前1-2天灌水增加土壤热容量",
                    "覆盖防霜：用塑料薄膜、草帘等覆盖作物",
                    "喷施防冻剂：喷施磷酸二氢钾等防冻剂"
                ],
                "emergency_actions": [
                    "霜冻后及时喷施叶面肥促进恢复",
                    "清除受冻组织防止病害感染",
                    "加强水肥管理促进生长恢复"
                ]
            },
            DisasterType.LATE_SPRING_COLD: {
                "defense_measures": [
                    "推迟播种或移栽时间",
                    "加强苗期保温措施",
                    "喷施防冻剂增强抗寒能力"
                ],
                "emergency_actions": [
                    "及时补种或补栽",
                    "加强肥水管理促进恢复",
                    "防治冻后病害"
                ]
            },
            DisasterType.HEAT_WAVE: {
                "defense_measures": [
                    "增加灌溉频率降低地温",
                    "覆盖遮阳网减少辐射",
                    "喷施抗旱剂增强抗旱能力"
                ],
                "emergency_actions": [
                    "避开高温时段作业",
                    "及时补充水分防止脱水",
                    "加强病虫害防治"
                ]
            },
            DisasterType.RAINSTORM: {
                "defense_measures": [
                    "及时开沟排涝防止积水",
                    "加固田间设施防止倒伏",
                    "提前抢收成熟作物"
                ],
                "emergency_actions": [
                    "雨后及时排水晾田",
                    "扶正倒伏作物",
                    "喷施杀菌剂防止病害"
                ]
            },
            DisasterType.DRY_HOT_WIND: {
                "defense_measures": [
                    "灌水降温增湿",
                    "喷施磷酸二氢钾增强抗逆性",
                    "叶面喷水降温"
                ],
                "emergency_actions": [
                    "增加灌溉频次",
                    "喷施叶面肥促进灌浆",
                    "适时早收减少损失"
                ]
            },
            DisasterType.TYPHOON: {
                "defense_measures": [
                    "加固大棚等设施",
                    "提前抢收成熟作物",
                    "疏通排水沟渠"
                ],
                "emergency_actions": [
                    "及时排除积水",
                    "扶正倒伏作物",
                    "补施肥料促进恢复"
                ]
            },
            DisasterType.HAIL: {
                "defense_measures": [
                    "覆盖防雹网",
                    "人工消雹作业"
                ],
                "emergency_actions": [
                    "及时喷施杀菌剂防止病害",
                    "追施速效肥促进恢复",
                    "严重受灾地块考虑改种"
                ]
            }
        }
    
    def predict_disaster(
        self,
        weather_forecast: List[WeatherData],
        crop_type: CropType,
        growth_stage: Optional[GrowthStage] = None
    ) -> List[DisasterWarning]:
        """
        预测气象灾害
        
        Args:
            weather_forecast: 天气预报数据列表
            crop_type: 作物类型
            growth_stage: 生长阶段
        
        Returns:
            灾害预警列表
        """
        warnings = []
        
        for weather in weather_forecast:
            if weather.min_temperature <= self.disaster_thresholds[DisasterType.FROST]["min_temp"]:
                risk_level = self._assess_frost_risk(weather.min_temperature)
                warning = DisasterWarning(
                    disaster_type=DisasterType.FROST,
                    risk_level=risk_level,
                    occur_time=weather.timestamp,
                    duration=8,
                    intensity=f"最低温度{weather.min_temperature}°C",
                    defense_measures=self.emergency_actions[DisasterType.FROST]["defense_measures"],
                    emergency_actions=self.emergency_actions[DisasterType.FROST]["emergency_actions"]
                )
                warnings.append(warning)
            
            if weather.max_temperature >= self.disaster_thresholds[DisasterType.HEAT_WAVE]["max_temp"]:
                risk_level = self._assess_heat_risk(weather.max_temperature)
                warning = DisasterWarning(
                    disaster_type=DisasterType.HEAT_WAVE,
                    risk_level=risk_level,
                    occur_time=weather.timestamp,
                    duration=8,
                    intensity=f"最高温度{weather.max_temperature}°C",
                    defense_measures=self.emergency_actions[DisasterType.HEAT_WAVE]["defense_measures"],
                    emergency_actions=self.emergency_actions[DisasterType.HEAT_WAVE]["emergency_actions"]
                )
                warnings.append(warning)
            
            if weather.precipitation >= self.disaster_thresholds[DisasterType.RAINSTORM]["precipitation"]:
                risk_level = self._assess_rainstorm_risk(weather.precipitation)
                warning = DisasterWarning(
                    disaster_type=DisasterType.RAINSTORM,
                    risk_level=risk_level,
                    occur_time=weather.timestamp,
                    duration=24,
                    intensity=f"降水量{weather.precipitation}mm",
                    defense_measures=self.emergency_actions[DisasterType.RAINSTORM]["defense_measures"],
                    emergency_actions=self.emergency_actions[DisasterType.RAINSTORM]["emergency_actions"]
                )
                warnings.append(warning)
            
            if (weather.max_temperature >= self.disaster_thresholds[DisasterType.DRY_HOT_WIND]["max_temp"] and
                weather.humidity <= self.disaster_thresholds[DisasterType.DRY_HOT_WIND]["humidity"] and
                weather.wind_speed >= self.disaster_thresholds[DisasterType.DRY_HOT_WIND]["wind_speed"]):
                warning = DisasterWarning(
                    disaster_type=DisasterType.DRY_HOT_WIND,
                    risk_level=RiskLevel.HIGH,
                    occur_time=weather.timestamp,
                    duration=6,
                    intensity=f"温度{weather.max_temperature}°C，湿度{weather.humidity}%，风速{weather.wind_speed}m/s",
                    defense_measures=self.emergency_actions[DisasterType.DRY_HOT_WIND]["defense_measures"],
                    emergency_actions=self.emergency_actions[DisasterType.DRY_HOT_WIND]["emergency_actions"]
                )
                warnings.append(warning)
        
        return warnings
    
    def _assess_frost_risk(self, min_temp: float) -> RiskLevel:
        """评估霜冻风险等级"""
        if min_temp <= -10:
            return RiskLevel.CRITICAL
        elif min_temp <= -5:
            return RiskLevel.HIGH
        elif min_temp <= -2:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _assess_heat_risk(self, max_temp: float) -> RiskLevel:
        """评估高温风险等级"""
        if max_temp >= 42:
            return RiskLevel.CRITICAL
        elif max_temp >= 40:
            return RiskLevel.HIGH
        elif max_temp >= 38:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _assess_rainstorm_risk(self, precipitation: float) -> RiskLevel:
        """评估暴雨风险等级"""
        if precipitation >= 150:
            return RiskLevel.CRITICAL
        elif precipitation >= 100:
            return RiskLevel.HIGH
        elif precipitation >= 80:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW


class PestDiseasePredictionTool:
    """病虫害气象潜势预测工具"""
    
    def __init__(self):
        self.name = "pest_disease_prediction"
        self.description = "基于气象条件的病虫害发生风险预测"
        
        self.disease_conditions = {
            PestDiseaseType.DOWNY_MILDEW: {
                "optimal_temp_range": (15, 24),
                "optimal_humidity": 85,
                "dew_duration_hours": 8,
                "risk_factors": ["高湿", "结露时间长", "温度适宜"]
            },
            PestDiseaseType.POWDERY_MILDEW: {
                "optimal_temp_range": (20, 28),
                "optimal_humidity": 70,
                "risk_factors": ["中等湿度", "温度适宜", "昼夜温差大"]
            },
            PestDiseaseType.RUST: {
                "optimal_temp_range": (15, 25),
                "optimal_humidity": 80,
                "risk_factors": ["高湿", "温度适宜", "结露"]
            },
            PestDiseaseType.RICE_BLAST: {
                "optimal_temp_range": (25, 28),
                "optimal_humidity": 90,
                "risk_factors": ["高湿", "温度适宜", "氮肥过量"]
            }
        }
        
        self.pest_conditions = {
            PestDiseaseType.APHID: {
                "optimal_temp_range": (16, 25),
                "optimal_humidity_range": (50, 80),
                "risk_factors": ["温度适宜", "湿度适中", "天敌少"]
            },
            PestDiseaseType.RED_SPIDER: {
                "optimal_temp_range": (25, 30),
                "optimal_humidity_range": (35, 55),
                "risk_factors": ["高温", "低湿", "干旱"]
            },
            PestDiseaseType.ARMYWORM: {
                "optimal_temp_range": (20, 30),
                "optimal_humidity_range": (60, 90),
                "risk_factors": ["温度适宜", "高湿", "降雨多"]
            }
        }
    
    def predict_pest_disease_risk(
        self,
        weather_forecast: List[WeatherData],
        crop_type: CropType,
        growth_stage: Optional[GrowthStage] = None
    ) -> List[PestDiseaseRisk]:
        """
        预测病虫害风险
        
        Args:
            weather_forecast: 天气预报数据
            crop_type: 作物类型
            growth_stage: 生长阶段
        
        Returns:
            病虫害风险列表
        """
        risks = []
        
        relevant_diseases = self._get_relevant_diseases(crop_type)
        relevant_pests = self._get_relevant_pests(crop_type)
        
        for disease in relevant_diseases:
            risk = self._assess_disease_risk(disease, weather_forecast, crop_type)
            if risk and risk.occur_probability > 0.3:
                risks.append(risk)
        
        for pest in relevant_pests:
            risk = self._assess_pest_risk(pest, weather_forecast, crop_type)
            if risk and risk.occur_probability > 0.3:
                risks.append(risk)
        
        return sorted(risks, key=lambda x: x.occur_probability, reverse=True)
    
    def _get_relevant_diseases(self, crop_type: CropType) -> List[PestDiseaseType]:
        """获取作物相关病害"""
        disease_mapping = {
            CropType.WHEAT: [PestDiseaseType.RUST, PestDiseaseType.POWDERY_MILDEW],
            CropType.RICE: [PestDiseaseType.RICE_BLAST, PestDiseaseType.SHEATH_BLIGHT],
            CropType.CORN: [PestDiseaseType.DOWNY_MILDEW, PestDiseaseType.RUST],
            CropType.CUCUMBER: [PestDiseaseType.DOWNY_MILDEW, PestDiseaseType.POWDERY_MILDEW],
            CropType.TOMATO: [PestDiseaseType.POWDERY_MILDEW, PestDiseaseType.EAR_BLIGHT],
            CropType.GRAPE: [PestDiseaseType.DOWNY_MILDEW, PestDiseaseType.POWDERY_MILDEW]
        }
        return disease_mapping.get(crop_type, [PestDiseaseType.DOWNY_MILDEW])
    
    def _get_relevant_pests(self, crop_type: CropType) -> List[PestDiseaseType]:
        """获取作物相关虫害"""
        pest_mapping = {
            CropType.WHEAT: [PestDiseaseType.APHID, PestDiseaseType.ARMYWORM],
            CropType.RICE: [PestDiseaseType.BORER, PestDiseaseType.ARMYWORM],
            CropType.CORN: [PestDiseaseType.BORER, PestDiseaseType.APHID],
            CropType.CUCUMBER: [PestDiseaseType.APHID, PestDiseaseType.RED_SPIDER],
            CropType.TOMATO: [PestDiseaseType.APHID, PestDiseaseType.RED_SPIDER]
        }
        return pest_mapping.get(crop_type, [PestDiseaseType.APHID])
    
    def _assess_disease_risk(
        self,
        disease: PestDiseaseType,
        weather_forecast: List[WeatherData],
        crop_type: CropType
    ) -> Optional[PestDiseaseRisk]:
        """评估病害风险"""
        if disease not in self.disease_conditions:
            return None
        
        conditions = self.disease_conditions[disease]
        temp_range = conditions["optimal_temp_range"]
        optimal_humidity = conditions["optimal_humidity"]
        
        suitable_days = 0
        for weather in weather_forecast:
            if (temp_range[0] <= weather.temperature <= temp_range[1] and
                weather.humidity >= optimal_humidity - 10):
                suitable_days += 1
        
        probability = min(suitable_days / len(weather_forecast), 1.0) if weather_forecast else 0
        
        if probability < 0.3:
            return None
        
        risk_level = RiskLevel.LOW
        if probability >= 0.7:
            risk_level = RiskLevel.HIGH
        elif probability >= 0.5:
            risk_level = RiskLevel.MEDIUM
        
        start_time = weather_forecast[0].timestamp if weather_forecast else datetime.now()
        end_time = weather_forecast[-1].timestamp if weather_forecast else datetime.now()
        
        return PestDiseaseRisk(
            pest_disease_type=disease,
            risk_level=risk_level,
            occur_probability=probability,
            trigger_conditions={
                "temperature_range": temp_range,
                "humidity_threshold": optimal_humidity,
                "suitable_days": suitable_days
            },
            risk_period=(start_time, end_time),
            prevention_measures=self._get_prevention_measures(disease),
            control_measures=self._get_control_measures(disease),
            chemical_recommendations=self._get_chemical_options(disease),
            confidence=probability
        )
    
    def _assess_pest_risk(
        self,
        pest: PestDiseaseType,
        weather_forecast: List[WeatherData],
        crop_type: CropType
    ) -> Optional[PestDiseaseRisk]:
        """评估虫害风险"""
        if pest not in self.pest_conditions:
            return None
        
        conditions = self.pest_conditions[pest]
        temp_range = conditions["optimal_temp_range"]
        humidity_range = conditions["optimal_humidity_range"]
        
        suitable_days = 0
        for weather in weather_forecast:
            if (temp_range[0] <= weather.temperature <= temp_range[1] and
                humidity_range[0] <= weather.humidity <= humidity_range[1]):
                suitable_days += 1
        
        probability = min(suitable_days / len(weather_forecast), 1.0) if weather_forecast else 0
        
        if probability < 0.3:
            return None
        
        risk_level = RiskLevel.LOW
        if probability >= 0.7:
            risk_level = RiskLevel.HIGH
        elif probability >= 0.5:
            risk_level = RiskLevel.MEDIUM
        
        start_time = weather_forecast[0].timestamp if weather_forecast else datetime.now()
        end_time = weather_forecast[-1].timestamp if weather_forecast else datetime.now()
        
        return PestDiseaseRisk(
            pest_disease_type=pest,
            risk_level=risk_level,
            occur_probability=probability,
            trigger_conditions={
                "temperature_range": temp_range,
                "humidity_range": humidity_range,
                "suitable_days": suitable_days
            },
            risk_period=(start_time, end_time),
            prevention_measures=self._get_prevention_measures(pest),
            control_measures=self._get_control_measures(pest),
            chemical_recommendations=self._get_chemical_options(pest),
            confidence=probability
        )
    
    def _get_prevention_measures(self, pest_disease: PestDiseaseType) -> List[str]:
        """获取预防措施"""
        measures = {
            PestDiseaseType.DOWNY_MILDEW: [
                "选用抗病品种",
                "合理密植，改善通风透光",
                "控制田间湿度",
                "及时清除病株残体"
            ],
            PestDiseaseType.POWDERY_MILDEW: [
                "选用抗病品种",
                "避免偏施氮肥",
                "增加磷钾肥",
                "及时清除病叶"
            ],
            PestDiseaseType.RUST: [
                "选用抗病品种",
                "适期晚播",
                "清除田间病残体",
                "合理轮作"
            ],
            PestDiseaseType.APHID: [
                "清除田间杂草",
                "保护天敌（瓢虫、草蛉）",
                "悬挂黄板诱杀",
                "银灰色地膜避蚜"
            ],
            PestDiseaseType.RED_SPIDER: [
                "清除田间杂草",
                "保护天敌（捕食螨）",
                "增加田间湿度",
                "避免干旱"
            ]
        }
        return measures.get(pest_disease, ["加强田间管理", "及时观察"])
    
    def _get_control_measures(self, pest_disease: PestDiseaseType) -> List[str]:
        """获取防治措施"""
        measures = {
            PestDiseaseType.DOWNY_MILDEW: [
                "发病初期及时喷药",
                "注意药剂轮换使用",
                "重点喷施叶片背面",
                "7-10天喷一次，连续2-3次"
            ],
            PestDiseaseType.POWDERY_MILDEW: [
                "发病初期及时防治",
                "均匀喷施药剂",
                "注意叶片正反面",
                "间隔7天喷一次"
            ],
            PestDiseaseType.APHID: [
                "点片发生时挑治",
                "全面发生时普治",
                "喷药要均匀周到",
                "注意叶片背面"
            ],
            PestDiseaseType.RED_SPIDER: [
                "早期发现早期防治",
                "重点喷施叶背",
                "药剂要轮换使用",
                "连续防治2-3次"
            ]
        }
        return measures.get(pest_disease, ["及时防治", "科学用药"])
    
    def _get_chemical_options(self, pest_disease: PestDiseaseType) -> List[str]:
        """获取化学防治选项"""
        options = {
            PestDiseaseType.DOWNY_MILDEW: [
                "甲霜灵·锰锌",
                "霜脲·锰锌",
                "烯酰吗啉",
                "霜霉威"
            ],
            PestDiseaseType.POWDERY_MILDEW: [
                "三唑酮",
                "腈菌唑",
                "苯醚甲环唑",
                "氟硅唑"
            ],
            PestDiseaseType.RUST: [
                "三唑酮",
                "戊唑醇",
                "苯醚甲环唑",
                "丙环唑"
            ],
            PestDiseaseType.APHID: [
                "吡虫啉",
                "啶虫脒",
                "噻虫嗪",
                "苦参碱"
            ],
            PestDiseaseType.RED_SPIDER: [
                "阿维菌素",
                "哒螨灵",
                "螺螨酯",
                "联苯肼酯"
            ]
        }
        return options.get(pest_disease, ["请咨询当地农技部门"])


class WeatherSuitabilityTool:
    """气象适宜度评分工具"""
    
    def __init__(self):
        self.name = "weather_suitability"
        self.description = "农事操作气象适宜度评分"
        
        self.operation_requirements = {
            OperationWindow.SPRAYING: {
                "max_wind_speed": 3.0,
                "max_precipitation": 0.5,
                "optimal_temp_range": (15, 30),
                "optimal_humidity_range": (40, 70),
                "avoid_rain_hours": 6
            },
            OperationWindow.IRRIGATION: {
                "max_precipitation": 5.0,
                "optimal_temp_range": (10, 35),
                "avoid_high_temp": True
            },
            OperationWindow.FERTILIZING: {
                "max_precipitation": 10.0,
                "optimal_temp_range": (15, 30),
                "avoid_rain_before": 24
            },
            OperationWindow.HARVESTING: {
                "max_precipitation": 0.5,
                "optimal_temp_range": (15, 30),
                "max_humidity": 75,
                "avoid_rain_hours": 12
            },
            OperationWindow.SOWING: {
                "optimal_temp_range": (10, 25),
                "optimal_soil_moisture": (60, 80),
                "avoid_heavy_rain": True
            },
            OperationWindow.TRANSPLANTING: {
                "optimal_temp_range": (15, 28),
                "max_wind_speed": 4.0,
                "avoid_strong_sun": True
            }
        }
    
    def assess_operation_suitability(
        self,
        operation_type: OperationWindow,
        weather_forecast: List[WeatherData],
        crop_type: Optional[CropType] = None
    ) -> WeatherSuitabilityScore:
        """
        评估农事操作适宜度
        
        Args:
            operation_type: 操作类型
            weather_forecast: 天气预报数据
            crop_type: 作物类型
        
        Returns:
            适宜度评分结果
        """
        requirements = self.operation_requirements.get(operation_type, {})
        
        if not weather_forecast:
            return WeatherSuitabilityScore(
                operation_type=operation_type,
                suitability_score=0,
                risk_level=RiskLevel.HIGH,
                optimal_dates=[],
                optimal_periods=[],
                unsuitable_reasons=["无天气预报数据"],
                weather_forecast="数据缺失",
                confidence=0
            )
        
        scores = []
        optimal_dates = []
        optimal_periods = []
        unsuitable_reasons = []
        
        for weather in weather_forecast:
            score = 100
            reasons = []
            
            if operation_type == OperationWindow.SPRAYING:
                if weather.wind_speed > requirements.get("max_wind_speed", 3.0):
                    score -= 30
                    reasons.append(f"风速过大({weather.wind_speed}m/s)")
                
                if weather.precipitation > requirements.get("max_precipitation", 0.5):
                    score -= 40
                    reasons.append(f"有降雨({weather.precipitation}mm)")
                
                temp_range = requirements.get("optimal_temp_range", (15, 30))
                if not (temp_range[0] <= weather.temperature <= temp_range[1]):
                    score -= 20
                    reasons.append(f"温度不适宜({weather.temperature}°C)")
                
                humidity_range = requirements.get("optimal_humidity_range", (40, 70))
                if not (humidity_range[0] <= weather.humidity <= humidity_range[1]):
                    score -= 10
                    reasons.append(f"湿度不适宜({weather.humidity}%)")
            
            elif operation_type == OperationWindow.HARVESTING:
                if weather.precipitation > requirements.get("max_precipitation", 0.5):
                    score -= 50
                    reasons.append(f"有降雨({weather.precipitation}mm)")
                
                if weather.humidity > requirements.get("max_humidity", 75):
                    score -= 20
                    reasons.append(f"湿度过高({weather.humidity}%)")
                
                temp_range = requirements.get("optimal_temp_range", (15, 30))
                if not (temp_range[0] <= weather.temperature <= temp_range[1]):
                    score -= 15
                    reasons.append(f"温度不适宜({weather.temperature}°C)")
            
            elif operation_type == OperationWindow.IRRIGATION:
                if weather.precipitation > requirements.get("max_precipitation", 5.0):
                    score -= 40
                    reasons.append(f"有降雨({weather.precipitation}mm)，无需灌溉")
                
                if requirements.get("avoid_high_temp", True) and weather.max_temperature > 32:
                    score -= 20
                    reasons.append(f"高温时段({weather.max_temperature}°C)，建议避开")
            
            elif operation_type == OperationWindow.FERTILIZING:
                if weather.precipitation > requirements.get("max_precipitation", 10.0):
                    score -= 50
                    reasons.append(f"降雨量大({weather.precipitation}mm)，肥料易流失")
                
                temp_range = requirements.get("optimal_temp_range", (15, 30))
                if not (temp_range[0] <= weather.temperature <= temp_range[1]):
                    score -= 15
                    reasons.append(f"温度不适宜({weather.temperature}°C)")
            
            scores.append(max(score, 0))
            
            if score >= 70:
                optimal_dates.append(weather.timestamp.date())
                hour = weather.timestamp.hour
                if 8 <= hour <= 11:
                    optimal_periods.append(f"{weather.timestamp.strftime('%m月%d日')} 上午")
                elif 14 <= hour <= 17:
                    optimal_periods.append(f"{weather.timestamp.strftime('%m月%d日')} 下午")
            
            if reasons:
                unsuitable_reasons.extend(reasons)
        
        avg_score = sum(scores) / len(scores) if scores else 0
        
        risk_level = RiskLevel.LOW
        if avg_score < 40:
            risk_level = RiskLevel.CRITICAL
        elif avg_score < 60:
            risk_level = RiskLevel.HIGH
        elif avg_score < 80:
            risk_level = RiskLevel.MEDIUM
        
        unique_dates = list(set(optimal_dates))
        unique_dates.sort()
        
        unique_periods = list(set(optimal_periods))
        unique_periods.sort()
        
        unsuitable_reasons = list(set(unsuitable_reasons))
        
        weather_summary = self._generate_weather_summary(weather_forecast)
        
        confidence = min(len(weather_forecast) / 24, 1.0)
        
        return WeatherSuitabilityScore(
            operation_type=operation_type,
            suitability_score=round(avg_score, 1),
            risk_level=risk_level,
            optimal_dates=unique_dates[:5],
            optimal_periods=unique_periods[:5],
            unsuitable_reasons=unsuitable_reasons[:5],
            weather_forecast=weather_summary,
            confidence=confidence
        )
    
    def _generate_weather_summary(self, weather_forecast: List[WeatherData]) -> str:
        """生成天气预报摘要"""
        if not weather_forecast:
            return "无数据"
        
        temps = [w.temperature for w in weather_forecast]
        precips = [w.precipitation for w in weather_forecast]
        
        min_temp = min(temps)
        max_temp = max(temps)
        total_precip = sum(precips)
        
        summary = f"温度{min_temp:.0f}~{max_temp:.0f}°C"
        
        if total_precip > 0:
            summary += f"，累计降水{total_precip:.1f}mm"
        
        return summary
    
    def get_all_operations_suitability(
        self,
        weather_forecast: List[WeatherData],
        crop_type: Optional[CropType] = None
    ) -> Dict[str, WeatherSuitabilityScore]:
        """
        获取所有农事操作的适宜度评分
        
        Args:
            weather_forecast: 天气预报数据
            crop_type: 作物类型
        
        Returns:
            各操作适宜度评分字典
        """
        results = {}
        
        for operation in OperationWindow:
            score = self.assess_operation_suitability(operation, weather_forecast, crop_type)
            results[operation.value] = score
        
        return results

