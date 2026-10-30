# -*- coding: utf-8 -*-
"""
气象数据处理模块
负责气象数据获取、处理和农业指标计算

修复点：
1. 模拟数据不再全恒定：加入昼夜温度正弦变化、湿度反相关、随机降水事件、
   按季节的日照时长、随机风向，使预警/适宜度判断真实可触发
2. 修复真实API解析：max/min 不再都用 t2m（导致 ET0=(max-min)^0.5=0），
   缺失时用 t2m±温差估计
3. 同步 requests 改为 asyncio.to_thread 异步执行，避免阻塞事件循环
4. 返回数据统一按时间升序排序
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict
import asyncio
import math
import random
import requests
from src.models import (
    WeatherData, AgriculturalWeatherData,
    Location, CropType
)
from config.settings import WEATHER_THRESHOLDS

# 中科天机 API 以 tz=8（东八区）返回时间戳（实测 "2026-10-14T09:00+08:00"）。
# 窗口比较统一归一到东八区，避免容器时区（通常为 UTC）下 naive/aware 比较异常与"当前时刻"错位。
CST = timezone(timedelta(hours=8))


def _as_cst(dt: Optional[datetime]) -> Optional[datetime]:
    """把任意 datetime 归一到东八区；naive 值按东八区本地时间理解。"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=CST)
    return dt.astimezone(CST)


