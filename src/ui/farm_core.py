# -*- coding: utf-8 -*-
"""
QQ农场风格界面 - 完整版
支持地块管理、作物生长模拟、气象智能提示
"""
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple
import random
import json


# ==================== 作物配置 ====================

CROP_CONFIG = {
    "黄瓜": {
        "emoji": "🥒",
        "duration": 90,
        "stages": ["播种期", "苗期", "伸蔓期", "开花期", "结果期", "成熟期"],
        "stage_icons": {
            "播种期": "🌱",      # 种子
            "苗期": "🌿",        # 幼苗
            "伸蔓期": "🥒",      # 藤蔓
            "开花期": "🌸",      # 开花
            "结果期": "🥒",      # 小瓜
            "成熟期": "🥒"       # 成熟瓜
        },
        "stage_descriptions": {
            "播种期": "种子播种育苗，等待发芽",
            "苗期": "培育壮苗，长出真叶",
            "伸蔓期": "藤蔓生长，攀爬支架",
            "开花期": "雌雄花开放，准备授粉",
            "结果期": "瓜条生长膨大",
            "成熟期": "瓜条饱满，可以采摘"
        },
        "water_needs": {"播种期": 60, "苗期": 70, "伸蔓期": 80, "开花期": 75, "结果期": 85, "成熟期": 70},
        "fertilizer_needs": {"播种期": False, "苗期": True, "伸蔓期": True, "开花期": True, "结果期": True, "成熟期": False}
    },
    "番茄": {
        "emoji": "🍅",
        "duration": 120,
        "stages": ["播种期", "苗期", "定植期", "开花期", "结果期", "成熟期"],
        "stage_icons": {
            "播种期": "🌱",
            "苗期": "🌿",
            "定植期": "🌿",
            "开花期": "🌸",
            "结果期": "🍏",
            "成熟期": "🍅"
        },
        "stage_descriptions": {
            "播种期": "种子播种育苗",
            "苗期": "培育壮苗，长出真叶",
            "定植期": "移栽到大田",
            "开花期": "花朵开放，准备结果",
            "结果期": "果实生长膨大",
            "成熟期": "果实变红，可以采摘"
        },
        "water_needs": {"播种期": 60, "苗期": 70, "定植期": 80, "开花期": 75, "结果期": 80, "成熟期": 65},
        "fertilizer_needs": {"播种期": False, "苗期": True, "定植期": True, "开花期": True, "结果期": True, "成熟期": False}
    },
    "玉米": {
        "emoji": "🌽",
        "duration": 120,
        "stages": ["播种期", "出苗期", "三叶期", "拔节期", "抽雄期", "吐丝期", "灌浆期", "成熟期"],
        "stage_icons": {
            "播种期": "🌱",
            "出苗期": "🌿",
            "三叶期": "🌿",
            "拔节期": "🌾",
            "抽雄期": "🌾",
            "吐丝期": "🌾",
            "灌浆期": "🌽",
            "成熟期": "🌽"
        },
        "stage_descriptions": {
            "播种期": "种子播入土壤，等待发芽",
            "出苗期": "幼苗破土而出，展现第一片真叶",
            "三叶期": "长出3片叶子，开始光合作用",
            "拔节期": "茎秆快速生长，节间伸长",
            "抽雄期": "雄穗抽出，准备授粉",
            "吐丝期": "雌穗吐丝，接受花粉",
            "灌浆期": "籽粒充实，积累干物质",
            "成熟期": "籽粒变硬，准备收获"
        },
        "water_needs": {"播种期": 60, "出苗期": 65, "三叶期": 70, "拔节期": 80, "抽雄期": 85, "吐丝期": 80, "灌浆期": 75, "成熟期": 60},
        "fertilizer_needs": {"播种期": False, "出苗期": False, "三叶期": True, "拔节期": True, "抽雄期": True, "吐丝期": False, "灌浆期": True, "成熟期": False}
    },
    "莜麦": {
        "emoji": "🌾",
        "duration": 100,
        "stages": ["播种期", "出苗期", "分蘖期", "拔节期", "抽穗期", "开花期", "灌浆期", "成熟期"],
        "stage_icons": {
            "播种期": "🌱",
            "出苗期": "🌿",
            "分蘖期": "🌿",
            "拔节期": "🌾",
            "抽穗期": "🌾",
            "开花期": "🌾",
            "灌浆期": "🌾",
            "成熟期": "🌾"
        },
        "stage_descriptions": {
            "播种期": "种子播入土壤",
            "出苗期": "幼苗出土",
            "分蘖期": "产生分枝",
            "拔节期": "茎秆伸长",
            "抽穗期": "麦穗抽出",
            "开花期": "花朵开放",
            "灌浆期": "籽粒充实",
            "成熟期": "麦粒饱满"
        },
        "water_needs": {"播种期": 55, "出苗期": 60, "分蘖期": 70, "拔节期": 75, "抽穗期": 70, "开花期": 65, "灌浆期": 60, "成熟期": 50},
        "fertilizer_needs": {"播种期": False, "出苗期": False, "分蘖期": True, "拔节期": True, "抽穗期": True, "开花期": False, "灌浆期": False, "成熟期": False}
    },
    "小麦": {
        "emoji": "🌾",
        "duration": 240,
        "stages": ["播种期", "出苗期", "分蘖期", "越冬期", "返青期", "拔节期", "抽穗期", "开花期", "灌浆期", "成熟期"],
        "stage_icons": {
            "播种期": "🌱", "出苗期": "🌿", "分蘖期": "🌿", "越冬期": "❄️",
            "返青期": "🌿", "拔节期": "🌾", "抽穗期": "🌾", "开花期": "🌾",
            "灌浆期": "🌾", "成熟期": "🌾"
        },
        "stage_descriptions": {
            "播种期": "种子播入土壤，等待发芽",
            "出苗期": "幼苗出土，展现绿色",
            "分蘖期": "产生分枝，增加穗数",
            "越冬期": "冬季休眠，积累养分",
            "返青期": "春季复苏，恢复生长",
            "拔节期": "茎秆伸长，快速生长",
            "抽穗期": "麦穗抽出，准备开花",
            "开花期": "花朵开放，完成授粉",
            "灌浆期": "籽粒充实，积累营养",
            "成熟期": "麦粒饱满，准备收获"
        },
        "water_needs": {"播种期": 55, "出苗期": 60, "分蘖期": 65, "越冬期": 50, "返青期": 70, "拔节期": 80, "抽穗期": 75, "开花期": 70, "灌浆期": 65, "成熟期": 55},
        "fertilizer_needs": {"播种期": False, "出苗期": False, "分蘖期": True, "越冬期": False, "返青期": True, "拔节期": True, "抽穗期": True, "开花期": False, "灌浆期": False, "成熟期": False}
    },
    "水稻": {
        "emoji": "🌾",
        "duration": 150,
        "stages": ["播种期", "秧苗期", "分蘖期", "拔节期", "孕穗期", "抽穗期", "开花期", "灌浆期", "成熟期"],
        "stage_icons": {
            "播种期": "🌱", "秧苗期": "🌿", "分蘖期": "🌿", "拔节期": "🌾",
            "孕穗期": "🌾", "抽穗期": "🌾", "开花期": "🌾", "灌浆期": "🌾", "成熟期": "🌾"
        },
        "stage_descriptions": {
            "播种期": "种子播入秧田",
            "秧苗期": "培育壮秧，准备移栽",
            "分蘖期": "产生分枝，形成有效穗",
            "拔节期": "茎秆伸长，幼穗分化",
            "孕穗期": "幼穗发育，准备抽穗",
            "抽穗期": "稻穗抽出，准备开花",
            "开花期": "花朵开放，完成授粉",
            "灌浆期": "籽粒充实，积累营养",
            "成熟期": "稻谷饱满，准备收获"
        },
        "water_needs": {"播种期": 70, "秧苗期": 80, "分蘖期": 85, "拔节期": 90, "孕穗期": 85, "抽穗期": 80, "开花期": 75, "灌浆期": 70, "成熟期": 60},
        "fertilizer_needs": {"播种期": False, "秧苗期": True, "分蘖期": True, "拔节期": True, "孕穗期": True, "抽穗期": False, "开花期": False, "灌浆期": False, "成熟期": False}
    }
}


