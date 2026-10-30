# -*- coding: utf-8 -*-
"""农场数据 SQLite 持久化：包装 farm_core.FarmManager，写操作落库、启动恢复。

纵深防御：每个 PersistentFarmManager 绑定一个 user_id，所有读写都按 user_id 过滤
（磁盘级已按 data/users/{user_id}/agri_weather.db 隔离，这里再叠加行级约束）。
即使 db_path 指向错误的文件、或未来合并为单库，也不会发生跨用户数据串读/串写。
"""
import json
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

from src.ui.farm_core import FarmManager, FarmField
from config.settings import settings

logger = logging.getLogger("agri-backend.farm_persistence")

# 未显式传入 user_id 时的兜底归属（兼容旧的全局单例路径）
_LEGACY_USER_ID = "__legacy__"


class PersistentFarmManager(FarmManager):
    """带 SQLite 持久化的农场管理器（不改原业务逻辑，叠加 user_id 隔离）"""

    def __init__(self, db_path: str = None, user_id: str = None):
        super().__init__()
        self.user_id = str(user_id) if user_id is not None else _LEGACY_USER_ID
        self.db_path = Path(db_path or settings.DATABASE_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()
        self._load_all()

    def _init_tables(self):
        conn = sqlite3.connect(self.db_path)
        try:
            self._ensure_fields_table(conn)
            self._ensure_location_table(conn)
            conn.commit()
        finally:
            conn.close()

    def _ensure_fields_table(self, conn):
        cols = {r[1] for r in conn.execute("PRAGMA table_info(api_farm_fields)").fetchall()}
        if not cols:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS api_farm_fields (
                    user_id TEXT NOT NULL DEFAULT '',
                    field_id TEXT NOT NULL,
                    data TEXT NOT NULL,
                    updated_at TIMESTAMP,
                    PRIMARY KEY (user_id, field_id)
                )
                """
            )
        elif "user_id" not in cols:
            # 兼容升级：旧表无 user_id，补列并把既有行归属到当前管理器用户
            conn.execute(
                "ALTER TABLE api_farm_fields ADD COLUMN user_id TEXT NOT NULL DEFAULT ''"
            )
            conn.execute(
                "UPDATE api_farm_fields SET user_id = ? WHERE user_id = ''",
                (self.user_id,),
            )

    def _ensure_location_table(self, conn):
        cols = {r[1] for r in conn.execute("PRAGMA table_info(api_farm_location)").fetchall()}
        if not cols:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS api_farm_location (
                    user_id TEXT NOT NULL DEFAULT '',
                    id INTEGER NOT NULL,
                    data TEXT NOT NULL,
                    PRIMARY KEY (user_id, id),
                    CHECK (id = 1)
                )
                """
            )
        elif "user_id" not in cols:
            conn.execute(
                "ALTER TABLE api_farm_location ADD COLUMN user_id TEXT NOT NULL DEFAULT ''"
            )
            conn.execute(
                "UPDATE api_farm_location SET user_id = ? WHERE user_id = ''",
                (self.user_id,),
            )

    # ---------- 序列化 ----------

    @staticmethod
    def _field_to_dict(field: FarmField) -> Dict:
        return {
            "field_id": field.field_id,
            "name": field.name,
            "crop": field.crop,
            "stage": field.stage,
            "area": field.area,
            "location": field.location,
            "health": field.health,
            "water": field.water,
            "growth": field.growth,
            "is_empty": field.is_empty,
            "actions": field.actions,
            "created_at": field.created_at.isoformat(),
            "planted_at": field.planted_at.isoformat(),
            "last_updated": field.last_updated.isoformat(),
        }

    @staticmethod
    def _dict_to_field(d: Dict) -> FarmField:
        field = FarmField(
            d["field_id"], d["name"], d["crop"], d["stage"], d["area"], d.get("location", "")
        )
        field.health = d.get("health", 100)
        field.water = d.get("water", 70)
        field.growth = d.get("growth", 0)
        field.is_empty = d.get("is_empty", False)
        field.actions = d.get("actions", [])
        field.created_at = datetime.fromisoformat(d["created_at"]) if d.get("created_at") else datetime.now()
        field.planted_at = datetime.fromisoformat(d["planted_at"]) if d.get("planted_at") else datetime.now()
        field.last_updated = datetime.fromisoformat(d["last_updated"]) if d.get("last_updated") else datetime.now()
        return field

    # ---------- 读写库 ----------

    def _save_field(self, field: FarmField):
        try:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO api_farm_fields (user_id, field_id, data, updated_at) VALUES (?, ?, ?, ?)",
                    (self.user_id, field.field_id, json.dumps(self._field_to_dict(field), ensure_ascii=False), datetime.now().isoformat()),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"保存地块失败: {e}")

    def _delete_field_db(self, field_id: str):
        try:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute(
                    "DELETE FROM api_farm_fields WHERE user_id = ? AND field_id = ?",
                    (self.user_id, field_id),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"删除地块记录失败: {e}")

    def _load_all(self):
        try:
            conn = sqlite3.connect(self.db_path)
            try:
                rows = conn.execute(
                    "SELECT data FROM api_farm_fields WHERE user_id = ?", (self.user_id,)
                ).fetchall()
                loc_row = conn.execute(
                    "SELECT data FROM api_farm_location WHERE user_id = ? AND id = 1",
                    (self.user_id,),
                ).fetchone()
            finally:
                conn.close()
            for (data,) in rows:
                try:
                    field = self._dict_to_field(json.loads(data))
                    self.fields[field.field_id] = field
                except Exception as e:
                    logger.warning(f"恢复地块失败，跳过: {e}")
            if loc_row:
                self.user_location = json.loads(loc_row[0])
            logger.info(f"农场持久化恢复完成: {len(self.fields)} 个地块")
        except Exception as e:
            logger.error(f"农场数据加载失败: {e}")

    def _save_location(self):
        try:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO api_farm_location (user_id, id, data) VALUES (?, 1, ?)",
                    (self.user_id, json.dumps(self.user_location, ensure_ascii=False)),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"保存位置失败: {e}")

    # ---------- 覆写写操作，落库 ----------

    def set_location(self, province: str, city: str, district: str, lat: float, lon: float):
        super().set_location(province, city, district, lat, lon)
        self._save_location()

    def create_field(self, name: str, crop: str, stage: str, area: float) -> FarmField:
        field = super().create_field(name, crop, stage, area)
        self._save_field(field)
        return field

    def delete_field(self, field_id: str) -> bool:
        ok = super().delete_field(field_id)
        if ok:
            self._delete_field_db(field_id)
        return ok

    def harvest_field(self, field_id: str) -> Tuple[bool, str]:
        ok, msg = super().harvest_field(field_id)
        if ok:
            self._save_field(self.fields[field_id])
        return ok, msg

    def water_field(self, field_id: str) -> Tuple[bool, str]:
        ok, msg = super().water_field(field_id)
        if ok:
            self._save_field(self.fields[field_id])
        return ok, msg

    def fertilize_field(self, field_id: str) -> Tuple[bool, str]:
        ok, msg = super().fertilize_field(field_id)
        if ok:
            self._save_field(self.fields[field_id])
        return ok, msg
