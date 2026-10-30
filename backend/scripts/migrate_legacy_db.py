# -*- coding: utf-8 -*-
"""一次性迁移脚本：把登录前「全局单库」 data/agri_weather.db 的数据迁移到指定用户子库。

背景：登录 + 每用户隔离上线前，农场/对话数据写在全局库（无 user_id 归属）。
上线后每个用户有独立子库 data/users/{user_id}/agri_weather.db。
本脚本把旧全局库数据归属到某个「legacy」用户子库，避免历史数据丢失。

特性：
- 幂等：重复执行用 INSERT OR IGNORE，不重复写入。
- 兼容：源表可能缺少 user_id 列，缺失时统一回填到目标 uid。
- 可定制：source / target / uid 均可传参（默认 source=全局库, uid="legacy"）。

用法：
    python backend/scripts/migrate_legacy_db.py
    python backend/scripts/migrate_legacy_db.py --source /path/to/old.db --uid alice
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path


def migrate_legacy_db(source: str = None, target: str = None, uid: str = "legacy") -> dict:
    # 延迟导入，避免脚本被无依赖环境 import 时报错
    from backend.app.services.farm_persistence import PersistentFarmManager
    from src.core.memory_manager import MemoryManager
    from config.settings import settings, user_db_path

    source = source or settings.DATABASE_PATH
    target = target or str(user_db_path(uid))
    src = Path(source)
    if not src.exists():
        return {"migrated": False, "reason": "no_source_db", "source": str(source)}

    # 确保目标库 schema 就绪（新建子库即带 user_id 列）
    PersistentFarmManager(db_path=target, user_id=uid)  # 建 farm 表
    MemoryManager(db_path=target)                       # 建 user_profiles / conversations

    sconn = sqlite3.connect(source)
    tconn = sqlite3.connect(target)
    stats = {"farm_fields": 0, "farm_location": 0, "conversations": 0, "user_profiles": 0}
    try:
        # 1) 地块
        try:
            rows = sconn.execute("SELECT field_id, data, updated_at FROM api_farm_fields").fetchall()
            for fid, data, upd in rows:
                tconn.execute(
                    "INSERT OR IGNORE INTO api_farm_fields (user_id, field_id, data, updated_at) VALUES (?,?,?,?)",
                    (uid, fid, data, upd),
                )
            stats["farm_fields"] = len(rows)
        except sqlite3.OperationalError:
            pass  # 源无 farm 表

        # 2) 位置
        try:
            rows = sconn.execute("SELECT data FROM api_farm_location WHERE id = 1").fetchall()
            for (data,) in rows:
                tconn.execute(
                    "INSERT OR IGNORE INTO api_farm_location (user_id, id, data) VALUES (?, 1, ?)",
                    (uid, data),
                )
            stats["farm_location"] = len(rows)
        except sqlite3.OperationalError:
            pass

        # 3) 对话（conversations 已有 user_id 列）
        #    说明：旧全局库里的对话多为匿名（user_id=api_user），本次迁移把整库旧数据
        #    统一归属到目标 legacy 用户，故 user_id 强制写 uid（即便源非空也覆盖）。
        try:
            rows = sconn.execute(
                "SELECT session_id, user_id, messages, created_at, updated_at FROM conversations"
            ).fetchall()
            for sid, suid, msgs, ca, ua in rows:
                tconn.execute(
                    "INSERT OR IGNORE INTO conversations (session_id, user_id, messages, created_at, updated_at) VALUES (?,?,?,?,?)",
                    (sid, uid, msgs, ca, ua),
                )
            stats["conversations"] = len(rows)
        except sqlite3.OperationalError:
            pass

        # 4) 用户档案（user_profiles 以 user_id 为主键，统一归属到目标 legacy 用户）
        try:
            rows = sconn.execute(
                "SELECT user_id, user_data, created_at, updated_at FROM user_profiles"
            ).fetchall()
            for puid, pdata, ca, ua in rows:
                tconn.execute(
                    "INSERT OR IGNORE INTO user_profiles (user_id, user_data, created_at, updated_at) VALUES (?,?,?,?)",
                    (uid, pdata, ca, ua),
                )
            stats["user_profiles"] = len(rows)
        except sqlite3.OperationalError:
            pass

        tconn.commit()
    finally:
        sconn.close()
        tconn.close()
    return {"migrated": True, "source": str(source), "target": str(target), "uid": uid, **stats}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="迁移旧全局库数据到每用户子库")
    parser.add_argument("--source", default=None, help="源全局库路径（默认 settings.DATABASE_PATH）")
    parser.add_argument("--target", default=None, help="目标库路径（默认 user_db_path(uid)）")
    parser.add_argument("--uid", default="legacy", help="归属的用户 id（默认 legacy）")
    args = parser.parse_args()

    # 把 modelscope_space 根目录加入 sys.path，便于直接运行
    _ROOT = Path(__file__).resolve().parent.parent.parent
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))

    result = migrate_legacy_db(source=args.source, target=args.target, uid=args.uid)
    print(json.dumps(result, ensure_ascii=False, indent=2))