# ==================== 地块类 ====================

class FarmField:
    """地块类"""
    
    def __init__(
        self,
        field_id: str,
        name: str,
        crop: str,
        stage: str,
        area: float,
        location: str
    ):
        self.field_id = field_id
        self.name = name
        self.crop = crop
        self.stage = stage
        self.area = area
        self.location = location
        
        # 状态属性
        self.health = 100      # 健康度 0-100
        self.water = 70        # 水分 0-100
        self.growth = 0        # 当前阶段生长进度 0-100
        self.is_empty = False  # 是否为空地
        
        # 时间记录
        self.created_at = datetime.now()
        self.planted_at = datetime.now()
        self.last_updated = datetime.now()
        
        # 操作记录
        self.actions = []
    
    def add_action(self, action: str):
        """添加操作记录"""
        self.actions.append({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "action": action
        })
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        config = CROP_CONFIG.get(self.crop, {})
        return {
            "field_id": self.field_id,
            "name": self.name,
            "crop": self.crop,
            "stage": self.stage,
            "area": self.area,
            "location": self.location,
            "health": self.health,
            "water": self.water,
            "growth": self.growth,
            "is_empty": self.is_empty,
            "emoji": config.get("emoji", "🌱"),
            "stage_icon": config.get("stage_icons", {}).get(self.stage, "🌱"),
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M"),
            "last_updated": self.last_updated.strftime("%Y-%m-%d %H:%M")
        }


