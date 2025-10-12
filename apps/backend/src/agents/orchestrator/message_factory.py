"""消息工厂 - 通用消息模式的创建工具

提供用于创建编排器中常用消息结构的工具方法，
减少代码重复并集中管理消息格式逻辑。

该工厂类封装了质量评审、内容重生成等核心工作流中的消息创建逻辑，
确保消息格式的一致性和可维护性。
"""

from __future__ import annotations

from typing import Any

from src.common.events.config import get_message_type, get_strategy_config


class MessageFactory:
    """消息工厂类 - 创建编排器中常用的消息类型

    使用工厂模式集中管理消息创建逻辑，提供静态方法用于生成标准化的消息结构。
    所有方法都是无状态的，可以直接通过类名调用。

    主要功能:
    - 创建质量评审请求消息
    - 创建内容重生成任务消息
    - 生成标准化的动作名称（确认、失败、重生成）
    """

    @staticmethod
    def create_quality_review_message(
        session_id: str, target_type: str, content: dict[str, Any], scope_prefix: str
    ) -> dict[str, Any]:
        """创建质量评审请求消息

        生成用于触发内容质量评审流程的标准消息结构。
        该消息将被路由到质量评审服务进行内容质量验证。

        Args:
            session_id: 会话标识符，用于关联整个处理流程
            target_type: 被评审内容的类型（如 character、theme 等）
            content: 待评审的内容数据
            scope_prefix: 范围前缀，用于消息主题路由（如 genesis、development）

        Returns:
            格式化的质量评审消息字典，包含消息类型、会话ID、目标类型、
            输入内容以及路由信息（_topic、_key）
        """
        # 从配置中获取阶段验证策略，确定评审服务的主题基础名称
        review_config = get_strategy_config("stage_validation")
        base_topic = review_config["base_topic"] if review_config else "review"

        # 构建并返回标准化的能力任务消息
        # 运行时返回字典结构，类型提示为 CapabilityTaskMessage
        return {
            "type": get_message_type("quality_review"),  # 质量评审消息类型
            "session_id": session_id,
            "target_type": target_type,
            "input": {"content": content},
            # 主题格式: {scope}.{base_topic}.tasks (如 genesis.review.tasks)
            "_topic": f"{scope_prefix.lower()}.{base_topic}.tasks",
            "_key": session_id,  # 使用会话ID作为消息分区键，保证同会话消息有序
        }

    @staticmethod
    def create_regeneration_message(
        target_type: str, session_id: str, attempts: int, scope_prefix: str
    ) -> dict[str, Any] | None:
        """创建内容重生成任务消息

        当内容质量评审未通过时，创建用于重新生成内容的任务消息。
        根据目标类型自动选择合适的生成策略和提示词调整方式。

        Args:
            target_type: 待重生成内容的类型（character、theme等）
            session_id: 会话标识符
            attempts: 当前尝试次数（用于生成递增的attempt参数）
            scope_prefix: 范围前缀，用于消息主题路由

        Returns:
            格式化的重生成任务消息字典，如果目标类型不支持则返回None
        """
        # 根据目标类型获取对应的策略配置（包含能力类型和主题信息）
        strategy_config = get_strategy_config(target_type)
        if not strategy_config:
            # 不支持的内容类型，无法创建重生成消息
            return None

        # 使用配置驱动的方式构建重生成消息
        return {
            "type": strategy_config["capability_type"],  # 从策略配置获取能力类型
            "session_id": session_id,
            "input": {
                # 根据内容类型选择提示词调整策略
                # character使用结构化调整，其他类型使用详细调整
                "prompt_adjust": "structured" if target_type == "character" else "detailed",
                "attempt": attempts + 1,  # 递增尝试次数
            },
            # 主题格式: {scope}.{base_topic}.tasks
            "_topic": f"{scope_prefix.lower()}.{strategy_config['base_topic']}.tasks",
            "_key": session_id,  # 使用会话ID作为分区键
        }

    @staticmethod
    def get_confirmation_action(target_type: str) -> str:
        """获取指定内容类型的确认动作名称

        根据内容类型生成标准化的确认动作名称，用于表示内容已通过验证。
        不同类型的内容使用不同的命名空间以保持语义清晰。

        Args:
            target_type: 被确认的内容类型（character、theme等）

        Returns:
            格式化的确认动作名称
            - 特定类型: "{Type}.Confirmed" (如 Character.Confirmed)
            - 默认类型: "Stage.Confirmed"
        """
        # character和theme使用特定类型的确认动作，其他使用通用的阶段确认
        return f"{target_type.capitalize()}.Confirmed" if target_type in {"character", "theme"} else "Stage.Confirmed"

    @staticmethod
    def get_failure_action(target_type: str) -> str:
        """获取指定内容类型的失败动作名称

        根据内容类型生成标准化的失败动作名称，用于表示内容处理失败。
        与确认动作保持一致的命名规则，便于统一管理状态转换。

        Args:
            target_type: 失败的内容类型（character、theme等）

        Returns:
            格式化的失败动作名称
            - 特定类型: "{Type}.Failed" (如 Character.Failed)
            - 默认类型: "Stage.Failed"
        """
        # character和theme使用特定类型的失败动作，其他使用通用的阶段失败
        return f"{target_type.capitalize()}.Failed" if target_type in {"character", "theme"} else "Stage.Failed"

    @staticmethod
    def get_regeneration_action(target_type: str) -> str:
        """获取指定内容类型的重生成请求动作名称

        根据内容类型生成标准化的重生成请求动作名称，用于表示需要重新生成内容。
        该动作通常在质量评审失败后触发，启动内容重生成流程。

        Args:
            target_type: 需要重生成的内容类型（character、theme等）

        Returns:
            格式化的重生成请求动作名称
            - 特定类型: "{Type}.RegenerationRequested" (如 Character.RegenerationRequested)
            - 默认类型: "Stage.RegenerationRequested"
        """
        # character和theme使用特定类型的重生成动作，其他使用通用的阶段重生成
        return (
            f"{target_type.capitalize()}.RegenerationRequested"
            if target_type in {"character", "theme"}
            else "Stage.RegenerationRequested"
        )