class WeatherProcessor:
    """气象数据处理器"""

    def __init__(self, api_key: str = None, api_url: str = None, subscription_id: str = None):
        self.api_key = api_key
        # 中科天机气象预测API的正确URL（官方示例）
        self.api_url = api_url or "https://api.tjweather.com/v2"
        self.subscription_id = subscription_id
        # 数据来源标记：'api' 真实 / 'mock' 模拟 / 'none' 无数据（供前端提示）
        self.last_source = "none"

    async def fetch_weather_data(
        self,
        location: Location,
        start_time: datetime,
        end_time: datetime,
        granularity: str = "hourly"
    ) -> List[WeatherData]:
        """
        获取气象数据（对接中科天机气象预测API）

        Args:
            location: 地理位置信息
            start_time: 开始时间
            end_time: 结束时间
            granularity: 时间粒度（hourly/daily）

        Returns:
            气象数据列表（按时间升序）
        """
        if not self.api_key or not self.subscription_id:
            print("警告: 未配置气象API密钥，返回模拟数据")
            self.last_source = "mock"
            return self._trim_past_samples(
                self._get_mock_weather_data(location, start_time, end_time)
            )

        try:
            lat = location.latitude or 34.75
            lon = location.longitude or 113.65

            params = {
                "key": self.api_key,
                "subscriptionId": self.subscription_id,
                "loc": f"{lon},{lat}",
                "fields": "ws10m,t2m,rh2m,psz,tp",  # 移除wd10m（风向），因为订阅未授权
                "t_res": "1h" if granularity == "hourly" else "1d",
                "fcst_days": "7",
                "fcst_hours": "0",
                "tz": "8"  # 北京时区（东八区）
            }

            # 同步 requests 放入线程池，避免阻塞事件循环
            response = await asyncio.to_thread(
                requests.get, self.api_url, params, timeout=10
            )

            if response.ok:
                data = response.json()
                # 先乐观标记为真实数据；_parse_weather_response 内部回退模拟数据时会改回 "mock"
                self.last_source = "api"
                weather_list = self._parse_weather_response(data, start_time, end_time)
                if not weather_list:
                    self.last_source = "mock"
            else:
                print(f"气象API请求失败: {response.status_code} {response.reason}")
                self.last_source = "mock"
                weather_list = self._get_mock_weather_data(location, start_time, end_time)

        except requests.exceptions.RequestException as e:
            print(f"气象API请求异常: {e}")
            self.last_source = "mock"
            weather_list = self._get_mock_weather_data(location, start_time, end_time)

        # 裁掉"起报时刻 → 当前时刻"之间的历史时次（见 _trim_past_samples 注释）
        weather_list = self._trim_past_samples(weather_list)
        # 统一按时间升序
        weather_list.sort(key=lambda w: w.timestamp)
        return weather_list

    @staticmethod
    def _trim_past_samples(weather_list: List[WeatherData]) -> List[WeatherData]:
        """裁掉早于「当前小时（东八区）」的时次，保证首个样本就是当前时次。

        中科天机返回的是**从模式起报时刻开始**的整段序列，而不是请求窗口。实测
        time_init=2026-10-13T20:00+08:00 时，首条样本为 2026-10-13T21:00（比请求时刻早 12 小时）。
        不裁剪会连锁引发两类线上问题：
        1. 前端 `hourly[0]`（"当前温度/湿度"）落在昨天 → 首页大号温度显示的是昨夜气温；
        2. 前端按日聚合后 `daily7[0]` 是"昨天"，且昨天只剩 3 个时次（< 6）→ 农事适宜度全部
           返回 null → 首页"今日农事建议"永久卡在"气象数据加载中，稍后为你生成今日农事建议"。
        """
        if not weather_list:
            return weather_list
        cutoff = datetime.now(CST).replace(minute=0, second=0, microsecond=0)
        kept = [w for w in weather_list if (_as_cst(w.timestamp) or cutoff) >= cutoff]
        if not kept:
            print("警告: 气象数据全部早于当前时刻（起报时间过旧），保留原始序列")
            return weather_list
        return kept

    def _parse_weather_response(
        self,
        response_data: Dict,
        start_time: datetime,
        end_time: datetime
    ) -> List[WeatherData]:
        """解析API响应（修复 max/min 用 t2m 顶替导致的失真）"""
        weather_list = []

        try:
            data_list = response_data.get("data", {}).get("data", [])

            for item in data_list:
                t2m = float(item.get("t2m", 20))
                # 修复：max/min 优先取真实字段；缺失时用 t2m ± 温差估计（避免 (max-min)=0）
                tmax = item.get("tmax")
                tmin = item.get("tmin")
                max_temperature = float(tmax) if tmax is not None else t2m + 3.0
                min_temperature = float(tmin) if tmin is not None else t2m - 3.0

                weather = WeatherData(
                    timestamp=datetime.fromisoformat(item.get("time", datetime.now().isoformat())),
                    temperature=t2m,
                    max_temperature=max_temperature,
                    min_temperature=min_temperature,
                    humidity=float(item.get("rh2m", 60)),
                    precipitation=float(item.get("tp", 0)),
                    wind_speed=float(item.get("ws10m", 2.5)),
                    # 订阅未授权 wd10m：风向确实拿不到，留空即可。
                    # 不要写"未知"——前端会把它当成真实风向渲染成"未知 1.4级"。
                    wind_direction="",
                    sunshine_hours=float(item.get("ssd", 8.0)) if item.get("ssd") is not None else 8.0,
                    pressure=float(item.get("psz", 1013))
                )
                weather_list.append(weather)

        except Exception as e:
            print(f"解析气象数据异常: {e}")

        if not weather_list:
            # 解析失败/无有效样本 → 回退模拟数据，并如实标记来源（否则前端会把模拟数据当实时数据展示）
            self.last_source = "mock"
            weather_list = self._get_mock_weather_data(
                Location(province="", city=""), start_time, end_time
            )

        return weather_list

    def _wind_deg_to_direction(self, deg: float) -> str:
        """
        将风向角度转换为方向名称

        Args:
            deg: 风向角度（0-360度）

        Returns:
            风向名称（如"东北风"）
        """
        # 16方位风向
        directions = [
            "北风", "北东北风", "东北风", "东东北风",
            "东风", "东东南风", "东南风", "南东南风",
            "南风", "南西南风", "西南风", "西西南风",
            "西风", "西西北风", "西北风", "北西北风"
        ]

        # 将角度转换为索引（每个方向22.5度）
        index = int((deg + 11.25) / 22.5) % 16

        return directions[index]

    def process_to_agricultural_weather(
        self,
        weather_data: WeatherData,
        historical_weather: List[WeatherData],
        soil_moisture: float,
        crop_type: CropType,
        growth_stage: str
    ) -> AgriculturalWeatherData:
        """
        将气象数据转换为农业气象数据

        Args:
            weather_data: 当前气象数据
            historical_weather: 历史气象数据
            soil_moisture: 土壤湿度
            crop_type: 作物类型
            growth_stage: 生长阶段

        Returns:
            农业气象数据
        """
        # 计算累积温度
        accumulated_temp = sum([w.temperature for w in historical_weather]) if historical_weather else 0

        # 计算有效降水
        effective_precipitation = sum([w.precipitation for w in historical_weather]) if historical_weather else 0

        # 计算参考蒸散量（简化计算；max-min 已修复为非零，避免蒸散量恒为0）
        temp_range = max(weather_data.max_temperature - weather_data.min_temperature, 1.0)
        et0 = 0.0023 * (weather_data.temperature + 17.8) * (temp_range ** 0.5) * weather_data.sunshine_hours

        # 计算作物蒸散量（简化，使用作物系数0.8）
        etc = et0 * 0.8

        # 计算水分亏缺
        water_deficit = max(0, etc - effective_precipitation - soil_moisture * 0.1)

        # 判断灌溉需求
        irrigation_needed = water_deficit > 10 or soil_moisture < 60

        # 判断施肥适宜性
        fertilization_suitable = (
            15 <= weather_data.temperature <= 30 and
            weather_data.precipitation < 10 and
            soil_moisture >= 40
        )

        # 判断病虫害风险
        disease_risk = (
            weather_data.humidity > 80 and
            20 <= weather_data.temperature <= 30
        )

        # 计算活动积温（日平均温度>10°C的累积）
        active_accumulated_temp = sum([
            max(0, w.temperature - 10) for w in historical_weather
        ]) if historical_weather else max(0, weather_data.temperature - 10)

        # 计算有效积温（日平均温度>0°C的累积）
        effective_accumulated_temp = sum([
            max(0, w.temperature) for w in historical_weather
        ]) if historical_weather else max(0, weather_data.temperature)

        # 计算降水距平（与常年平均的偏差，简化计算）
        normal_precipitation = 100  # 常年平均降水量（mm）
        precipitation_anomaly = effective_precipitation - normal_precipitation

        # 计算灌溉需求指数（0-1）
        irrigation_demand_index = min(1.0, max(0.0, water_deficit / 50))

        # 计算灾害胁迫指数（0-1）
        disaster_stress_index = 0.0
        if weather_data.temperature > 35:
            disaster_stress_index += 0.3  # 高温胁迫
        if weather_data.temperature < 5:
            disaster_stress_index += 0.3  # 低温胁迫
        if weather_data.humidity > 85:
            disaster_stress_index += 0.2  # 高湿胁迫
        if effective_precipitation > 50:
            disaster_stress_index += 0.2  # 涝害

        # 计算晾晒指数（0-1，越高越适合晾晒）
        drying_index = 0.0
        if weather_data.humidity < 60 and weather_data.precipitation == 0:
            drying_index = min(1.0, (60 - weather_data.humidity) / 60 + weather_data.sunshine_hours / 12)

        # 构建农业气象数据
        agri_weather = AgriculturalWeatherData(
            base_weather=weather_data,
            active_accumulated_temperature=active_accumulated_temp,
            effective_accumulated_temperature=effective_accumulated_temp,
            precipitation_anomaly=precipitation_anomaly,
            drought_index=None,  # 可选字段
            irrigation_demand_index=irrigation_demand_index,
            disaster_stress_index=disaster_stress_index,
            drying_index=drying_index
        )

        return agri_weather

    def _get_mock_weather_data(
        self,
        location: Location,
        start_time: datetime,
        end_time: datetime
    ) -> List[WeatherData]:
        """
        生成模拟气象数据（带昼夜/季节变化，非恒定值）

        修复点：
        - 温度随昼夜正弦变化 + 月份季节基线，不再恒 25°C
        - 湿度与温度反相关
        - 降水为低频随机事件（能让预警/灌溉判断真实触发）
        - 日照按季节与昼长
        - 风向随机
        """
        weather_list = []
        current_time = start_time

        # 依据纬度粗估年基线（中纬度大陆性，简化为月份修正）
        month = start_time.month
        # 季节基线：7月最高(~28)，1月最低(~-2)，用余弦近似
        # 公式：month=7 → cos(0)=1 → 峰值；month=1 → cos(-π)=-1 → 谷值
        seasonal_base = 13.0 + 15.0 * math.cos(2 * math.pi * (month - 7) / 12.0)

        # 随机降水：低频事件（避免每天都一样）
        rain_events = []
        n_hours = max(int((end_time - start_time).total_seconds() // 3600), 1)
        for _ in range(max(n_hours // 48, 0)):
            # 每 48h 有一次 60% 概率的降水过程，持续若干小时
            if random.random() < 0.6:
                start_h = random.randint(0, n_hours - 6)
                dur = random.randint(2, 6)
                rain_events.append((start_h, dur, random.uniform(0.5, 3.0)))

        _wind_dirs = ["北风", "东北风", "东风", "东南风", "南风", "西南风", "西风", "西北风"]

        idx = 0
        while current_time <= end_time:
            hour = current_time.hour

            # 昼夜温度曲线：最低在凌晨5点，最高在下午14点
            diurnal = 6.0 * math.sin(2 * math.pi * (hour - 5) / 24.0)
            # 叠加轻微的逐时随机扰动，避免过于平滑
            noise = random.uniform(-1.0, 1.0)
            temperature = round(seasonal_base + diurnal + noise, 1)

            # 湿度与温度反相关，附加随机扰动
            humidity = round(max(30.0, min(98.0, 85.0 - 1.2 * diurnal + random.uniform(-8, 8))), 1)

            # 降水：命中事件窗口则产生降水
            precipitation = 0.0
            for (sh, dur, rate) in rain_events:
                if sh <= idx < sh + dur:
                    precipitation = round(rate * random.uniform(0.4, 1.6), 1)
                    break

            # 日照：仅白天，随昼长（夏季长冬季短）
            day_start, day_end = 7, 19
            if 4 <= month <= 5 or 9 <= month <= 10:
                day_start, day_end = 6, 19
            elif 6 <= month <= 8:
                day_start, day_end = 5, 20
            elif 11 <= month <= 12 or 1 <= month <= 2:
                day_start, day_end = 7, 18
            if day_start <= hour <= day_end and precipitation == 0:
                sunshine_hours = round(random.uniform(6.0, 12.0), 1)
            else:
                sunshine_hours = 0.0

            weather = WeatherData(
                timestamp=current_time,
                temperature=temperature,
                max_temperature=round(temperature + 3.0, 1),
                min_temperature=round(temperature - 3.0, 1),
                humidity=humidity,
                precipitation=precipitation,
                wind_speed=round(random.uniform(1.0, 8.0), 1),
                wind_direction=random.choice(_wind_dirs),
                sunshine_hours=sunshine_hours,
                pressure=round(random.uniform(1005.0, 1025.0), 1)
            )
            weather_list.append(weather)

            current_time += timedelta(hours=1)
            idx += 1

        return weather_list
