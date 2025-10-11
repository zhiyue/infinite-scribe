"""
用户命令意图分类器 - MVP版本
仅识别两种核心意图：查询(inquiry)和生成(generation)
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Literal

from src.core.config import get_settings
from src.external.clients.llm import ChatMessage, LLMRequest, LLMResponse
from src.services.llm import LLMService, LLMServiceFactory

# MVP版：只有两种意图类型
IntentType = Literal["inquiry", "generation"]


@dataclass(slots=True)
class IntentClassification:
    """意图分类结果"""

    intent: IntentType
    confidence: float = 0.5
    source: Literal["llm", "heuristic", "fallback"] = "fallback"
    reasoning: str | None = None
    raw_response: str | None = None


class IntentClassifier:
    """
    MVP版意图分类器 - 仅区分查询(inquiry)和生成(generation)两种意图

    查询意图(inquiry)特征：
    - 询问信息、状态、进度
    - 查看、显示、列出内容
    - 请求解释、说明

    生成意图(generation)特征：
    - 创建新内容（角色、情节、世界观等）
    - 继续创作
    - 设计、构建元素
    """

    # 默认模型 - 使用快速模型以提高响应速度
    DEFAULT_MODEL = "gpt-3.5-turbo"

    # 默认置信度阈值
    CONFIDENCE_THRESHOLD = 0.7

    def __init__(
        self,
        *,
        llm_service: LLMService | None = None,
        model: str | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """
        初始化意图分类器

        Args:
            llm_service: LLM服务实例
            model: 使用的模型名称
            logger: 日志记录器
        """
        self._logger = logger or logging.getLogger(__name__)
        self._llm_service = llm_service
        self._model = model or self._resolve_default_model()

        if self._llm_service is None:
            try:
                self._llm_service = LLMServiceFactory().create_service()
                self._logger.info(f"intent_classifier_initialized: model={self._model}")
            except Exception as exc:
                self._logger.warning("intent_classifier_llm_init_failed: %s", exc)
                self._llm_service = None

    @staticmethod
    def _resolve_default_model() -> str:
        """解析默认模型配置"""
        try:
            settings = get_settings()
            if settings.llm.default_model:
                return settings.llm.default_model
        except Exception:
            pass
        return IntentClassifier.DEFAULT_MODEL

    async def classify(
        self, user_input: str | None = None, command_type: str | None = None, payload: dict[str, Any] | None = None
    ) -> IntentClassification:
        """
        识别用户输入意图

        Args:
            user_input: 直接的用户输入文本
            command_type: 命令类型（用于兼容现有系统）
            payload: 包含用户输入和上下文的字典

        Returns:
            IntentClassification: 分类结果
        """
        # 提取文本
        text = user_input or self._extract_text(payload or {})
        if not text:
            # 无输入时默认为生成意图
            return IntentClassification(intent="generation", confidence=0.5, source="fallback")

        # 先尝试启发式规则（快速且准确）
        heuristic_result = self._run_heuristics(text, payload or {})
        if heuristic_result and heuristic_result.confidence >= 0.8:
            self._logger.info(
                f"intent_classified_by_heuristics: intent={heuristic_result.intent}, confidence={heuristic_result.confidence}"
            )
            return heuristic_result

        # 使用LLM进行分类
        llm_result = await self._call_llm(text, command_type, payload or {})
        if llm_result:
            self._logger.info(
                f"intent_classified_by_llm: intent={llm_result.intent}, confidence={llm_result.confidence}"
            )
            return llm_result

        # 如果LLM失败但有启发式结果，使用启发式
        if heuristic_result:
            return heuristic_result

        # 最终兜底：默认为生成意图
        self._logger.warning("intent_classification_fallback", text=text[:100])
        return IntentClassification(
            intent="generation",
            confidence=0.5,
            source="fallback",
            reasoning="Unable to classify, defaulting to generation",
        )

    def _extract_text(self, payload: dict[str, Any]) -> str | None:
        """从payload中提取用户输入文本"""
        # 尝试多个可能的字段名
        candidates = [
            payload.get("user_input"),
            payload.get("input"),
            payload.get("content"),
            payload.get("text"),
            payload.get("prompt"),
            payload.get("message"),
        ]

        # 检查嵌套结构
        if "context" in payload and isinstance(payload["context"], dict):
            context = payload["context"]
            candidates.extend([context.get("user_input"), context.get("prompt"), context.get("message")])

        # 返回第一个非空字符串
        for value in candidates:
            if isinstance(value, str) and value.strip():
                return value.strip()

        return None

    def _run_heuristics(self, text: str, payload: dict[str, Any]) -> IntentClassification | None:
        """
        基于规则的启发式分类

        Args:
            text: 用户输入文本
            payload: 额外的上下文信息

        Returns:
            分类结果或None
        """
        text_lower = text.lower()

        # 查询意图的强特征
        inquiry_patterns = [
            # 疑问词
            r"^(什么|怎么|为什么|哪个|谁|何时|哪里|多少)",
            r"^(what|how|why|which|who|when|where)",
            # 查询动词
            r"(查看|显示|展示|列出|获取|了解|检查|查询|搜索)",
            r"(show|display|list|get|check|search|find|query|look)",
            # 状态询问
            r"(进度|状态|情况|结果)",
            r"(progress|status|state|result)",
            # 问号结尾
            r"[?？]$",
        ]

        # 生成意图的强特征
        generation_patterns = [
            # 创建动词
            r"(生成|创建|创作|写|设计|构建|制作|创造)",
            r"(generate|create|write|design|build|make|construct)",
            # 继续动词
            r"(继续|接着|延续|扩展|接下来)",
            r"(continue|proceed|extend|next)",
            # 内容类型
            r"(角色|情节|世界观|章节|场景|对话|故事|小说)",
            r"(character|plot|world|chapter|scene|dialogue|story|novel)",
        ]

        # 计算匹配分数
        inquiry_score = sum(1 for pattern in inquiry_patterns if re.search(pattern, text_lower, re.IGNORECASE))

        generation_score = sum(1 for pattern in generation_patterns if re.search(pattern, text_lower, re.IGNORECASE))

        # 根据分数判断
        if inquiry_score > generation_score:
            confidence = min(0.9, 0.6 + inquiry_score * 0.1)
            return IntentClassification(
                intent="inquiry",
                confidence=confidence,
                source="heuristic",
                reasoning=f"Matched {inquiry_score} inquiry patterns",
            )
        elif generation_score > 0:
            confidence = min(0.9, 0.6 + generation_score * 0.1)
            return IntentClassification(
                intent="generation",
                confidence=confidence,
                source="heuristic",
                reasoning=f"Matched {generation_score} generation patterns",
            )

        # 检查payload中的提示
        hint = payload.get("intent_hint")
        if isinstance(hint, str):
            normalized = hint.strip().lower()
            if normalized in {"inquiry", "query", "question"}:
                return IntentClassification(
                    intent="inquiry", confidence=0.7, source="heuristic", reasoning="Intent hint provided"
                )
            elif normalized in {"generation", "create", "generate"}:
                return IntentClassification(
                    intent="generation", confidence=0.7, source="heuristic", reasoning="Intent hint provided"
                )

        return None

    async def _call_llm(
        self, text: str, command_type: str | None, payload: dict[str, Any]
    ) -> IntentClassification | None:
        """
        调用LLM进行意图分类

        Args:
            text: 用户输入文本
            command_type: 命令类型
            payload: 上下文信息

        Returns:
            分类结果或None
        """
        if self._llm_service is None:
            return None

        # 构建系统提示词
        system_prompt = """你是一个意图分类器，需要判断用户输入属于以下两类之一：

