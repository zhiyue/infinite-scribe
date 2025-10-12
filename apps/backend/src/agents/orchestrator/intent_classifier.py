"""
用户命令意图分类器 - MVP版本

本模块实现基于混合策略的意图分类系统，用于识别用户输入的核心意图类型。
采用三层降级策略确保分类的准确性和鲁棒性：

1. 启发式规则（优先级最高）：基于模式匹配的快速分类，准确度高
2. LLM分类（中等优先级）：使用语言模型进行语义理解和分类
3. 兜底策略（最低优先级）：当前两者都失败时返回默认分类

MVP阶段仅支持两种核心意图：
- inquiry（查询意图）：获取信息、查看状态、了解进度
- generation（生成意图）：创建内容、继续创作、设计元素
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

# MVP版：只有两种意图类型，后续可扩展为更多意图类型
IntentType = Literal["inquiry", "generation"]


@dataclass(slots=True)
class IntentClassification:
    """意图分类结果数据类

    封装意图分类的完整结果，包括意图类型、置信度、来源和推理过程。
    使用dataclass简化数据结构定义，slots=True优化内存占用。

    Attributes:
        intent: 识别出的意图类型（inquiry或generation）
        confidence: 分类置信度，取值范围[0.0, 1.0]，默认0.5表示不确定
        source: 分类结果来源，标识使用了哪种策略
            - "llm": 通过语言模型分类
            - "heuristic": 通过启发式规则分类
            - "fallback": 兜底策略（无法分类时的默认值）
        reasoning: 分类推理过程的文字说明，便于调试和理解分类依据
        raw_response: LLM返回的原始响应内容（仅在source="llm"时有值）
    """

    intent: IntentType
    confidence: float = 0.5
    source: Literal["llm", "heuristic", "fallback"] = "fallback"
    reasoning: str | None = None
    raw_response: str | None = None


class IntentClassifier:
    """
    MVP版用户意图分类器

    实现三层降级的混合分类策略，确保在各种场景下都能给出合理的分类结果：
    1. 启发式规则优先：基于正则表达式的模式匹配，速度快、准确度高
    2. LLM语义理解：当启发式规则置信度不足时，使用语言模型进行深度语义分析
    3. 兜底默认策略：当前两种方法都失败时，返回默认的generation意图

    设计理念：
    - 快速响应：启发式规则可在毫秒级完成分类
    - 准确性：LLM提供语义理解能力，处理复杂和模糊的输入
    - 可靠性：兜底策略确保系统在任何情况下都能返回有效结果
    - 可追溯：记录分类来源和推理过程，便于调试和优化

    支持的意图类型：

    查询意图(inquiry)特征：
    - 询问信息、状态、进度（"我的小说写到哪里了？"）
    - 查看、显示、列出内容（"显示所有角色"）
    - 请求解释、说明（"这个世界观是什么意思？"）

    生成意图(generation)特征：
    - 创建新内容（"创建一个魔法世界"）
    - 继续创作（"继续写这个章节"）
    - 设计、构建元素（"设计主角的背景故事"）

    Attributes:
        DEFAULT_MODEL: 默认使用的LLM模型，优先选择快速响应的模型
        CONFIDENCE_THRESHOLD: 高置信度判定阈值，用于决策是否需要更深入的分类
    """

    # 默认模型 - 使用快速模型以提高响应速度，降低API调用成本
    DEFAULT_MODEL = "deepseek-chat"

    # 默认置信度阈值 - 高于此值视为高置信度分类结果
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

        采用依赖注入模式，支持外部传入服务实例以便于测试和灵活配置。
        如果未提供LLM服务实例，将尝试通过工厂模式自动创建。

        初始化失败策略：
        - LLM服务创建失败时不抛出异常，而是记录警告日志
        - 分类器仍可继续工作，依靠启发式规则和兜底策略
        - 这种设计保证了系统的可用性和容错性

        Args:
            llm_service: LLM服务实例（可选）。用于调用语言模型进行意图分类。
                        如为None，将尝试自动创建服务实例
            model: 使用的模型名称（可选）。如为None，将从配置中读取或使用默认模型
            logger: 日志记录器（可选）。如为None，将使用模块默认logger
        """
        self._logger = logger or logging.getLogger(__name__)
        self._llm_service = llm_service
        self._model = model or self._resolve_default_model()

        # 延迟初始化LLM服务 - 如果外部未提供，则尝试自动创建
        if self._llm_service is None:
            try:
                self._llm_service = LLMServiceFactory().create_service()
                self._logger.info(f"intent_classifier_initialized: model={self._model}")
            except Exception as exc:
                # LLM服务初始化失败不应导致分类器不可用
                # 降级使用启发式规则和兜底策略
                self._logger.warning("intent_classifier_llm_init_failed: %s", exc)
                self._llm_service = None

    @staticmethod
    def _resolve_default_model() -> str:
        """
        解析默认模型配置

        按优先级顺序获取模型配置：
        1. 从系统配置中读取default_model
        2. 使用类常量DEFAULT_MODEL作为兜底

        这种两级兜底机制确保即使配置读取失败也能正常工作。

        Returns:
            str: 模型名称
        """
        try:
            settings = get_settings()
            if settings.llm.default_model:
                return settings.llm.default_model
        except Exception:
            # 配置读取失败时静默处理，使用默认值
            pass
        return IntentClassifier.DEFAULT_MODEL

    async def classify(
        self, user_input: str | None = None, command_type: str | None = None, payload: dict[str, Any] | None = None
    ) -> IntentClassification:
        """
        识别用户输入意图 - 核心分类方法

        实现三层降级策略的完整分类流程：

        1. 文本提取阶段：
           - 优先使用直接传入的user_input
           - 如无直接输入，从payload中提取文本
           - 支持多种字段名和嵌套结构

        2. 分类决策流程：
           a. 启发式规则（快速路径）：
              - 基于正则表达式的模式匹配
              - 如果置信度 >= 0.8，直接返回结果
              - 毫秒级响应，适合明确的意图表达

           b. LLM语义分析（智能路径）：
              - 当启发式规则置信度不足时启用
              - 使用语言模型进行深度语义理解
              - 处理复杂、模糊或新颖的表达方式

           c. 启发式兜底（次级路径）：
              - 当LLM调用失败但启发式有结果时使用
              - 避免因LLM服务不可用导致分类失败

           d. 默认兜底（最终路径）：
              - 当所有方法都失败时返回默认generation意图
              - 确保系统永远不会因分类失败而中断

        设计考量：
        - 性能优先：先尝试快速的启发式规则
        - 准确性保障：LLM提供复杂场景的处理能力
        - 可靠性：多层兜底确保总能返回有效结果
        - 可追溯性：详细的调试日志便于问题诊断

        Args:
            user_input: 直接的用户输入文本（可选）
            command_type: 命令类型（可选），用于兼容现有系统
            payload: 包含用户输入和上下文的字典（可选）

        Returns:
            IntentClassification: 分类结果，包含意图类型、置信度、来源和推理过程
        """
        # 记录输入参数，便于调试和追踪分类过程
        self._logger.debug(
            f"intent_classifier_input: user_input={user_input}, command_type={command_type}, "
            f"payload_keys={list(payload.keys()) if payload else []}"
        )

        # 第一步：提取用户输入文本
        # 优先使用直接传入的user_input，否则从payload中智能提取
        text = user_input or self._extract_text(payload or {})

        # 记录提取结果，限制长度避免日志过大
        self._logger.debug(f"intent_classifier_extracted_text: text={repr(text)[:200] if text else None}")

        if not text:
            # 边界情况：无任何输入文本时的处理
            # 默认为generation意图，因为大部分无明确输入的场景是创作场景
            self._logger.info(
                f"intent_classifier_no_text: defaulting to generation, user_input={user_input is not None}, "
                f"payload_has_user_input={'user_input' in (payload or {})}"
            )
            return IntentClassification(intent="generation", confidence=0.5, source="fallback")

        # 第二步：启发式规则分类（快速路径）
        # 使用正则表达式匹配特征模式，响应速度快
        heuristic_result = self._run_heuristics(text, payload or {})
        if heuristic_result and heuristic_result.confidence >= 0.8:
            # 高置信度的启发式结果可直接使用，无需调用LLM
            self._logger.info(
                f"intent_classified_by_heuristics: intent={heuristic_result.intent}, confidence={heuristic_result.confidence}"
            )
            return heuristic_result

        # 第三步：LLM语义分析（智能路径）
        # 处理启发式规则无法准确分类的复杂场景
        llm_result = await self._call_llm(text, command_type, payload or {})
        if llm_result:
            self._logger.info(
                f"intent_classified_by_llm: intent={llm_result.intent}, confidence={llm_result.confidence}"
            )
            return llm_result

        # 第四步：启发式兜底（次级路径）
        # LLM失败但启发式有结果时，即使置信度较低也使用
        if heuristic_result:
            return heuristic_result

        # 第五步：默认兜底（最终路径）
        # 所有方法都失败时的最后防线，确保系统不会崩溃
        self._logger.warning("intent_classification_fallback: %s", text[:100])
        return IntentClassification(
            intent="generation",
            confidence=0.5,
            source="fallback",
            reasoning="Unable to classify, defaulting to generation",
        )

    def _extract_text(self, payload: dict[str, Any]) -> str | None:
        """
        从payload中智能提取用户输入文本

        支持多种常见的字段名和嵌套结构，提高系统的适配性和容错性。
        这种灵活的提取策略允许系统与不同的前端和API格式兼容。

        提取策略：
        1. 尝试常见的顶层字段名（按优先级排序）
        2. 检查嵌套的context对象中的字段
        3. 返回第一个找到的非空字符串值

        设计理由：
        - 兼容性：不同模块可能使用不同的字段名
        - 健壮性：即使payload结构变化也能正常工作
        - 调试友好：详细的日志记录便于问题排查

        Args:
            payload: 包含用户输入的字典，可能包含嵌套结构

        Returns:
            str | None: 提取到的文本内容，如果未找到返回None
        """
        # 按优先级尝试多个可能的字段名
        # 顺序反映了字段名的常见程度和语义明确性
        candidates = [
            payload.get("user_input"),  # 最明确的字段名
            payload.get("input"),  # 通用输入字段
            payload.get("content"),  # 内容字段
            payload.get("text"),  # 文本字段
            payload.get("prompt"),  # 提示词字段
            payload.get("message"),  # 消息字段
        ]

        # 记录候选字段的类型信息，便于调试字段名不匹配的问题
        self._logger.debug(
            f"intent_classifier_extract_candidates: "
            f"user_input={type(payload.get('user_input')).__name__ if 'user_input' in payload else 'missing'}, "
            f"input={type(payload.get('input')).__name__ if 'input' in payload else 'missing'}, "
            f"content={type(payload.get('content')).__name__ if 'content' in payload else 'missing'}"
        )

        # 检查嵌套的context对象
        # 某些系统将用户输入包装在context字段中
        if "context" in payload and isinstance(payload["context"], dict):
            context = payload["context"]
            candidates.extend([context.get("user_input"), context.get("prompt"), context.get("message")])

        # 遍历所有候选值，返回第一个有效的字符串
        for idx, value in enumerate(candidates):
            if isinstance(value, str) and value.strip():
                # 找到有效文本，记录位置和长度
                self._logger.debug(f"intent_classifier_text_found_at_index: {idx}, length={len(value)}")
                return value.strip()

        # 所有候选值都无效时记录详细信息
        self._logger.debug("intent_classifier_no_text_found: all candidates were non-string or empty")
        return None

    def _run_heuristics(self, text: str, payload: dict[str, Any]) -> IntentClassification | None:
        """
        基于规则的启发式分类 - 快速且准确的模式匹配

        使用预定义的正则表达式模式对用户输入进行特征匹配。
        这种方法在处理明确表达的意图时非常准确，且响应速度极快（毫秒级）。

        分类策略：
        1. 模式匹配：统计命中的特征模式数量
        2. 分数计算：根据匹配数量计算置信度
        3. 意图提示：支持外部提供的意图提示作为补充判断

        置信度计算公式：
        - 基础置信度：0.6
        - 每个匹配模式增加：0.1
        - 上限：0.9（留出空间给LLM提供更高置信度）

        支持的特征模式：
        - 查询特征：疑问词、查询动词、状态询问、问号结尾
        - 生成特征：创建动词、继续动词、内容类型词
        - 中英文双语支持

        Args:
            text: 用户输入文本
            payload: 额外的上下文信息，可能包含intent_hint字段

        Returns:
            IntentClassification | None: 分类结果，如果无法确定则返回None
        """
        text_lower = text.lower()

        # 查询意图的强特征模式集合
        # 包含疑问句式、查询动词、状态询问等典型特征
        inquiry_patterns = [
            # 疑问词开头 - 中文常见疑问词
            r"^(什么|怎么|为什么|哪个|谁|何时|哪里|多少)",
            # 疑问词开头 - 英文常见疑问词
            r"^(what|how|why|which|who|when|where)",
            # 查询动词 - 中文
            r"(查看|显示|展示|列出|获取|了解|检查|查询|搜索)",
            # 查询动词 - 英文
            r"(show|display|list|get|check|search|find|query|look)",
            # 状态询问 - 中文
            r"(进度|状态|情况|结果)",
            # 状态询问 - 英文
            r"(progress|status|state|result)",
            # 问号结尾 - 中英文问号都支持
            r"[?？]$",
        ]

        # 生成意图的强特征模式集合
        # 包含创建动词、继续动词、内容类型等典型特征
        generation_patterns = [
            # 创建动词 - 中文
            r"(生成|创建|创作|写|设计|构建|制作|创造)",
            # 创建动词 - 英文
            r"(generate|create|write|design|build|make|construct)",
            # 继续动词 - 中文
            r"(继续|接着|延续|扩展|接下来)",
            # 继续动词 - 英文
            r"(continue|proceed|extend|next)",
            # 内容类型 - 中文小说创作领域术语
            r"(角色|情节|世界观|章节|场景|对话|故事|小说)",
            # 内容类型 - 英文小说创作领域术语
            r"(character|plot|world|chapter|scene|dialogue|story|novel)",
        ]

        # 计算匹配分数 - 统计命中的模式数量
        inquiry_score = sum(1 for pattern in inquiry_patterns if re.search(pattern, text_lower, re.IGNORECASE))

        generation_score = sum(1 for pattern in generation_patterns if re.search(pattern, text_lower, re.IGNORECASE))

        # 根据分数判断意图类型
        if inquiry_score > generation_score:
            # 查询意图占优：匹配了更多查询特征
            # 置信度计算：基础0.6 + 每个匹配0.1，上限0.9
            confidence = min(0.9, 0.6 + inquiry_score * 0.1)
            return IntentClassification(
                intent="inquiry",
                confidence=confidence,
                source="heuristic",
                reasoning=f"Matched {inquiry_score} inquiry patterns",
            )
        elif generation_score > 0:
            # 生成意图占优：匹配了更多生成特征
            # 即使只匹配一个生成特征，只要没有查询特征也视为生成意图
            confidence = min(0.9, 0.6 + generation_score * 0.1)
            return IntentClassification(
                intent="generation",
                confidence=confidence,
                source="heuristic",
                reasoning=f"Matched {generation_score} generation patterns",
            )

        # 检查payload中的意图提示
        # 允许外部系统显式指定意图类型，作为额外的分类依据
        hint = payload.get("intent_hint")
        if isinstance(hint, str):
            normalized = hint.strip().lower()
            if normalized in {"inquiry", "query", "question"}:
                # 明确的查询意图提示
                return IntentClassification(
                    intent="inquiry", confidence=0.7, source="heuristic", reasoning="Intent hint provided"
                )
            elif normalized in {"generation", "create", "generate"}:
                # 明确的生成意图提示
                return IntentClassification(
                    intent="generation", confidence=0.7, source="heuristic", reasoning="Intent hint provided"
                )

        # 无法通过启发式规则确定意图
        return None

    async def _call_llm(
        self, text: str, command_type: str | None, payload: dict[str, Any]
    ) -> IntentClassification | None:
        """
        调用LLM进行意图分类 - 语义理解的智能路径

        当启发式规则无法提供高置信度分类时，使用语言模型进行深度语义分析。
        LLM能够理解复杂的上下文、隐含的意图和模糊的表达方式。

        实现细节：
        1. 提示词工程：使用结构化的系统提示词引导模型输出
        2. 低温度采样：temperature=0.1确保输出的一致性和可预测性
        3. 限制输出长度：max_tokens=200足够返回分类结果，避免过长响应
        4. 结构化输入：将用户输入和上下文打包为JSON格式

        容错处理：
        - LLM服务不可用时返回None，降级使用其他策略
        - 调用失败时记录警告日志但不抛出异常
        - 确保分类器在LLM故障时仍能正常工作

        Args:
            text: 用户输入文本
            command_type: 命令类型（可选），提供额外的上下文信息
            payload: 完整的上下文信息字典

        Returns:
            IntentClassification | None: 分类结果，如果LLM不可用或调用失败返回None
        """
        if self._llm_service is None:
            # LLM服务未初始化，静默返回None
            return None

        # 构建系统提示词
        # 使用清晰的分类标准和示例，引导模型输出结构化JSON
        system_prompt = """你是一个意图分类器，需要判断用户输入属于以下两类之一：

1. inquiry（查询类）- 用户想要获取信息、查看状态、了解情况
   特征：疑问句、查询动词、请求解释或说明

2. generation（生成类）- 用户想要创建新内容、继续创作
   特征：创建动词、内容类型词、继续或扩展请求

请分析用户输入，只返回JSON格式：
{"intent": "inquiry或generation", "confidence": 0-1之间的数值, "reasoning": "判断理由"}
"""

        # 构建用户消息
        # 打包用户输入和上下文信息，为LLM提供完整的分类依据
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
            temperature=0.1,  # 低温度以获得更一致的结果，减少随机性
            max_tokens=200,  # 限制输出长度，分类结果通常很短
        )

        try:
            response = await self._llm_service.generate(request)
            return self._parse_llm_response(response)
        except Exception as exc:
            # LLM调用失败时记录警告，但不中断分类流程
            # 允许降级到其他分类策略
            self._logger.warning("intent_classifier_llm_failed: %s", exc)
            return None

    def _parse_llm_response(self, response: LLMResponse) -> IntentClassification | None:
        """
        解析LLM返回的JSON响应

        处理LLM可能返回的各种格式，包括纯JSON、带文本包装的JSON、格式错误的JSON等。
        采用多层解析策略确保最大程度地提取有效信息。

        解析策略：
        1. 直接JSON解析：尝试将整个响应作为JSON解析
        2. 正则提取：如果直接解析失败，尝试从文本中提取JSON部分
        3. 字段验证：验证必需字段的存在和有效性
        4. 数值规范化：确保置信度在[0.0, 1.0]范围内

        容错处理：
        - 空响应：返回None
        - JSON格式错误：尝试正则提取
        - 意图类型无效：返回None
        - 置信度无效：使用默认值0.5
        - 推理理由缺失：使用空字符串

        Args:
            response: LLM服务返回的响应对象

        Returns:
            IntentClassification | None: 解析成功返回分类结果，失败返回None
        """
        raw = (response.content or "").strip()
        if not raw:
            # 空响应直接返回None
            return None

        try:
            # 第一次尝试：直接解析整个响应为JSON
            data = json.loads(raw)
        except json.JSONDecodeError:
            # 第二次尝试：从文本中提取JSON部分
            # LLM有时会在JSON前后添加额外说明文本
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                # 无法找到有效的JSON结构
                return None
            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError:
                # JSON格式仍然无效
                return None

        # 提取和验证意图类型
        # 必须是"inquiry"或"generation"之一
        intent = str(data.get("intent", "")).strip().lower()
        if intent not in {"inquiry", "generation"}:
            # 意图类型无效
            return None

        # 提取置信度并规范化到[0.0, 1.0]范围
        try:
            confidence = float(data.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))  # 限制在0-1范围
        except (TypeError, ValueError):
            # 置信度格式错误时使用默认值
            confidence = 0.5

        # 提取推理理由（可选字段）
        reasoning = data.get("reasoning", "")

        return IntentClassification(
            intent=intent,  # type: ignore[arg-type]
            confidence=confidence,
            source="llm",
            reasoning=reasoning,
            raw_response=raw,  # 保留原始响应便于调试
        )

    def is_high_confidence(self, result: IntentClassification) -> bool:
        """
        检查分类结果是否具有高置信度

        用于判断分类结果的可靠性，帮助决策是否需要进一步确认或采取额外措施。
        高置信度的分类结果可以直接使用，低置信度结果可能需要人工审核或提示用户确认。

        判定标准：
        - 置信度 >= CONFIDENCE_THRESHOLD (0.7) 视为高置信度
        - 这个阈值平衡了准确性和可用性

        使用场景：
        - 决定是否显示确认对话框
        - 判断是否记录额外的审计日志
        - 决定是否触发人工审核流程

        Args:
            result: 意图分类结果对象

        Returns:
            bool: True表示高置信度，False表示低置信度
        """
        return result.confidence >= self.CONFIDENCE_THRESHOLD
