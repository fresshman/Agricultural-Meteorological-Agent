# -*- coding: utf-8 -*-
"""
智能体编排层（Agent Orchestration）
实现双轨协同工作流程

修复点：
1. 修复生长阶段与土壤墒情硬编码（"拔节期"/65.0）→ 按作物+播种日期+近期降水动态推导
2. 修复多轮对话记忆不生效 → 加载历史并注入 LLM 上下文，消息可正确持久化
3. 修复意图识别脆弱 → LLM 失败时关键词规则兜底，不静默跳过失农事判断
4. 默认模型从 settings 统一读取，与配置文件保持一致
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, date
import json
from src.models import (
    UserType, CropType, Location, FieldInfo,
    AgriculturalWeatherData, OperationRecommendation,
    DisasterWarning, DiseaseRisk, AgentResponse
)
from src.data.weather_processor import WeatherProcessor
from src.core.rule_engine import RuleEngine
from src.core.memory_manager import MemoryManager
from src.tools.agent_tools import (
    ToolRegistry, WeatherQueryTool, CropGrowthCalculatorTool,
    FarmOperationJudgeTool, DisasterRiskAssessTool, KnowledgeRetrievalTool
)
from src.agents.llm_integration import RAGEngine, PromptBuilder
from config.settings import settings, CROP_GROWTH_STAGES


class AgriculturalWeatherAgent:
    """农业气象智能体"""

    # 主要作物生育期（天），用于无播种日期时的生长阶段估算
    _CROP_MATURITY_DAYS = {
        "玉米": 120, "小麦": 230, "水稻": 120, "大豆": 110,
        "马铃薯": 100, "番茄": 110, "黄瓜": 90, "辣椒": 120,
        "白菜": 70, "菠菜": 50, "胡萝卜": 100, "苹果": 180,
        "梨": 180, "桃": 160, "葡萄": 150, "柑橘": 210,
        "月季": 120, "菊花": 120, "百合": 100, "兰花": 200, "多肉植物": 120,
    }

    # 意图关键词兜底（LLM 意图识别失败时使用）
    _INTENT_KEYWORDS = [
        ("播种", ["播种", "下种", "育苗", "移栽"]),
        ("灌溉", ["灌溉", "浇水", "灌水", "墒情"]),
        ("施肥", ["施肥", "追肥", "基肥", "叶面肥", "上肥"]),
        ("植保", ["喷药", "打药", "植保", "防虫", "防治", "除草"]),
        ("收获", ["收获", "收割", "采收", "采摘"]),
        ("病虫害", ["病虫害", "病害", "虫害", "发病", "生虫"]),
        ("灾害", ["灾害", "预警", "霜冻", "暴雨", "高温", "干旱", "大风", "台风"]),
    ]

    def __init__(
        self,
        llm_api_key: str = None,
        weather_api_key: str = None,
        weather_subscription_id: str = None,
        llm_model: str = None,
        embedding_model: str = None
    ):
        from src.utils.clients import LLMClient as RealLLMClient, EmbeddingClient

        # 默认模型统一从 settings 读取，避免与配置文件不一致
        llm_model = llm_model or settings.LLM_MODEL
        embedding_model = embedding_model or settings.EMBEDDING_MODEL

        print("  ├─ 初始化LLM客户端...")
        llm_api_url = getattr(settings, 'LLM_API_URL', None)

        try:
            self.llm_client = RealLLMClient(
                model=llm_model,
                api_key=llm_api_key,
                base_url=llm_api_url
            )
            print(f"  │  ✅ LLM客户端初始化成功 (模型: {llm_model})")
        except Exception as e:
            print(f"  │  ❌ LLM客户端初始化失败: {e}")
            self.llm_client = None

        print("  ├─ 初始化气象数据处理器...")
        try:
            self.weather_processor = WeatherProcessor(
                api_key=weather_api_key,
                subscription_id=weather_subscription_id
            )
            print("  │  ✅ 气象处理器初始化成功")
        except Exception as e:
            print(f"  │  ❌ 气象处理器初始化失败: {e}")
            self.weather_processor = None

        print("  ├─ 初始化规则引擎...")
        self.rule_engine = RuleEngine()
        print("  │  ✅ 规则引擎初始化成功")

        print("  ├─ 初始化记忆管理器...")
        self.memory_manager = MemoryManager()
        # 每用户记忆管理器缓存：登录用户的数据落各自独立子库（磁盘级隔离）
        self._mem_cache: dict = {}
        print("  │  ✅ 记忆管理器初始化成功")

        print(f"  ├─ 初始化RAG引擎 (Embedding: {embedding_model})...")
        try:
            self.rag_engine = RAGEngine(self.llm_client, embedding_model=embedding_model)
            if self.rag_engine and self.rag_engine.vector_db:
                stats = self.rag_engine.vector_db.get_statistics()
                print(f"  │  ✅ RAG引擎初始化成功 (文档数: {stats['total_documents']})")
            else:
                print("  │  ⚠️ RAG引擎初始化成功，但向量数据库未加载")
        except Exception as e:
            print(f"  │  ❌ RAG引擎初始化失败: {e}")
            self.rag_engine = None

        print("  ├─ 注册工具...")
        self.tool_registry = ToolRegistry()
        self._register_tools()
        # 修复：LLM 可用性统一判断（对象存在 且 内部 client 已配置 key）
        # 避免"有对象但无 key"时调用空 client 崩溃，而是走规则引擎兜底
        self.llm_available = bool(self.llm_client and self.llm_client.client)
        print(f"  │  ✅ 已注册 {len(self.tool_registry.tools)} 个工具 (LLM可用={self.llm_available})")

    def get_memory_manager(self, user_id: str):
        """按用户返回其独立子库的记忆管理器（缓存复用）。

        未提供 user_id 时回退到全局默认管理器，保证向后兼容。
        """
        if not user_id:
            return self.memory_manager
        uid = str(user_id)
        if uid not in self._mem_cache:
            from config.settings import user_db_path
            self._mem_cache[uid] = MemoryManager(db_path=str(user_db_path(uid)))
        return self._mem_cache[uid]

    def _register_tools(self):
        """注册工具"""
        from src.tools.agent_tools import (
            FertilizationRecommendTool, HarvestTimingTool,
            VarietyRecommendTool, CropRotationTool,
            SymptomDiagnosisTool, StorageRiskTool,
            VegetablePlantingTool, FruitTreeManagementTool,
            FlowerCareTool, GreenhouseEnvironmentTool
        )
        from src.tools.weather_warning_tools import (
            DisasterWarningTool, PestDiseasePredictionTool,
            WeatherSuitabilityTool
        )

        self.tool_registry.register(WeatherQueryTool(self.weather_processor))
        self.tool_registry.register(CropGrowthCalculatorTool(self.rule_engine))
        self.tool_registry.register(FarmOperationJudgeTool(self.rule_engine))
        self.tool_registry.register(DisasterRiskAssessTool(self.rule_engine))
        self.tool_registry.register(KnowledgeRetrievalTool(self.rag_engine))
        self.tool_registry.register(FertilizationRecommendTool(self.rule_engine))
        self.tool_registry.register(HarvestTimingTool(self.rule_engine))
        self.tool_registry.register(VarietyRecommendTool(self.rule_engine))
        self.tool_registry.register(CropRotationTool(self.rule_engine))
        self.tool_registry.register(SymptomDiagnosisTool(self.rule_engine))
        self.tool_registry.register(StorageRiskTool(self.rule_engine))
        self.tool_registry.register(VegetablePlantingTool(self.rule_engine))
        self.tool_registry.register(FruitTreeManagementTool(self.rule_engine))
        self.tool_registry.register(FlowerCareTool(self.rule_engine))
        self.tool_registry.register(GreenhouseEnvironmentTool(self.rule_engine))

        self.tool_registry.register(DisasterWarningTool())
        self.tool_registry.register(PestDiseasePredictionTool())
        self.tool_registry.register(WeatherSuitabilityTool())

    # ---------- 意图识别（带关键词兜底） ----------

    async def _recognize_intent(self, query: str) -> Dict[str, Any]:
        """
        识别用户意图。

        修复点：LLM 返回非 JSON 或异常时，不再静默兜底为"其他"
        （会导致农事判断全被跳过），而是用关键词规则兜底。
        """
        if self.llm_available:
            try:
                intent_prompt = PromptBuilder.build_intent_recognition_prompt(query)
                intent_response = await self.llm_client.complete_async(intent_prompt, temperature=0.1)
                if "```json" in intent_response:
                    intent_response = intent_response.split("```json")[1].split("```")[0].strip()
                elif "```" in intent_response:
                    intent_response = intent_response.split("```")[1].split("```")[0].strip()
                # 容忍 LLM 在 JSON 前后加说明文字：提取第一个 {...}
                start = intent_response.find("{")
                end = intent_response.rfind("}")
                if start >= 0 and end > start:
                    intent_response = intent_response[start:end + 1]
                intent_data = json.loads(intent_response)
                if isinstance(intent_data, dict) and intent_data.get("intent"):
                    return intent_data
            except Exception as e:
                print(f"意图识别失败，使用关键词兜底: {e}")

        return self._keyword_intent(query)

    def _keyword_intent(self, query: str) -> Dict[str, Any]:
        """关键词规则兜底意图识别"""
        intent = "其他"
        for name, kws in self._INTENT_KEYWORDS:
            if any(kw in query for kw in kws):
                intent = name
                break

        # 尝试识别作物类型
        crop_type = None
        for ct in CropType:
            if ct.value in query:
                crop_type = ct.value
                break

        return {
            "intent": intent,
            "crop_type": crop_type,
            "growth_stage": None,
            "location": None,
            "time": None,
            "operation": None,
            "urgency": "低",
            "fallback": True,
        }

    # ---------- 生长阶段与土壤墒情动态推导 ----------

    def _estimate_growth_stage(
        self,
        crop_type: Optional[CropType],
        sowing_date: Optional[date]
    ) -> Optional[str]:
        """
        按作物 + 播种日期动态推导当前生长阶段（替代硬编码"拔节期"）。

        Args:
            crop_type: 作物类型
            sowing_date: 播种日期

        Returns:
            生长阶段名（字符串），无法推导时返回 None
        """
        if not crop_type:
            return None

        stages = CROP_GROWTH_STAGES.get(crop_type.value)
        if not stages:
            return None

        # 有播种日期：按播种天数占生育期比例推算阶段
        if sowing_date:
            days = (datetime.now().date() - sowing_date).days
            if days < 0:
                days = 0
            maturity = self._CROP_MATURITY_DAYS.get(crop_type.value, 120)
            ratio = max(0.0, min(1.0, days / maturity))
            idx = min(int(ratio * len(stages)), len(stages) - 1)
            return stages[idx]

        # 无播种日期：返回中期阶段（折中），保证农事判断仍可运行
        return stages[len(stages) // 2] if stages else None

    def _estimate_soil_moisture(
        self,
        historical_weather: List[Any]
    ) -> float:
        """
        基于近期降水估算土壤墒情（替代硬编码 65.0）。

        有真实土壤传感器数据时应替换为传感器值；此处为无传感器时合理的
        气象推导估算：近期降水多则墒情高，久旱则偏低。
        """
        if not historical_weather:
            return 60.0
        recent = historical_weather[-48:] if len(historical_weather) > 48 else historical_weather
        precip = sum(getattr(w, 'precipitation', 0) or 0 for w in recent)
        soil = 55.0 + precip * 1.5
        return max(25.0, min(90.0, soil))

    # ---------- 主流程 ----------

    async def prepare_query(
        self,
        query: str,
        user_id: str,
        session_id: str,
        user_type: UserType = UserType.FARMER,
        field_id: Optional[str] = None,
        location: Optional[Location] = None,
        crop_type: Optional[CropType] = None
    ) -> Dict[str, Any]:
        """
        执行意图识别 / 取天气 / 规则引擎 / 知识检索，
        返回生成回答所需的完整上下文（流式与非流式复用）。

        Returns:
            含 messages(LLM 对话消息，含历史)、structured_results、
            weather_data、knowledge_results、query/user_id/session_id 的字典
        """
        intent_data = await self._recognize_intent(query)

        field_info = self.get_memory_manager(user_id).get_active_field(user_id, field_id)

        # 如果提供了location或crop_type，更新或创建field_info
        if location or crop_type:
            if not field_info:
                from src.models import FieldInfo as FieldInfoModel
                field_info = FieldInfoModel(
                    field_id="temp_field",
                    location=location or Location(province="河南省", city="郑州市", latitude=34.75, longitude=113.65),
                    crop_type=crop_type or CropType.CORN,
                    area=10.0,
                    soil_type="壤土"  # 默认土壤类型
                )
            else:
                if location:
                    field_info.location = location
                if crop_type:
                    field_info.crop_type = crop_type

        weather_data, weather_list = await self._fetch_weather_data(field_info, intent_data)

        structured_results = await self._execute_rule_engine(
            intent_data, weather_data, field_info
        )

        knowledge_results = await self._retrieve_knowledge(query, field_info, intent_data)

        response_prompt = PromptBuilder.build_response_prompt(
            json.dumps(structured_results, ensure_ascii=False, indent=2),
            weather_data.json() if weather_data else "无气象数据",
            query,
            user_type
        )

        # 多轮记忆：加载历史并注入 LLM 上下文
        history = self.get_memory_manager(user_id).get_conversation_messages(
            session_id, settings.MAX_HISTORY_LENGTH
        )
        messages = [{"role": "system", "content": PromptBuilder.build_system_prompt(user_type)}]
        messages.extend(history)
        messages.append({"role": "user", "content": response_prompt})

        return {
            "messages": messages,
            "structured_results": structured_results,
            "weather_data": weather_data,
            "weather_list": weather_list,
            "knowledge_results": knowledge_results,
            "query": query,
            "user_id": user_id,
            "session_id": session_id,
        }

    def _finalize_response(
        self,
        ctx: Dict[str, Any],
        final_response: str
    ) -> AgentResponse:
        """记录消息并组装最终响应（流式/非流式共用）"""
        structured_results = ctx["structured_results"]
        weather_data = ctx["weather_data"]
        knowledge_results = ctx["knowledge_results"]

        self.get_memory_manager(ctx["user_id"]).add_message_to_conversation(
            ctx["session_id"], "user", ctx["query"], user_id=ctx["user_id"]
        )
        self.get_memory_manager(ctx["user_id"]).add_message_to_conversation(
            ctx["session_id"], "assistant", final_response, user_id=ctx["user_id"]
        )

        return AgentResponse(
            content=final_response,
            operation_recommendations=structured_results.get("operation_recommendations", []),
            disaster_warnings=structured_results.get("disaster_warnings", []),
            disease_risks=structured_results.get("disease_risks", []),
            weather_data=weather_data,
            evidence=self._build_evidence(structured_results, knowledge_results),
            confidence=self._calculate_confidence(structured_results, weather_data)
        )

    async def process_query(
        self,
        query: str,
        user_id: str,
        session_id: str,
        user_type: UserType = UserType.FARMER,
        field_id: Optional[str] = None,
        location: Optional[Location] = None,
        crop_type: Optional[CropType] = None
    ) -> AgentResponse:
        """
        处理用户查询（非流式主流程）

        Args:
            query: 用户问题
            user_id: 用户ID
            session_id: 会话ID
            user_type: 用户类型
            field_id: 地块ID
            location: 位置信息（可选，优先级高于field_info中的位置）
            crop_type: 作物类型（可选，优先级高于field_info中的作物）

        Returns:
            智能体响应
        """
        ctx = await self.prepare_query(
            query=query,
            user_id=user_id,
            session_id=session_id,
            user_type=user_type,
            field_id=field_id,
            location=location,
            crop_type=crop_type,
        )

        if self.llm_available:
            final_response = await self.llm_client.chat_async(ctx["messages"], temperature=0.3)
        else:
            final_response = self._fallback_response(
                ctx["structured_results"], ctx["weather_data"]
            )

        return self._finalize_response(ctx, final_response)

    async def stream_query(
        self,
        query: str,
        user_id: str,
        session_id: str,
        user_type: UserType = UserType.FARMER,
        field_id: Optional[str] = None,
        location: Optional[Location] = None,
        crop_type: Optional[CropType] = None
    ) -> Any:
        """
        真流式查询：先准备上下文，再逐 token 产出最终回答（AsyncGenerator[str]）。
        """
        ctx = await self.prepare_query(
            query=query,
            user_id=user_id,
            session_id=session_id,
            user_type=user_type,
            field_id=field_id,
            location=location,
            crop_type=crop_type,
        )

        if not self.llm_available:
            # LLM 不可用时，一次性产出兜底内容（保持接口一致）
            fallback = self._fallback_response(ctx["structured_results"], ctx["weather_data"])
            yield fallback
        else:
            async for token in self.llm_client.astream_chat(ctx["messages"], temperature=0.3):
                yield token

    def _fallback_response(
        self,
        structured_results: Dict[str, Any],
        weather_data: Optional[AgriculturalWeatherData]
    ) -> str:
        """LLM 不可用时，基于结构化结果生成兜底回复（不静默空白）"""
        parts = ["【系统提示】大模型服务暂不可用，以下为基于规则引擎的农事建议："]
        if weather_data:
            w = weather_data.base_weather
            parts.append(
                f"当前温度 {w.temperature}°C，湿度 {w.humidity}%，"
                f"降水 {w.precipitation}mm，风速 {w.wind_speed}m/s。"
            )
        for rec in structured_results.get("operation_recommendations", []):
            parts.append(f"- {rec.get('operation_type', '')}: {rec.get('operation_details', '')}")
        for warn in structured_results.get("disaster_warnings", []):
            parts.append(f"- 灾害预警: {warn.get('disaster_type', '')}({warn.get('risk_level', '')})")
        if not parts[1:]:
            parts.append("- 暂无明确的农事操作建议，建议结合本地农技站意见。")
        return "\n".join(parts)

    async def _fetch_weather_data(
        self,
        field_info: Optional[FieldInfo],
        intent_data: Dict[str, Any]
    ) -> Tuple[Optional[AgriculturalWeatherData], List[Dict[str, Any]]]:
        """
        获取气象数据（过去 7 天 + 未来 6 小时，一次请求供规则引擎与 nowcast 复用）

        Args:
            field_info: 地块信息
            intent_data: 意图数据

        Returns:
            (农业气象数据, 原始气象数据列表(含未来6h))
        """
        if not field_info:
            return None, []

        try:
            weather_tool = self.tool_registry.get("weather_query")
            end_time = datetime.now() + timedelta(hours=6)
            start_time = end_time - timedelta(days=7)

            result = await weather_tool.run(
                location=field_info.location,
                start_time=start_time,
                end_time=end_time,
                granularity="hourly"
            )

            if result.get("weather_data") and len(result["weather_data"]) > 0:
                weather_data_list = result["weather_data"]
                # 修复：数据已按时间升序，最新一条为最后一条
                latest_weather_dict = weather_data_list[-1]

                from src.models import WeatherData
                latest_weather = WeatherData(**latest_weather_dict)

                historical_weather = [WeatherData(**w) for w in weather_data_list[:-1]]

                # 修复：动态推导土壤墒情（替代硬编码 65.0）
                soil_moisture = self._estimate_soil_moisture(historical_weather)

                # 修复：动态推导生长阶段（替代硬编码 "拔节期"）
                crop_type = field_info.crop_type
                growth_stage = self._estimate_growth_stage(
                    crop_type, field_info.sowing_date
                )

                agri_weather = self.weather_processor.process_to_agricultural_weather(
                    weather_data=latest_weather,
                    historical_weather=historical_weather,
                    soil_moisture=soil_moisture,
                    crop_type=crop_type,
                    growth_stage=growth_stage
                )

                return agri_weather, weather_data_list
        except Exception as e:
            print(f"获取气象数据失败: {e}")

        return None, []

    async def _execute_rule_engine(
        self,
        intent_data: Dict[str, Any],
        weather_data: Optional[AgriculturalWeatherData],
        field_info: Optional[FieldInfo]
    ) -> Dict[str, Any]:
        """
        执行规则引擎

        Args:
            intent_data: 意图数据
            weather_data: 气象数据
            field_info: 地块信息

        Returns:
            结构化结果
        """
        results = {
            "operation_recommendations": [],
            "disaster_warnings": [],
            "disease_risks": []
        }

        if not weather_data:
            return results

        intent = intent_data.get("intent", "其他")

        if intent in ["播种", "灌溉", "施肥", "植保", "收获"]:
            operation_tool = self.tool_registry.get("farm_operation_judge")

            crop_type = None
            growth_stage = None
            if field_info:
                crop_type = field_info.crop_type
                growth_stage = self._estimate_growth_stage(
                    crop_type, field_info.sowing_date
                )

            # 获取动态土壤墒情（复用估算逻辑）
            soil_moisture = None
            if weather_data and weather_data.base_weather:
                from src.models import WeatherData as _W
                # 使用规则引擎评估时传入动态墒情
                try:
                    # 从农业气象数据的积温/降水反推一个合理墒情
                    precip = 0.0
                    if hasattr(weather_data, 'precipitation_anomaly'):
                        precip = max(0.0, 100.0 + (weather_data.precipitation_anomaly or 0))
                    soil_moisture = max(25.0, min(90.0, 55.0 + precip * 0.15))
                except Exception:
                    soil_moisture = None

            operation_result = operation_tool.run(
                operation_type=intent,
                weather_data=weather_data,
                crop_type=crop_type,
                soil_moisture=soil_moisture,
                growth_stage=growth_stage,
                location=field_info.location if field_info else None
            )

            if "error" not in operation_result:
                results["operation_recommendations"].append(operation_result)

        disaster_tool = self.tool_registry.get("disaster_risk_assess")
        disaster_result = disaster_tool.run(
            weather_data=weather_data,
            crop_type=field_info.crop_type if field_info else None,
            growth_stage=self._estimate_growth_stage(
                field_info.crop_type if field_info else None,
                field_info.sowing_date if field_info else None
            )
        )

        results["disaster_warnings"] = disaster_result.get("disaster_warnings", [])
        results["disease_risks"] = disaster_result.get("disease_risks", [])

        return results

    async def _retrieve_knowledge(
        self,
        query: str,
        field_info: Optional[FieldInfo],
        intent_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        检索知识

        Args:
            query: 用户问题
            field_info: 地块信息
            intent_data: 意图数据

        Returns:
            知识检索结果
        """
        if not self.rag_engine:
            return []

        knowledge_tool = self.tool_registry.get("knowledge_retrieval")

        region = None
        crop_type = None
        if field_info:
            region = field_info.location.agricultural_region
            crop_type = field_info.crop_type.value

        result = await knowledge_tool.run(
            query=query,
            top_k=5,
            region=region,
            crop_type=crop_type
        )

        return result.get("results", [])

    def _build_evidence(
        self,
        structured_results: Dict[str, Any],
        knowledge_results: List[Dict[str, Any]]
    ) -> str:
        """
        构建证据链

        Args:
            structured_results: 结构化结果
            knowledge_results: 知识检索结果

        Returns:
            证据文本
        """
        evidence_parts = []

        if structured_results.get("operation_recommendations"):
            for rec in structured_results["operation_recommendations"]:
                evidence_parts.append(f"操作建议依据：{rec.get('evidence', '')}")

        if structured_results.get("disaster_warnings"):
            evidence_parts.append(f"灾害预警：检测到{len(structured_results['disaster_warnings'])}项风险")

        if structured_results.get("disease_risks"):
            evidence_parts.append(f"病虫害风险：检测到{len(structured_results['disease_risks'])}项风险")

        if knowledge_results:
            evidence_parts.append(f"知识库参考：引用{len(knowledge_results)}条资料")

        return "；".join(evidence_parts) if evidence_parts else "基于气象数据和农业标准"

    def _calculate_confidence(
        self,
        structured_results: Dict[str, Any],
        weather_data: Optional[AgriculturalWeatherData]
    ) -> float:
        """
        计算置信度

        Args:
            structured_results: 结构化结果
            weather_data: 气象数据

        Returns:
            置信度（0-1）
        """
        confidence = 0.5

        if weather_data:
            confidence += 0.2

        if structured_results.get("operation_recommendations"):
            confidence += 0.1

        if structured_results.get("disaster_warnings"):
            confidence += 0.1

        if structured_results.get("disease_risks"):
            confidence += 0.1

        return min(confidence, 1.0)

    async def register_user(
        self,
        user_id: str,
        user_type: UserType,
        name: str,
        phone: Optional[str] = None
    ) -> bool:
        """
        注册用户

        Args:
            user_id: 用户ID
            user_type: 用户类型
            name: 用户名称
            phone: 手机号

        Returns:
            是否成功
        """
        from src.models import UserProfile

        profile = UserProfile(
            user_id=user_id,
            user_type=user_type,
            name=name,
            phone=phone
        )

        return self.get_memory_manager(user_id).save_user_profile(profile)

    async def add_field(
        self,
        user_id: str,
        field_id: str,
        location: Location,
        area: float,
        soil_type: str,
        crop_type: CropType,
        variety: Optional[str] = None,
        sowing_date: Optional[datetime] = None
    ) -> bool:
        """
        添加地块

        Args:
            user_id: 用户ID
            field_id: 地块ID
            location: 地理位置信息
            area: 面积
            soil_type: 土壤类型
            crop_type: 作物类型
            variety: 品种
            sowing_date: 播种日期

        Returns:
            是否成功
        """
        # 修复：sowing_date 支持 date / datetime 两种类型
        sowing = sowing_date
        if sowing_date is not None and hasattr(sowing_date, "date"):
            sowing = sowing_date.date()

        field_info = FieldInfo(
            field_id=field_id,
            location=location,
            area=area,
            soil_type=soil_type,
            crop_type=crop_type,
            variety=variety,
            sowing_date=sowing
        )

        return self.get_memory_manager(user_id).add_field_to_user(user_id, field_info)