1. inquiry（查询类）- 用户想要获取信息、查看状态、了解情况
   特征：疑问句、查询动词、请求解释或说明

2. generation（生成类）- 用户想要创建新内容、继续创作
   特征：创建动词、内容类型词、继续或扩展请求

请分析用户输入，只返回JSON格式：
{"intent": "inquiry或generation", "confidence": 0-1之间的数值, "reasoning": "判断理由"}
"""

        # 构建用户消息
        user_message = {
            "user_input": text,
            "command_type": command_type,
            "context_keys": list(payload.keys()) if payload else [],
        }

        request = LLMRequest(
            model=self._model,
            messages=[
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=json.dumps(user_message, ensure_ascii=False)),
            ],
            temperature=0.1,  # 低温度以获得更一致的结果
            max_tokens=200,
        )

        try:
            response = await self._llm_service.generate(request)
            return self._parse_llm_response(response)
        except Exception as exc:
            self._logger.warning("intent_classifier_llm_failed", error=str(exc))
            return None

    def _parse_llm_response(self, response: LLMResponse) -> IntentClassification | None:
        """解析LLM返回的JSON"""
        raw = (response.content or "").strip()
        if not raw:
            return None

        try:
            # 尝试直接解析JSON
            data = json.loads(raw)
        except json.JSONDecodeError:
            # 尝试从文本中提取JSON
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                return None
            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError:
                return None

        # 提取和验证意图类型
        intent = str(data.get("intent", "")).strip().lower()
        if intent not in {"inquiry", "generation"}:
            return None

        # 提取置信度
        try:
            confidence = float(data.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))  # 限制在0-1范围
        except (TypeError, ValueError):
            confidence = 0.5

        # 提取理由
        reasoning = data.get("reasoning", "")

        return IntentClassification(
            intent=intent,  # type: ignore[arg-type]
            confidence=confidence,
            source="llm",
            reasoning=reasoning,
            raw_response=raw,
        )

    def is_high_confidence(self, result: IntentClassification) -> bool:
        """
        检查分类结果是否具有高置信度

        Args:
            result: 分类结果

        Returns:
            是否为高置信度
        """
        return result.confidence >= self.CONFIDENCE_THRESHOLD
