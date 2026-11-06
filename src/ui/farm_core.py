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


# 其余作物用紧凑表补齐：每行 = (阶段名, 图标, 需水阈值, 是否需追肥)
# 与 config.settings.CROP_GROWTH_STAGES 的阶段序列保持一致（tests 会校验）。
_COMPACT_CROPS = {
    "大豆": ("🫘", 130, [
        ("播种期", "🌱", 60, False), ("出苗期", "🌿", 65, False),
        ("分枝期", "🌿", 75, True), ("开花期", "🌸", 80, True),
        ("结荚期", "🫛", 80, True), ("鼓粒期", "🫘", 75, False),
        ("成熟期", "🫘", 60, False),
    ]),
    "马铃薯": ("🥔", 100, [
        ("播种期", "🌱", 60, False), ("出苗期", "🌿", 70, False),
        ("块茎形成", "🥔", 75, True), ("块茎膨大", "🥔", 80, True),
        ("淀粉积累", "🥔", 70, False), ("成熟期", "🥔", 55, False),
    ]),
    "辣椒": ("🌶️", 120, [
        ("播种期", "🌱", 60, False), ("苗期", "🌿", 70, True),
        ("定植期", "🌿", 75, True), ("开花期", "🌸", 75, True),
        ("结果期", "🌶️", 80, True), ("成熟期", "🌶️", 65, False),
    ]),
    "白菜": ("🥬", 70, [
        ("播种期", "🌱", 60, False), ("出苗期", "🌿", 65, False),
        ("莲座期", "🥬", 75, True), ("结球期", "🥬", 80, True),
        ("成熟期", "🥬", 60, False),
    ]),
    "菠菜": ("🥬", 50, [
        ("播种期", "🌱", 60, False), ("出苗期", "🌿", 65, False),
        ("叶丛期", "🥬", 70, True), ("抽薹期", "🌱", 70, False),
        ("成熟期", "🥬", 55, False),
    ]),
    "胡萝卜": ("🥕", 100, [
        ("播种期", "🌱", 60, False), ("出苗期", "🌿", 65, False),
        ("叶丛期", "🌿", 70, True), ("肉质根膨大", "🥕", 75, True),
        ("成熟期", "🥕", 55, False),
    ]),
    "苹果": ("🍎", 180, [
        ("播种期", "🌱", 60, False), ("苗期", "🌿", 65, True),
        ("开花期", "🌸", 70, True), ("坐果期", "🍏", 70, True),
        ("果实膨大", "🍎", 75, True), ("成熟期", "🍎", 60, False),
    ]),
    "梨": ("🍐", 180, [
        ("播种期", "🌱", 60, False), ("苗期", "🌿", 65, True),
        ("开花期", "🌸", 70, True), ("坐果期", "🍐", 70, True),
        ("果实膨大", "🍐", 75, True), ("成熟期", "🍐", 60, False),
    ]),
    "桃": ("🍑", 160, [
        ("播种期", "🌱", 60, False), ("苗期", "🌿", 65, True),
        ("开花期", "🌸", 70, True), ("坐果期", "🍑", 70, True),
        ("果实膨大", "🍑", 75, True), ("成熟期", "🍑", 60, False),
    ]),
    "葡萄": ("🍇", 150, [
        ("播种期", "🌱", 60, False), ("萌芽期", "🌿", 65, False),
        ("开花期", "🌸", 70, True), ("坐果期", "🍇", 70, True),
        ("果实膨大", "🍇", 75, True), ("成熟期", "🍇", 60, False),
    ]),
    "柑橘": ("🍊", 210, [
        ("播种期", "🌱", 60, False), ("苗期", "🌿", 65, True),
        ("开花期", "🌸", 70, True), ("坐果期", "🍊", 70, True),
        ("果实膨大", "🍊", 75, True), ("成熟期", "🍊", 60, False),
    ]),
    "月季": ("🌹", 120, [
        ("播种期", "🌱", 60, False), ("苗期", "🌿", 70, True),
        ("分枝期", "🌿", 70, True), ("现蕾期", "✳️", 75, True),
        ("开花期", "🌹", 75, False), ("成熟期", "🌹", 60, False),
    ]),
    "菊花": ("🌼", 120, [
        ("播种期", "🌱", 60, False), ("苗期", "🌿", 70, True),
        ("分枝期", "🌿", 70, True), ("现蕾期", "✳️", 75, True),
        ("开花期", "🌼", 75, False), ("成熟期", "🌼", 60, False),
    ]),
    "百合": ("🌷", 100, [
        ("播种期", "🌱", 60, False), ("出苗期", "🌿", 70, False),
        ("现蕾期", "✳️", 75, True), ("开花期", "🌷", 75, False),
        ("成熟期", "🌷", 60, False),
    ]),
    "兰花": ("🌸", 200, [
        ("播种期", "🌱", 60, False), ("苗期", "🌿", 65, True),
        ("新芽期", "🌿", 70, True), ("开花期", "🌸", 70, False),
        ("成熟期", "🌸", 60, False),
    ]),
    "多肉植物": ("🪴", 120, [
        ("播种期", "🌱", 55, False), ("幼苗期", "🌿", 60, False),
        ("生长期", "🪴", 65, True), ("上色期", "🪴", 60, False),
        ("成熟期", "🪴", 50, False),
    ]),
}

for _crop_name, (_emoji, _duration, _rows) in _COMPACT_CROPS.items():
    CROP_CONFIG[_crop_name] = {
        "emoji": _emoji,
        "duration": _duration,
        "stages": [row[0] for row in _rows],
        "stage_icons": {row[0]: row[1] for row in _rows},
        "water_needs": {row[0]: row[2] for row in _rows},
        "fertilizer_needs": {row[0]: row[3] for row in _rows},
    }
del _COMPACT_CROPS, _crop_name, _emoji, _duration, _rows


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
        location: str,
        planted_at: Optional[datetime] = None
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
        # 播种日期决定物候推演的起点，必须由用户指定而非默认"今天"
        self.planted_at = planted_at or datetime.now()
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
            "planted_at": self.planted_at.isoformat(timespec="seconds"),
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
        area: float,
        planted_at: Optional[datetime] = None
    ) -> FarmField:
        """创建新地块"""
        field_id = f"field_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self.fields)}"
        
        location = f"{self.user_location['province']}{self.user_location['city']}{self.user_location['district']}"
        
        field = FarmField(field_id, name, crop, stage, area, location, planted_at=planted_at)
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
        stages = config.get("stages") or []
        if not stages:
            return False, f"「{field.crop}」缺少物候配置，暂时无法判断是否成熟"

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
    
# 全局农场管理器
farm_manager = FarmManager()