# ==================== 农场管理器 ====================

class FarmManager:
    """农场管理器"""
    
    def __init__(self):
        self.fields: Dict[str, FarmField] = {}
        self.user_location = {"province": "", "city": "", "district": "", "lat": 0, "lon": 0}
    
    def set_location(self, province: str, city: str, district: str, lat: float, lon: float):
        """设置用户位置"""
        self.user_location = {
            "province": province,
            "city": city,
            "district": district,
            "lat": lat,
            "lon": lon
        }
    
    def create_field(
        self,
        name: str,
        crop: str,
        stage: str,
        area: float
    ) -> FarmField:
        """创建新地块"""
        field_id = f"field_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self.fields)}"
        
        location = f"{self.user_location['province']}{self.user_location['city']}{self.user_location['district']}"
        
        field = FarmField(field_id, name, crop, stage, area, location)
        field.add_action(f"创建地块，种植{crop}，当前阶段：{stage}")
        
        self.fields[field_id] = field
        return field
    
    def get_field(self, field_id: str) -> Optional[FarmField]:
        """获取地块"""
        return self.fields.get(field_id)
    
    def list_fields(self) -> List[FarmField]:
        """列出所有地块"""
        return list(self.fields.values())
    
    def delete_field(self, field_id: str) -> bool:
        """删除地块"""
        if field_id in self.fields:
            del self.fields[field_id]
            return True
        return False
    
    def harvest_field(self, field_id: str) -> Tuple[bool, str]:
        """收获地块"""
        field = self.fields.get(field_id)
        if not field:
            return False, "地块不存在"
        
        config = CROP_CONFIG.get(field.crop, {})
        stages = config.get("stages", [])
        
        if field.stage != stages[-1]:
            return False, f"作物还未成熟，当前阶段：{field.stage}"
        
        # 收获后变成空地
        field.is_empty = True
        field.add_action(f"收获{field.crop}")
        
        return True, f"成功收获{field.crop}！地块已清空，可以重新种植"
    
    def water_field(self, field_id: str) -> Tuple[bool, str]:
        """浇水"""
        field = self.fields.get(field_id)
        if not field:
            return False, "地块不存在"
        
        field.water = min(100, field.water + 30)
        field.health = min(100, field.health + 5)
        field.add_action("浇水")
        field.last_updated = datetime.now()
        
        return True, f"浇水成功！当前水分：{field.water}%"
    
    def fertilize_field(self, field_id: str) -> Tuple[bool, str]:
        """施肥"""
        field = self.fields.get(field_id)
        if not field:
            return False, "地块不存在"
        
        field.health = min(100, field.health + 10)
        field.growth = min(100, field.growth + 15)
        field.add_action("施肥")
        field.last_updated = datetime.now()
        
        return True, "施肥成功！促进作物生长"
    
    def simulate_weather_effect(self, field_id: str, weather: Dict) -> Dict:
        """模拟气象影响"""
        field = self.fields.get(field_id)
        if not field:
            return {"error": "地块不存在"}
        
        temp = weather.get("temperature", 25)
        humidity = weather.get("humidity", 60)
        precipitation = weather.get("precipitation", 0)
        
        # 水分变化
        if precipitation > 0:
            field.water = min(100, field.water + precipitation * 2)
        else:
            evaporation = max(0, (temp - 20) * 0.5)  # 温度越高蒸发越快
            field.water = max(0, field.water - evaporation)
        
        # 健康度变化
        config = CROP_CONFIG.get(field.crop, {})
        water_needs = config.get("water_needs", {}).get(field.stage, 70)
        
        if field.water < water_needs - 20:
            field.health = max(0, field.health - 5)
        elif field.water >= water_needs:
            field.health = min(100, field.health + 2)
        
        # 生长进度
        if 20 <= temp <= 30:
            field.growth = min(100, field.growth + 3)
        elif 15 <= temp < 20 or 30 < temp <= 35:
            field.growth = min(100, field.growth + 1.5)
        
        # 自动进入下一阶段
        if field.growth >= 100:
            stages = config.get("stages", [])
            if stages and field.stage in stages:
                current_idx = stages.index(field.stage)
                if current_idx < len(stages) - 1:
                    field.stage = stages[current_idx + 1]
                    field.growth = 0
                    field.add_action(f"进入{field.stage}")
        
        field.last_updated = datetime.now()
        
        return {
            "water": field.water,
            "health": field.health,
            "growth": field.growth,
            "stage": field.stage
        }
    
    def get_field_alerts(self, field_id: str, weather: Dict) -> List[str]:
        """获取地块预警信息"""
        field = self.fields.get(field_id)
        if not field or field.is_empty:
            return []
        
        alerts = []
        config = CROP_CONFIG.get(field.crop, {})
        
        # 水分预警
        water_needs = config.get("water_needs", {}).get(field.stage, 70)
        if field.water < water_needs - 15:
            alerts.append(f"💧 需要浇水（当前{field.water}%，需要{water_needs}%）")
        elif field.water < water_needs - 5:
            alerts.append(f"⚠️ 水分偏低（{field.water}%）")
        
        # 施肥提醒
        fertilizer_needs = config.get("fertilizer_needs", {}).get(field.stage, False)
        if fertilizer_needs and field.health < 80:
            alerts.append("🌱 建议施肥，增强作物营养")
        
        # 收获提醒
        stages = config.get("stages", [])
        if field.stage == stages[-1] and field.growth >= 80:
            alerts.append(f"🌾 {field.crop}已成熟，可以收获！")
        
        # 气象预警
        temp = weather.get("temperature", 25)
        if temp > 35:
            alerts.append("🌡️ 高温预警，注意遮阳降温")
        elif temp < 5:
            alerts.append("❄️ 低温预警，注意防寒保温")
        
        if weather.get("precipitation", 0) > 20:
            alerts.append("🌧️ 大雨将至，注意排水防涝")
        
        return alerts
    
    def get_all_alerts(self, weather: Dict) -> List[Dict]:
        """获取所有地块预警"""
        all_alerts = []
        for field in self.fields.values():
            alerts = self.get_field_alerts(field.field_id, weather)
            if alerts:
                all_alerts.append({
                    "field_name": field.name,
                    "crop": field.crop,
                    "alerts": alerts
                })
        return all_alerts


# 全局农场管理器
farm_manager = FarmManager()
