# -*- coding: utf-8 -*-
"""
规则引擎核心逻辑
实现确定性农事决策的规则判定
"""
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
from src.models import (
    CropType, GrowthStage, OperationType, 
    RiskLevel, OperationRecommendation,
    DisasterType, DisasterWarning,
    DiseaseRisk, AgriculturalWeatherData,
    Location, FieldInfo
)
from config.settings import (
    WEATHER_THRESHOLDS, CROP_GROWTH_STAGES,
    DISEASE_RISK_THRESHOLDS, DISASTER_THRESHOLDS,
    AGRICULTURAL_REGIONS
)


class RuleEngine:
    """规则引擎"""
    
    def __init__(self):
        self.weather_thresholds = WEATHER_THRESHOLDS
        self.crop_stages = CROP_GROWTH_STAGES
        self.disease_thresholds = DISEASE_RISK_THRESHOLDS
        self.disaster_thresholds = DISASTER_THRESHOLDS
        self.agri_regions = AGRICULTURAL_REGIONS
    
    def judge_sowing_window(
        self,
        weather_data: AgriculturalWeatherData,
        crop_type: CropType,
        location: Location
    ) -> OperationRecommendation:
        """
        判断播种窗口期
        
        Args:
            weather_data: 农业气象数据
            crop_type: 作物类型
            location: 地理位置信息
        
        Returns:
            播种建议
        """
        crop_name = crop_type.value
        thresholds = self.weather_thresholds["播种"].get(crop_name, {})
        
        current_temp = weather_data.base_weather.temperature
        min_temp = thresholds.get("最低温度", 10)
        suitable_range = thresholds.get("适宜温度范围", (15, 25))
        
        if current_temp < min_temp:
            suitability = RiskLevel.HIGH
            details = f"当前温度{current_temp}℃低于播种最低温度{min_temp}℃，不适宜播种"
            warnings = ["低温风险：可能影响种子发芽", "建议等待温度回升"]
        elif suitable_range[0] <= current_temp <= suitable_range[1]:
            suitability = RiskLevel.LOW
            details = f"当前温度{current_temp}℃处于适宜范围{suitable_range}，适宜播种"
            warnings = []
        else:
            suitability = RiskLevel.MEDIUM
            details = f"当前温度{current_temp}℃略高于适宜范围，可以播种但需注意"
            warnings = ["温度偏高可能影响出苗率"]
        
        optimal_time = datetime.now()
        time_window = (
            optimal_time,
            optimal_time + timedelta(days=7)
        )
        
        return OperationRecommendation(
            operation_type=OperationType.SOWING,
            suitability_level=suitability,
            optimal_time=optimal_time,
            time_window=time_window,
            operation_details=details,
            precautions=["选择晴好天气播种", "注意土壤墒情"],
            risk_warnings=warnings,
            evidence=f"依据：{crop_name}播种温度阈值{min_temp}℃"
        )
    
    def judge_irrigation_timing(
        self,
        weather_data: AgriculturalWeatherData,
        soil_moisture: float,
        crop_type: CropType,
        growth_stage: str
    ) -> OperationRecommendation:
        """
        判断灌溉时机
        
        Args:
            weather_data: 农业气象数据
            soil_moisture: 土壤墒情
            crop_type: 作物类型
            growth_stage: 生长阶段
        
        Returns:
            灌溉建议
        """
        irrigation_idx = weather_data.irrigation_demand_index
        thresholds = self.weather_thresholds["灌溉"]
        
        if irrigation_idx > 0.7:
            suitability = RiskLevel.LOW
            details = f"土壤墒情{soil_moisture}%偏低，灌溉需求指数{irrigation_idx:.2f}，急需灌溉"
            warnings = ["干旱胁迫风险高"]
        elif irrigation_idx > 0.3:
            suitability = RiskLevel.MEDIUM
            details = f"土壤墒情{soil_moisture}%适中，灌溉需求指数{irrigation_idx:.2f}，建议适量灌溉"
            warnings = []
        else:
            suitability = RiskLevel.HIGH
            details = f"土壤墒情{soil_moisture}%充足，暂不需要灌溉"
            warnings = ["过量灌溉可能造成浪费或涝害"]
        
        optimal_time = datetime.now()
        time_window = (optimal_time, optimal_time + timedelta(days=3))
        
        return OperationRecommendation(
            operation_type=OperationType.IRRIGATION,
            suitability_level=suitability,
            optimal_time=optimal_time,
            time_window=time_window,
            operation_details=details,
            precautions=["避开中午高温时段", "注意天气预报"],
            risk_warnings=warnings,
            evidence=f"依据：土壤墒情阈值{thresholds['土壤墒情下限']}-{thresholds['土壤墒情上限']}%"
        )
    
    def judge_pest_control_timing(
        self,
        weather_data: AgriculturalWeatherData
    ) -> OperationRecommendation:
        """
        判断植保作业时机
        
        Args:
            weather_data: 农业气象数据
        
        Returns:
            植保建议
        """
        thresholds = self.weather_thresholds["植保"]
        base_weather = weather_data.base_weather
        
        wind_ok = base_weather.wind_speed < thresholds["风速上限"]
        temp_ok = thresholds["温度范围"][0] <= base_weather.temperature <= thresholds["温度范围"][1]
        humidity_ok = base_weather.humidity < thresholds["湿度上限"]
        no_rain = base_weather.precipitation < 0.1
        
        if wind_ok and temp_ok and humidity_ok and no_rain:
            suitability = RiskLevel.LOW
            details = "当前气象条件适宜植保作业"
            warnings = []
        else:
            suitability = RiskLevel.HIGH
            details = "当前气象条件不适宜植保作业"
            warnings = []
            if not wind_ok:
                warnings.append(f"风速{base_weather.wind_speed}m/s超过阈值{thresholds['风速上限']}m/s，药液易漂移")
            if not temp_ok:
                warnings.append(f"温度{base_weather.temperature}℃不在适宜范围{thresholds['温度范围']}")
            if not humidity_ok:
                warnings.append(f"湿度{base_weather.humidity}%过高，影响药效")
            if not no_rain:
                warnings.append("有降水，药液易被冲刷")
        
        optimal_time = datetime.now() if suitability == RiskLevel.LOW else datetime.now() + timedelta(days=1)
        time_window = (optimal_time, optimal_time + timedelta(hours=6))
        
        return OperationRecommendation(
            operation_type=OperationType.PEST_CONTROL,
            suitability_level=suitability,
            optimal_time=optimal_time,
            time_window=time_window,
            operation_details=details,
            precautions=["选择无风或微风时段", "避开高温时段", "注意个人防护"],
            risk_warnings=warnings,
            evidence=f"依据：植保作业气象标准（风速<{thresholds['风速上限']}级，无降水，温度适宜）"
        )
    
    def assess_disease_risk(
        self,
        weather_data: AgriculturalWeatherData,
        crop_type: CropType,
        growth_stage: str
    ) -> List[DiseaseRisk]:
        """
        评估病虫害风险
        
        Args:
            weather_data: 农业气象数据
            crop_type: 作物类型
            growth_stage: 生长阶段
        
        Returns:
            病虫害风险列表
        """
        risks = []
        base_weather = weather_data.base_weather
        
        for disease_name, thresholds in self.disease_thresholds.items():
            risk_score = 0.0
            
            if "温度范围" in thresholds:
                temp_range = thresholds["温度范围"]
                if temp_range[0] <= base_weather.temperature <= temp_range[1]:
                    risk_score += 0.4
            
            if "湿度下限" in thresholds:
                if base_weather.humidity >= thresholds["湿度下限"]:
                    risk_score += 0.3
            
            if "湿度范围" in thresholds:
                hum_range = thresholds["湿度范围"]
                if hum_range[0] <= base_weather.humidity <= hum_range[1]:
                    risk_score += 0.3
            
            if "湿度上限" in thresholds:
                if base_weather.humidity <= thresholds["湿度上限"]:
                    risk_score += 0.2
            
            if risk_score > 0.6:
                risk_level = RiskLevel.HIGH
            elif risk_score > 0.3:
                risk_level = RiskLevel.MEDIUM
            else:
                risk_level = RiskLevel.LOW
            
            if risk_level != RiskLevel.LOW:
                optimal_window = (
                    datetime.now() + timedelta(days=1),
                    datetime.now() + timedelta(days=3)
                )
                
                risks.append(DiseaseRisk(
                    disease_name=disease_name,
                    risk_level=risk_level,
                    occur_probability=risk_score,
                    optimal_control_window=optimal_window,
                    control_measures=["喷施杀菌剂", "加强田间管理"],
                    prevention_methods=["合理密植", "及时排水", "增施磷钾肥"]
                ))
        
        return risks
    
    def assess_disaster_risk(
        self,
        weather_data: AgriculturalWeatherData,
        forecast_days: int = 7
    ) -> List[DisasterWarning]:
        """
        评估气象灾害风险
        
        Args:
            weather_data: 农业气象数据
            forecast_days: 预报天数
        
        Returns:
            灾害预警列表
        """
        warnings = []
        base_weather = weather_data.base_weather
        
        if base_weather.min_temperature <= self.disaster_thresholds["霜冻"]["温度阈值"]:
            temp = base_weather.min_temperature
            level = RiskLevel.MEDIUM
            for level_name, threshold in self.disaster_thresholds["霜冻"]["预警等级"].items():
                if temp <= threshold:
                    level = RiskLevel(level_name)
            
            warnings.append(DisasterWarning(
                disaster_type=DisasterType.FROST,
                risk_level=level,
                occur_time=datetime.now() + timedelta(hours=12),
                duration=6,
                intensity=f"最低温度{temp}℃",
                defense_measures=["熏烟防霜", "田间灌水", "秸秆覆盖"],
                emergency_actions=["提前抢收成熟作物", "加强田间巡查"]
            ))
        
        if base_weather.precipitation >= self.disaster_thresholds["暴雨"]["降水阈值"]:
            precip = base_weather.precipitation
            level = RiskLevel.MEDIUM
            for level_name, threshold in self.disaster_thresholds["暴雨"]["预警等级"].items():
                if precip >= threshold:
                    level = RiskLevel(level_name)
            
            warnings.append(DisasterWarning(
                disaster_type=DisasterType.RAINSTORM,
                risk_level=level,
                occur_time=datetime.now(),
                duration=24,
                intensity=f"降水量{precip}mm",
                defense_measures=["疏通沟渠", "加固田埂", "准备排水设备"],
                emergency_actions=["抢收成熟作物", "及时排涝", "雨后松土通气"]
            ))
        
        if base_weather.max_temperature >= self.disaster_thresholds["高温热害"]["温度阈值"]:
            warnings.append(DisasterWarning(
                disaster_type=DisasterType.HEAT_WAVE,
                risk_level=RiskLevel.HIGH,
                occur_time=datetime.now() + timedelta(hours=6),
                duration=12,
                intensity=f"最高温度{base_weather.max_temperature}℃",
                defense_measures=["田间灌水降温", "叶面喷肥", "喷施抗蒸腾剂"],
                emergency_actions=["避开高温时段作业", "加强田间巡查"]
            ))
        
        if base_weather.wind_speed >= self.disaster_thresholds["大风"]["风速阈值"]:
            warnings.append(DisasterWarning(
                disaster_type=DisasterType.STRONG_WIND,
                risk_level=RiskLevel.MEDIUM,
                occur_time=datetime.now(),
                duration=6,
                intensity=f"风速{base_weather.wind_speed}m/s",
                defense_measures=["加固设施大棚", "高秆作物培土固根", "搭架支撑"],
                emergency_actions=["停止高空作业", "检查设施安全"]
            ))
        
        return warnings
    
    def determine_growth_stage(
        self,
        crop_type: CropType,
        sowing_date: datetime,
        accumulated_temperature: float
    ) -> Tuple[GrowthStage, int]:
        """
        根据积温判断作物生育期
        
        Args:
            crop_type: 作物类型
            sowing_date: 播种日期
            accumulated_temperature: 累计积温
        
        Returns:
            (生育期, 播种后天数)
        """
        days_after_sowing = (datetime.now() - sowing_date).days
        
        crop_name = crop_type.value
        stages = self.crop_stages.get(crop_name, [])
        
        if not stages:
            return GrowthStage.SEEDLING, days_after_sowing
        
        stage_index = min(int(accumulated_temperature / 200), len(stages) - 1)
        stage_name = stages[stage_index]
        
        try:
            growth_stage = GrowthStage(stage_name)
        except ValueError:
            growth_stage = GrowthStage.SEEDLING
        
        return growth_stage, days_after_sowing
    
    def judge_fertilization_timing(
        self,
        weather_data: AgriculturalWeatherData,
        fertilizer_type: str = "追肥",
        crop_type: Optional[CropType] = None,
        growth_stage: Optional[str] = None
    ) -> OperationRecommendation:
        """
        判断施肥窗口期
        
        Args:
            weather_data: 农业气象数据
            fertilizer_type: 肥料类型（基肥/追肥/叶面肥）
            crop_type: 作物类型
            growth_stage: 生长阶段
        
        Returns:
            施肥建议
        """
        thresholds = self.weather_thresholds["施肥"]
        base_weather = weather_data.base_weather
        
        current_temp = base_weather.temperature
        current_precip = base_weather.precipitation
        current_wind = base_weather.wind_speed
        
        temp_range = thresholds["温度范围"]
        precip_threshold = thresholds["降水阈值"]
        wind_threshold = thresholds["风速上限"]
        
        risk_factors = []
        suitability_score = 100
        
        if current_precip > precip_threshold:
            risk_factors.append(f"未来有降水{current_precip}mm，肥料易流失")
            suitability_score -= 40
        
        if not (temp_range[0] <= current_temp <= temp_range[1]):
            if current_temp > temp_range[1]:
                risk_factors.append(f"温度{current_temp}℃偏高，肥料易挥发")
                suitability_score -= 20
            else:
                risk_factors.append(f"温度{current_temp}℃偏低，作物吸收慢")
                suitability_score -= 15
        
        if current_wind > wind_threshold:
            risk_factors.append(f"风速{current_wind}m/s较大，肥料易飘散")
            suitability_score -= 20
        
        if suitability_score >= 80:
            suitability = RiskLevel.LOW
            details = f"当前气象条件适宜{fertilizer_type}，温度{current_temp}℃，无降水风险"
        elif suitability_score >= 50:
            suitability = RiskLevel.MEDIUM
            details = f"当前气象条件基本适宜{fertilizer_type}，但存在一定风险"
        else:
            suitability = RiskLevel.HIGH
            details = f"当前气象条件不适宜{fertilizer_type}，建议推迟"
        
        fertilizer_info = thresholds.get(fertilizer_type, {})
        precautions = fertilizer_info.get("注意事项", [])
        precautions.extend(["避开中午高温时段", "施肥后及时覆土或灌水"])
        
        optimal_time = datetime.now()
        time_window = (optimal_time, optimal_time + timedelta(days=3))
        
        return OperationRecommendation(
            operation_type=OperationType.FERTILIZATION,
            suitability_level=suitability,
            optimal_time=optimal_time,
            time_window=time_window,
            operation_details=details,
            precautions=precautions,
            risk_warnings=risk_factors,
            evidence=f"依据：施肥温度范围{temp_range}℃，降水阈值{precip_threshold}mm"
        )
    
    def judge_harvest_timing(
        self,
        weather_data: AgriculturalWeatherData,
        crop_type: CropType,
        maturity_progress: float = 80.0,
        grain_moisture: float = 20.0
    ) -> OperationRecommendation:
        """
        判断最佳收获期
        
        Args:
            weather_data: 农业气象数据
            crop_type: 作物类型
            maturity_progress: 成熟进度（%）
            grain_moisture: 籽粒含水率（%）
        
        Returns:
            收获建议
        """
        thresholds = self.weather_thresholds["收获"]
        base_weather = weather_data.base_weather
        
        current_precip = base_weather.precipitation
        current_wind = base_weather.wind_speed
        current_humidity = base_weather.humidity
        
        risk_factors = []
        suitability_score = 100
        
        if maturity_progress < 80:
            risk_factors.append(f"作物成熟度{maturity_progress}%不足，建议等待成熟")
            suitability_score -= 30
        
        if grain_moisture > thresholds["籽粒含水率上限"]:
            risk_factors.append(f"籽粒含水率{grain_moisture}%偏高，需晾晒")
            suitability_score -= 20
        
        if current_precip > 5:
            risk_factors.append(f"未来有降水{current_precip}mm，不宜收获")
            suitability_score -= 40
        
        if current_wind > 8:
            risk_factors.append(f"风速{current_wind}m/s较大，易造成落粒损失")
            suitability_score -= 25
        
        if current_humidity > 80:
            risk_factors.append(f"湿度{current_humidity}%偏高，易导致霉变")
            suitability_score -= 20
        
        if suitability_score >= 80:
            suitability = RiskLevel.LOW
            details = f"当前条件适宜收获，成熟度{maturity_progress}%，天气晴好"
        elif suitability_score >= 50:
            suitability = RiskLevel.MEDIUM
            details = f"当前条件基本适宜收获，但需注意风险"
        else:
            suitability = RiskLevel.HIGH
            details = f"当前条件不适宜收获，建议推迟"
        
        optimal_time = datetime.now()
        time_window = (optimal_time, optimal_time + timedelta(days=thresholds["晾晒天数"]))
        
        return OperationRecommendation(
            operation_type=OperationType.HARVEST,
            suitability_level=suitability,
            optimal_time=optimal_time,
            time_window=time_window,
            operation_details=details,
            precautions=["选择晴好天气收获", "及时晾晒或烘干", "注意防雨防潮"],
            risk_warnings=risk_factors,
            evidence=f"依据：成熟度{maturity_progress}%，籽粒含水率{grain_moisture}%"
        )
    
    def recommend_variety(
        self,
        location: Location,
        crop_type: CropType,
        accumulated_temperature: Optional[float] = None
    ) -> dict:
        """
        品种适配建议
        
        Args:
            location: 地理位置信息
            crop_type: 作物类型
            accumulated_temperature: 区域积温
        
        Returns:
            品种推荐结果
        """
        region_name = location.agricultural_region
        region_info = self.agri_regions.get(region_name, {})
        
        if not region_info:
            return {
                "success": False,
                "message": f"未找到区域{region_name}的适配信息"
            }
        
        frost_free_days = region_info.get("无霜期范围", (120, 180))
        temp_range = region_info.get("积温范围", (2500, 4000))
        
        avg_frost_free = sum(frost_free_days) / 2
        avg_accum_temp = sum(temp_range) / 2
        
        crop_name = crop_type.value
        
        variety_recommendations = {
            "玉米": {
                "早熟": {"积温": 2200, "生育期": 90, "适宜区域": ["东北春播区", "西北旱作区"]},
                "中熟": {"积温": 2600, "生育期": 105, "适宜区域": ["东北春播区", "黄淮海两熟区"]},
                "晚熟": {"积温": 3000, "生育期": 120, "适宜区域": ["黄淮海两熟区", "南方稻区"]}
            },
            "小麦": {
                "冬性": {"春化天数": 40, "适宜区域": ["黄淮海两熟区", "西北旱作区"]},
                "半冬性": {"春化天数": 30, "适宜区域": ["黄淮海两熟区"]},
                "春性": {"春化天数": 10, "适宜区域": ["东北春播区"]}
            },
            "水稻": {
                "早稻": {"积温": 2800, "生育期": 110, "适宜区域": ["南方稻区"]},
                "中稻": {"积温": 3200, "生育期": 130, "适宜区域": ["南方稻区"]},
                "晚稻": {"积温": 3600, "生育期": 150, "适宜区域": ["南方稻区"]}
            },
            "大豆": {
                "早熟": {"积温": 2100, "生育期": 85, "适宜区域": ["东北春播区"]},
                "中熟": {"积温": 2400, "生育期": 100, "适宜区域": ["东北春播区", "黄淮海两熟区"]},
                "晚熟": {"积温": 2700, "生育期": 115, "适宜区域": ["黄淮海两熟区"]}
            }
        }
        
        crop_varieties = variety_recommendations.get(crop_name, {})
        
        if not crop_varieties:
            return {
                "success": False,
                "message": f"暂无{crop_name}的品种适配信息"
            }
        
        suitable_varieties = []
        for variety_name, variety_info in crop_varieties.items():
            if region_name in variety_info.get("适宜区域", []):
                suitable_varieties.append({
                    "品种类型": variety_name,
                    "积温要求": variety_info.get("积温", "N/A"),
                    "生育期": variety_info.get("生育期", "N/A"),
                    "适宜性": "高度适宜"
                })
        
        if not suitable_varieties:
            for variety_name, variety_info in crop_varieties.items():
                suitable_varieties.append({
                    "品种类型": variety_name,
                    "积温要求": variety_info.get("积温", "N/A"),
                    "生育期": variety_info.get("生育期", "N/A"),
                    "适宜性": "可尝试种植"
                })
        
        return {
            "success": True,
            "区域": region_name,
            "作物": crop_name,
            "无霜期": f"{frost_free_days[0]}-{frost_free_days[1]}天",
            "积温范围": f"{temp_range[0]}-{temp_range[1]}℃",
            "推荐品种": suitable_varieties,
            "建议": "选择适宜熟期的品种，避免越区种植"
        }
    
    def plan_crop_rotation(
        self,
        location: Location,
        previous_crop: CropType,
        previous_harvest_date: datetime,
        next_crop: CropType
    ) -> dict:
        """
        茬口衔接规划
        
        Args:
            location: 地理位置信息
            previous_crop: 前茬作物
            previous_harvest_date: 前茬收获日期
            next_crop: 下茬作物
        
        Returns:
            茬口衔接方案
        """
        region_name = location.agricultural_region
        
        rotation_schemes = {
            "黄淮海两熟区": {
                ("小麦", "玉米"): {
                    "衔接方式": "直播",
                    "时间间隔": "7-10天",
                    "注意事项": ["抢时播种", "秸秆还田", "适量增施氮肥"]
                },
                ("玉米", "小麦"): {
                    "衔接方式": "直播",
                    "时间间隔": "10-15天",
                    "注意事项": ["深耕整地", "施足基肥", "适期播种"]
                }
            },
            "南方稻区": {
                ("水稻", "水稻"): {
                    "衔接方式": "育苗移栽",
                    "时间间隔": "30-40天",
                    "注意事项": ["提前育秧", "抢时移栽", "加强田间管理"]
                },
                ("水稻", "小麦"): {
                    "衔接方式": "直播",
                    "时间间隔": "15-20天",
                    "注意事项": ["及时排水晒田", "深耕整地", "适期播种"]
                }
            }
        }
        
        region_schemes = rotation_schemes.get(region_name, {})
        
        crop_pair = (previous_crop.value, next_crop.value)
        scheme = region_schemes.get(crop_pair)
        
        if not scheme:
            return {
                "success": False,
                "区域": region_name,
                "前茬作物": previous_crop.value,
                "下茬作物": next_crop.value,
                "消息": f"暂无{previous_crop.value}-{next_crop.value}茬口衔接方案，建议咨询当地农技部门"
            }
        
        days_gap = (datetime.now() - previous_harvest_date).days
        
        return {
            "success": True,
            "区域": region_name,
            "前茬作物": previous_crop.value,
            "前茬收获日期": previous_harvest_date.strftime("%Y-%m-%d"),
            "下茬作物": next_crop.value,
            "衔接方式": scheme["衔接方式"],
            "建议时间间隔": scheme["时间间隔"],
            "已间隔天数": days_gap,
            "注意事项": scheme["注意事项"],
            "建议": "合理安排茬口，充分利用光温资源"
        }
    
    def diagnose_crop_symptom(
        self,
        symptom_description: str,
        weather_data: AgriculturalWeatherData,
        crop_type: CropType,
        growth_stage: Optional[str] = None
    ) -> dict:
        """
        作物异常症状诊断
        
        Args:
            symptom_description: 症状描述
            weather_data: 农业气象数据
            crop_type: 作物类型
            growth_stage: 生长阶段
        
        Returns:
            诊断结果
        """
        symptom_keywords = {
            "黄叶": ["缺氮", "缺铁", "干旱", "涝害", "病虫害"],
            "斑点": ["病害", "虫害", "缺素", "药害"],
            "枯萎": ["干旱", "根腐病", "枯萎病", "高温热害"],
            "倒伏": ["大风", "茎腐病", "密度过大", "氮肥过量"],
            "卷叶": ["干旱", "蚜虫", "病毒病", "药害"],
            "矮化": ["病毒病", "缺素", "除草剂药害", "根结线虫"],
            "畸形": ["病毒病", "药害", "激素过量", "虫害"],
            "落花落果": ["高温", "干旱", "营养不足", "激素失调"]
        }
        
        base_weather = weather_data.base_weather
        current_temp = base_weather.temperature
        current_humidity = base_weather.humidity
        current_precip = base_weather.precipitation
        
        possible_causes = []
        
        for symptom, causes in symptom_keywords.items():
            if symptom in symptom_description:
                possible_causes.extend(causes)
        
        if not possible_causes:
            possible_causes = ["需进一步诊断", "建议田间实地查看"]
        
        diagnosis_results = []
        
        for cause in possible_causes:
            probability = 0.0
            evidence = []
            
            if cause == "干旱":
                if current_precip < 5 and weather_data.drought_index and weather_data.drought_index < -1:
                    probability = 0.8
                    evidence.append(f"近期降水{current_precip}mm，干旱指数{weather_data.drought_index:.2f}")
                elif current_precip < 10:
                    probability = 0.5
                    evidence.append(f"近期降水较少{current_precip}mm")
            
            elif cause == "涝害":
                if current_precip > 50:
                    probability = 0.7
                    evidence.append(f"近期强降水{current_precip}mm")
                elif current_humidity > 90:
                    probability = 0.5
                    evidence.append(f"空气湿度高{current_humidity}%")
            
            elif cause == "高温热害":
                if current_temp > 35:
                    probability = 0.8
                    evidence.append(f"当前温度{current_temp}℃，超过高温阈值")
                elif current_temp > 30:
                    probability = 0.5
                    evidence.append(f"温度偏高{current_temp}℃")
            
            elif cause in ["病害", "根腐病", "枯萎病", "霜霉病", "白粉病"]:
                if current_humidity > 80 and 15 <= current_temp <= 30:
                    probability = 0.7
                    evidence.append(f"温湿度条件适宜病害发生（温度{current_temp}℃，湿度{current_humidity}%）")
                elif current_humidity > 70:
                    probability = 0.4
                    evidence.append(f"湿度较高{current_humidity}%，可能诱发病害")
            
            elif cause in ["虫害", "蚜虫", "红蜘蛛"]:
                if 20 <= current_temp <= 30:
                    probability = 0.6
                    evidence.append(f"温度{current_temp}℃适宜虫害发生")
            
            elif cause == "大风":
                if base_weather.wind_speed > 8:
                    probability = 0.8
                    evidence.append(f"风速{base_weather.wind_speed}m/s，风力较大")
                elif base_weather.wind_speed > 5:
                    probability = 0.4
                    evidence.append(f"风速{base_weather.wind_speed}m/s")
            
            if probability > 0:
                diagnosis_results.append({
                    "可能原因": cause,
                    "概率": f"{probability*100:.1f}%",
                    "气象依据": evidence,
                    "处置建议": self._get_treatment_suggestion(cause, crop_type)
                })
        
        diagnosis_results.sort(key=lambda x: float(x["概率"].rstrip('%')), reverse=True)
        
        return {
            "作物": crop_type.value,
            "生长阶段": growth_stage or "未知",
            "症状描述": symptom_description,
            "诊断结果": diagnosis_results[:5],
            "建议": "结合田间实际情况综合判断，必要时联系农技人员"
        }
    
    def _get_treatment_suggestion(self, cause: str, crop_type: CropType) -> List[str]:
        """获取处置建议"""
        treatment_map = {
            "干旱": [
                "及时灌溉补水",
                "覆盖保墒",
                "叶面喷施抗旱剂"
            ],
            "涝害": [
                "及时排水降渍",
                "中耕松土通气",
                "补施速效肥料"
            ],
            "高温热害": [
                "田间灌水降温",
                "叶面喷肥",
                "喷施抗蒸腾剂"
            ],
            "病害": [
                "及时喷施杀菌剂",
                "清除病叶病株",
                "改善通风透光条件"
            ],
            "虫害": [
                "及时喷施杀虫剂",
                "清除虫卵和幼虫",
                "保护利用天敌"
            ],
            "大风": [
                "加固支撑",
                "培土固根",
                "雨后及时扶正"
            ],
            "缺氮": [
                "追施氮肥",
                "叶面喷施尿素"
            ],
            "缺素": [
                "叶面喷施微量元素肥料",
                "改良土壤"
            ]
        }
        
        return treatment_map.get(cause, ["根据具体情况采取相应措施"])
    
    def assess_storage_risk(
        self,
        weather_data: AgriculturalWeatherData,
        storage_type: str = "常温仓储",
        grain_moisture: float = 14.0,
        storage_duration_days: int = 30
    ) -> dict:
        """
        仓储气象风险评估
        
        Args:
            weather_data: 农业气象数据
            storage_type: 仓储类型
            grain_moisture: 粮食含水率（%）
            storage_duration_days: 已存储天数
        
        Returns:
            仓储风险评估结果
        """
        thresholds = self.weather_thresholds["仓储"]
        base_weather = weather_data.base_weather
        
        current_temp = base_weather.temperature
        current_humidity = base_weather.humidity
        
        risks = []
        risk_level = RiskLevel.LOW
        
        if current_humidity > thresholds["湿度上限"]:
            risk_level = RiskLevel.HIGH if current_humidity > 85 else RiskLevel.MEDIUM
            risks.append({
                "风险类型": "高湿霉变风险",
                "风险等级": risk_level.value,
                "当前湿度": f"{current_humidity}%",
                "阈值": f"{thresholds['湿度上限']}%",
                "危害": "粮食吸湿返潮，易发生霉变、发热",
                "应对措施": [
                    "立即通风除湿",
                    "翻倒粮堆散热",
                    "使用除湿设备",
                    "检查粮食含水率"
                ]
            })
        
        if current_temp > thresholds["温度上限"]:
            temp_risk = RiskLevel.HIGH if current_temp > 30 else RiskLevel.MEDIUM
            risks.append({
                "风险类型": "高温发热风险",
                "风险等级": temp_risk.value,
                "当前温度": f"{current_temp}℃",
                "阈值": f"{thresholds['温度上限']}℃",
                "危害": "粮温升高，加速呼吸作用，诱发热害、虫害",
                "应对措施": [
                    "机械通风降温",
                    "翻仓散热",
                    "避免新粮入仓",
                    "监测粮温变化"
                ]
            })
            if temp_risk == RiskLevel.HIGH:
                risk_level = RiskLevel.HIGH
        
        if current_temp > thresholds["防虫温度"]:
            risks.append({
                "风险类型": "储粮虫害风险",
                "风险等级": RiskLevel.MEDIUM.value,
                "当前温度": f"{current_temp}℃",
                "说明": f"温度超过{thresholds['防虫温度']}℃，害虫活动活跃",
                "应对措施": [
                    "加强虫情监测",
                    "必要时熏蒸处理",
                    "保持低温低湿环境",
                    "清洁仓储环境"
                ]
            })
        
        if grain_moisture > 14.5:
            moisture_risk = RiskLevel.HIGH if grain_moisture > 16 else RiskLevel.MEDIUM
            risks.append({
                "风险类型": "粮食水分偏高",
                "风险等级": moisture_risk.value,
                "当前含水率": f"{grain_moisture}%",
                "安全含水率": "13-14%",
                "危害": "水分偏高易霉变、发热、生虫",
                "应对措施": [
                    "及时晾晒或烘干",
                    "加强通风",
                    "分仓储存",
                    "优先出库"
                ]
            })
        
        if storage_duration_days > 180:
            risks.append({
                "风险类型": "长期储存风险",
                "风险等级": RiskLevel.LOW.value,
                "已储存天数": storage_duration_days,
                "建议": "定期检查粮情，注意品质变化"
            })
        
        overall_status = "安全"
        if risk_level == RiskLevel.HIGH:
            overall_status = "高风险，需立即处理"
        elif risk_level == RiskLevel.MEDIUM:
            overall_status = "中风险，需密切关注"
        elif risks:
            overall_status = "低风险，注意防范"
        
        return {
            "仓储类型": storage_type,
            "环境温度": f"{current_temp}℃",
            "环境湿度": f"{current_humidity}%",
            "粮食含水率": f"{grain_moisture}%",
            "已储存天数": storage_duration_days,
            "整体风险等级": risk_level.value,
            "整体状态": overall_status,
            "风险详情": risks,
            "日常管理建议": [
                "定期监测温湿度",
                "保持通风良好",
                "定期翻仓检查",
                "做好防虫防鼠工作",
                "记录粮情变化"
            ]
        }
    
    def judge_vegetable_planting(
        self,
        weather_data: AgriculturalWeatherData,
        crop_type: CropType,
        season: str = "春季"
    ) -> dict:
        """
        蔬菜种植决策
        
        Args:
            weather_data: 农业气象数据
            crop_type: 蔬菜类型
            season: 种植季节
        
        Returns:
            种植建议
        """
        vegetable_params = {
            "番茄": {
                "适宜温度": (20, 25),
                "最低温度": 15,
                "需水量": "中等",
                "光照需求": "强光",
                "生长周期": "90-120天"
            },
            "黄瓜": {
                "适宜温度": (18, 32),
                "最低温度": 12,
                "需水量": "大",
                "光照需求": "中等",
                "生长周期": "60-90天"
            },
            "辣椒": {
                "适宜温度": (20, 30),
                "最低温度": 15,
                "需水量": "中等",
                "光照需求": "中等",
                "生长周期": "120-150天"
            },
            "白菜": {
                "适宜温度": (15, 20),
                "最低温度": 5,
                "需水量": "大",
                "光照需求": "中等",
                "生长周期": "60-120天"
            },
            "菠菜": {
                "适宜温度": (15, 20),
                "最低温度": -6,
                "需水量": "较大",
                "光照需求": "中等",
                "生长周期": "30-60天"
            },
            "胡萝卜": {
                "适宜温度": (18, 23),
                "最低温度": -3,
                "需水量": "中等",
                "光照需求": "强光",
                "生长周期": "90-120天"
            }
        }
        
        crop_name = crop_type.value
        params = vegetable_params.get(crop_name, vegetable_params["番茄"])
        
        current_temp = weather_data.base_weather.temperature
        suitable_temp = params["适宜温度"]
        min_temp = params["最低温度"]
        
        suitability = RiskLevel.LOW
        warnings = []
        details = []
        
        if current_temp < min_temp:
            suitability = RiskLevel.HIGH
            warnings.append(f"当前温度{current_temp}℃低于最低生长温度{min_temp}℃，不宜种植")
        elif suitable_temp[0] <= current_temp <= suitable_temp[1]:
            details.append(f"当前温度{current_temp}℃处于适宜范围{suitable_temp}℃，适宜种植")
        else:
            suitability = RiskLevel.MEDIUM
            warnings.append(f"当前温度{current_temp}℃略偏离适宜范围，需注意管理")
        
        if weather_data.base_weather.precipitation > 20:
            warnings.append("近期有较大降水，注意排水防涝")
        
        return {
            "蔬菜类型": crop_name,
            "种植季节": season,
            "当前温度": f"{current_temp}℃",
            "适宜温度范围": f"{suitable_temp[0]}-{suitable_temp[1]}℃",
            "适宜性": suitability.value,
            "需水特性": params["需水量"],
            "光照需求": params["光照需求"],
            "生长周期": params["生长周期"],
            "种植建议": details,
            "风险提示": warnings,
            "管理要点": [
                "选择适宜品种",
                "合理密植",
                "科学施肥",
                "及时灌溉",
                "病虫害防治"
            ]
        }
    
    def judge_fruit_tree_management(
        self,
        weather_data: AgriculturalWeatherData,
        crop_type: CropType,
        growth_stage: str = "休眠期"
    ) -> dict:
        """
        果树管理决策
        
        Args:
            weather_data: 农业气象数据
            crop_type: 果树类型
            growth_stage: 生长阶段
        
        Returns:
            管理建议
        """
        fruit_params = {
            "苹果": {
                "适宜温度": (7, 14),
                "需冷量": 1200,
                "花期临界温度": -1.7,
                "采收期": "9-10月"
            },
            "梨": {
                "适宜温度": (7, 15),
                "需冷量": 1000,
                "花期临界温度": -1.7,
                "采收期": "8-9月"
            },
            "桃": {
                "适宜温度": (10, 15),
                "需冷量": 800,
                "花期临界温度": -1.1,
                "采收期": "7-8月"
            },
            "葡萄": {
                "适宜温度": (12, 18),
                "需冷量": 0,
                "花期临界温度": 0,
                "采收期": "8-9月"
            },
            "柑橘": {
                "适宜温度": (15, 22),
                "需冷量": 0,
                "花期临界温度": -5,
                "采收期": "10-12月"
            }
        }
        
        crop_name = crop_type.value
        params = fruit_params.get(crop_name, fruit_params["苹果"])
        
        current_temp = weather_data.base_weather.temperature
        current_month = datetime.now().month
        
        stage_management = {
            "休眠期": {
                "管理要点": ["冬季修剪", "清园", "涂白防寒"],
                "温度要求": "需低温打破休眠"
            },
            "萌芽期": {
                "管理要点": ["追施氮肥", "花前复剪", "防治病虫害"],
                "温度要求": "日平均气温稳定通过5℃"
            },
            "开花期": {
                "管理要点": ["疏花", "人工授粉", "防霜冻"],
                "温度要求": "花期适温15-20℃"
            },
            "果实发育期": {
                "管理要点": ["疏果定果", "套袋", "追肥浇水"],
                "温度要求": "果实膨大期需充足热量"
            },
            "成熟期": {
                "管理要点": ["分批采收", "采后处理", "分级包装"],
                "温度要求": "采收期天气晴朗"
            }
        }
        
        warnings = []
        if growth_stage == "开花期":
            critical_temp = params["花期临界温度"]
            if current_temp < critical_temp + 2:
                warnings.append(f"当前温度接近花期临界温度{critical_temp}℃，注意防霜冻")
        
        stage_info = stage_management.get(growth_stage, stage_management["休眠期"])
        
        return {
            "果树类型": crop_name,
            "生长阶段": growth_stage,
            "当前温度": f"{current_temp}℃",
            "适宜温度范围": f"{params['适宜温度'][0]}-{params['适宜温度'][1]}℃",
            "采收期": params["采收期"],
            "管理要点": stage_info["管理要点"],
            "温度要求": stage_info["温度要求"],
            "风险提示": warnings,
            "病虫害防治": [
                "清园消毒",
                "定期喷药",
                "加强监测",
                "及时处理"
            ]
        }
    
    def judge_flower_care(
        self,
        weather_data: AgriculturalWeatherData,
        crop_type: CropType,
        season: str = "春季"
    ) -> dict:
        """
        花卉养护决策
        
        Args:
            weather_data: 农业气象数据
            crop_type: 花卉类型
            season: 季节
        
        Returns:
            养护建议
        """
        flower_params = {
            "月季": {
                "适宜温度": (18, 26),
                "光照需求": "强光",
                "需水特性": "中等",
                "花期": "5-11月"
            },
            "菊花": {
                "适宜温度": (15, 25),
                "光照需求": "短日照",
                "需水特性": "中等",
                "花期": "10-12月"
            },
            "百合": {
                "适宜温度": (15, 25),
                "光照需求": "中等",
                "需水特性": "中等",
                "花期": "5-7月"
            },
            "兰花": {
                "适宜温度": (18, 28),
                "光照需求": "半阴",
                "需水特性": "中等",
                "花期": "品种不同花期不同"
            },
            "多肉植物": {
                "适宜温度": (15, 28),
                "光照需求": "强光",
                "需水特性": "耐旱",
                "花期": "品种不同花期不同"
            }
        }
        
        crop_name = crop_type.value
        params = flower_params.get(crop_name, flower_params["月季"])
        
        current_temp = weather_data.base_weather.temperature
        current_humidity = weather_data.base_weather.humidity
        suitable_temp = params["适宜温度"]
        
        suitability = RiskLevel.LOW
        warnings = []
        details = []
        
        if current_temp < suitable_temp[0]:
            suitability = RiskLevel.MEDIUM
            warnings.append(f"当前温度{current_temp}℃偏低，注意保温")
        elif current_temp > suitable_temp[1]:
            suitability = RiskLevel.MEDIUM
            warnings.append(f"当前温度{current_temp}℃偏高，注意遮阳通风")
        else:
            details.append(f"当前温度{current_temp}℃适宜")
        
        if params["光照需求"] == "半阴" and weather_data.base_weather.sunshine_hours > 8:
            warnings.append("光照过强，需要遮阳")
        
        season_care = {
            "春季": ["换盆分株", "追施氮肥", "增加浇水"],
            "夏季": ["遮阳降温", "早晚浇水", "防治病虫害"],
            "秋季": ["追施磷钾肥", "减少浇水", "促进花芽分化"],
            "冬季": ["保温防寒", "减少浇水", "停止施肥"]
        }
        
        return {
            "花卉类型": crop_name,
            "当前季节": season,
            "当前温度": f"{current_temp}℃",
            "适宜温度范围": f"{suitable_temp[0]}-{suitable_temp[1]}℃",
            "当前湿度": f"{current_humidity}%",
            "适宜性": suitability.value,
            "光照需求": params["光照需求"],
            "需水特性": params["需水特性"],
            "花期": params["花期"],
            "季节养护要点": season_care.get(season, season_care["春季"]),
            "养护建议": details,
            "风险提示": warnings
        }
    
    def assess_greenhouse_environment(
        self,
        weather_data: AgriculturalWeatherData,
        crop_type: CropType,
        greenhouse_type: str = "塑料大棚"
    ) -> dict:
        """
        保护地环境评估
        
        Args:
            weather_data: 农业气象数据
            crop_type: 作物类型
            greenhouse_type: 保护地类型
        
        Returns:
            环境评估结果
        """
        current_temp = weather_data.base_weather.temperature
        current_humidity = weather_data.base_weather.humidity
        sunshine_hours = weather_data.base_weather.sunshine_hours
        
        greenhouse_params = {
            "塑料大棚": {
                "保温性能": "中等",
                "透光率": 0.85,
                "适宜作物": ["蔬菜", "花卉"]
            },
            "日光温室": {
                "保温性能": "良好",
                "透光率": 0.75,
                "适宜作物": ["蔬菜", "果树", "花卉"]
            },
            "连栋温室": {
                "保温性能": "优秀",
                "透光率": 0.90,
                "适宜作物": ["蔬菜", "果树", "花卉", "育苗"]
            }
        }
        
        params = greenhouse_params.get(greenhouse_type, greenhouse_params["塑料大棚"])
        
        warnings = []
        recommendations = []
        
        ideal_temp_range = (20, 28)
        ideal_humidity_range = (60, 80)
        
        if current_temp < ideal_temp_range[0]:
            warnings.append(f"棚内温度{current_temp}℃偏低，需要保温")
            recommendations.append("覆盖保温被")
            recommendations.append("减少通风")
        elif current_temp > ideal_temp_range[1]:
            warnings.append(f"棚内温度{current_temp}℃偏高，需要降温")
            recommendations.append("加强通风")
            recommendations.append("遮阳网覆盖")
        
        if current_humidity > ideal_humidity_range[1]:
            warnings.append(f"棚内湿度{current_humidity}%偏高，易发病害")
            recommendations.append("加强通风排湿")
            recommendations.append("控制浇水")
            recommendations.append("地膜覆盖")
        
        if sunshine_hours < 4:
            warnings.append("光照不足，影响光合作用")
            recommendations.append("保持棚膜清洁")
            recommendations.append("必要时补光")
        
        return {
            "保护地类型": greenhouse_type,
            "保温性能": params["保温性能"],
            "透光率": f"{params['透光率']*100}%",
            "适宜作物类型": params["适宜作物"],
            "当前作物": crop_type.value,
            "环境温度": f"{current_temp}℃",
            "理想温度范围": f"{ideal_temp_range[0]}-{ideal_temp_range[1]}℃",
            "环境湿度": f"{current_humidity}%",
            "理想湿度范围": f"{ideal_humidity_range[0]}-{ideal_humidity_range[1]}%",
            "日照时数": f"{sunshine_hours}小时",
            "环境评估": warnings if warnings else ["环境条件适宜"],
            "调控建议": recommendations if recommendations else ["保持当前管理"],
            "日常管理": [
                "早晚揭盖保温被",
                "适时通风换气",
                "保持棚膜清洁",
                "科学浇水施肥",
                "病虫害综合防治"
            ]
        }

