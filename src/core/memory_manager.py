# -*- coding: utf-8 -*-
"""
用户记忆管理
实现长期记忆（地块档案）和短期记忆（对话上下文）
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
from pathlib import Path
from src.models import UserProfile, FieldInfo, ConversationHistory, Location
from config.settings import settings


class MemoryManager:
    """记忆管理器"""
    
    def __init__(self, db_path: str = None):
        self.db_path = Path(db_path or settings.DATABASE_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                user_data TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                session_id TEXT PRIMARY KEY,
                user_id TEXT,
                messages TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_user_profile(self, profile: UserProfile) -> bool:
        """
        保存用户档案（长期记忆）
        
        Args:
            profile: 用户档案
        
        Returns:
            是否成功
        """
        import sqlite3
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO user_profiles 
                (user_id, user_data, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            ''', (
                profile.user_id,
                profile.json(),
                profile.created_at,
                datetime.now()
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"保存用户档案失败: {e}")
            return False
    
    def load_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """
        加载用户档案
        
        Args:
            user_id: 用户ID
        
        Returns:
            用户档案
        """
        import sqlite3
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT user_data FROM user_profiles WHERE user_id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return UserProfile.parse_raw(result[0])
            return None
        except Exception as e:
            print(f"加载用户档案失败: {e}")
            return None
    
    def add_field_to_user(
        self,
        user_id: str,
        field_info: FieldInfo
    ) -> bool:
        """
        为用户添加地块
        
        Args:
            user_id: 用户ID
            field_info: 地块信息
        
        Returns:
            是否成功
        """
        profile = self.load_user_profile(user_id)
        if not profile:
            return False
        
        profile.fields.append(field_info)
        profile.updated_at = datetime.now()
        
        return self.save_user_profile(profile)
    
    def save_conversation(self, conversation: ConversationHistory) -> bool:
        """
        保存对话历史（短期记忆）
        
        Args:
            conversation: 对话历史
        
        Returns:
            是否成功
        """
        import sqlite3
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO conversations
                (session_id, user_id, messages, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                conversation.session_id,
                conversation.user_id,
                json.dumps(conversation.messages, ensure_ascii=False),
                conversation.created_at,
                datetime.now()
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"保存对话历史失败: {e}")
            return False
    
    def load_conversation(self, session_id: str) -> Optional[ConversationHistory]:
        """
        加载对话历史
        
        Args:
            session_id: 会话ID
        
        Returns:
            对话历史
        """
        import sqlite3
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT user_id, messages, created_at, updated_at 
                FROM conversations WHERE session_id = ?
            ''', (session_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return ConversationHistory(
                    session_id=session_id,
                    user_id=result[0],
                    messages=json.loads(result[1]),
                    created_at=result[2],
                    updated_at=result[3]
                )
            return None
        except Exception as e:
            print(f"加载对话历史失败: {e}")
            return None
    
    def add_message_to_conversation(
        self,
        session_id: str,
        role: str,
        content: str,
        user_id: str = "api_user"
    ) -> bool:
        """
        向对话添加消息（会话不存在时自动创建）

        修复点：原实现若会话不存在直接返回 False，导致消息永远记录不上，
        多轮记忆形同虚设。现自动创建会话再追加消息。

        Args:
            session_id: 会话ID
            role: 角色（user/assistant）
            content: 消息内容
            user_id: 用户ID（仅首次创建会话时使用）

        Returns:
            是否成功
        """
        conversation = self.load_conversation(session_id)
        if not conversation:
            # 自动创建会话，保证消息可持久化
            conversation = ConversationHistory(
                session_id=session_id,
                user_id=user_id,
                messages=[],
            )

        conversation.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        if len(conversation.messages) > settings.MAX_HISTORY_LENGTH * 2:
            conversation.messages = conversation.messages[-settings.MAX_HISTORY_LENGTH * 2:]
        
        conversation.updated_at = datetime.now()
        
        return self.save_conversation(conversation)
    
    def get_user_fields(self, user_id: str) -> List[FieldInfo]:
        """
        获取用户所有地块

        Args:
            user_id: 用户ID

        Returns:
            地块列表
        """
        profile = self.load_user_profile(user_id)
        if profile:
            return profile.fields
        return []

    def get_conversation_messages(self, session_id: str, limit: int = None) -> List[Dict[str, str]]:
        """
        读取会话历史消息（供多轮上下文注入）

        Args:
            session_id: 会话ID
            limit: 返回最近 N 条消息（None 返回全部）

        Returns:
            消息列表（剥离内部 timestamp 字段，只保留 role/content）
        """
        conversation = self.load_conversation(session_id)
        if not conversation:
            return []
        msgs = []
        for m in conversation.messages:
            if isinstance(m, dict) and "role" in m and "content" in m:
                msgs.append({"role": m["role"], "content": m["content"]})
        if limit and len(msgs) > limit:
            msgs = msgs[-limit:]
        return msgs

    def get_active_field(
        self,
        user_id: str,
        field_id: Optional[str] = None
    ) -> Optional[FieldInfo]:
        """
        获取用户当前活动地块
        
        Args:
            user_id: 用户ID
            field_id: 地块ID（可选）
        
        Returns:
            地块信息
        """
        fields = self.get_user_fields(user_id)
        if not fields:
            return None
        
        if field_id:
            for field in fields:
                if field.field_id == field_id:
                    return field
        
        return fields[0]

