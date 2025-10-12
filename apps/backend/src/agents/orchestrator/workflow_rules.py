"""工作流编排的业务规则接口

本模块通过提供清晰的工作流决策接口,将业务逻辑与 JSON 配置解耦。
这种设计使得业务规则可以独立于配置文件进行测试和维护。

核心设计理念:
- 接口抽象: 定义业务规则的标准接口,支持多种实现方式
- 配置解耦: 将业务决策逻辑与配置数据结构分离
- 灵活扩展: 支持从配置文件过渡到代码内嵌规则
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .workflow_constants import WORKFLOW_DEFAULTS


class ReviewResult(Enum):
    """质量或一致性审核的结果枚举

    定义了三种可能的审核结果,用于指导后续的工作流动作:
    - APPROVED: 审核通过,内容符合质量标准
    - REJECTED_RETRY: 审核未通过但可重试,触发内容重新生成
    - REJECTED_FAILED: 审核未通过且达到最大重试次数,标记为失败
    """

    APPROVED = "approved"  # 审核通过
    REJECTED_RETRY = "rejected_retry"  # 未通过,但可重试
    REJECTED_FAILED = "rejected_failed"  # 未通过,已达最大重试次数


@dataclass
class QualityReviewRequest:
    """质量审核请求的数据结构

    封装质量审核决策所需的所有输入参数,使决策逻辑更清晰。

    Attributes:
        score: 当前内容的质量评分(0.0-1.0)
        attempts: 当前已尝试的生成次数(从0开始)
        max_attempts: 允许的最大尝试次数
        threshold: 质量通过的阈值分数
        target_type: 目标内容类型(如 'Chapter', 'Scene'),用于确定对应的工作流动作
    """

    score: float
    attempts: int
    max_attempts: int
    threshold: float
    target_type: str


@dataclass
class WorkflowDecision:
    """工作流规则的决策结果

    包含审核结果、后续动作和决策原因,用于指导工作流的下一步操作。

    Attributes:
        result: 审核结果(通过/重试/失败)
        action: 需要执行的下一步动作(如 'Chapter.Confirmed', 'Chapter.RegenerationRequested')
        reason: 决策原因的详细说明,用于日志记录和调试
    """

    result: ReviewResult
    action: str
    reason: str | None = None


class IWorkflowRules(ABC):
    """工作流业务规则的抽象接口

    该接口将工作流决策从配置细节中抽象出来,使业务逻辑专注于行为而非数据结构。
    通过定义标准接口,支持多种实现方式(基于配置文件或静态代码)。

    设计目的:
    - 隔离变化: 配置结构变化不影响业务逻辑
    - 便于测试: 可轻松 mock 规则实现进行单元测试
    - 灵活切换: 支持在配置驱动和代码驱动之间切换
    """

    @abstractmethod
    def get_target_for_event(self, event_type: str) -> str | None:
        """根据生成事件类型获取目标内容类型

        Args:
            event_type: 事件类型(如 'ChapterGenerated', 'SceneGenerated')

        Returns:
            目标类型(如 'Chapter', 'Scene'),若事件类型未知则返回 None
        """

    @abstractmethod
    def get_task_prefix(self, task_type: str) -> str:
        """获取任务类型对应的前缀标识

        Args:
            task_type: 任务类型(如 'quality_review', 'consistency_check')

        Returns:
            任务前缀字符串(如 'Review.Quality.Evaluation')
        """

    @abstractmethod
    def evaluate_quality_review(self, request: QualityReviewRequest) -> WorkflowDecision:
        """评估质量审核并返回决策结果

        核心业务逻辑:根据评分、阈值和重试次数决定下一步动作。

        Args:
            request: 质量审核请求,包含评分、重试次数等信息

        Returns:
            工作流决策,包含审核结果和后续动作
        """

    @abstractmethod
    def get_confirmation_action(self, target_type: str) -> str:
        """获取目标类型的确认动作

        Args:
            target_type: 目标内容类型(如 'Chapter', 'Scene')

        Returns:
            确认动作字符串(如 'Chapter.Confirmed')
        """

    @abstractmethod
    def get_failure_action(self, target_type: str) -> str:
        """获取目标类型的失败动作

        Args:
            target_type: 目标内容类型

        Returns:
            失败动作字符串(如 'Chapter.Failed')
        """

    @abstractmethod
    def get_regeneration_action(self, target_type: str) -> str:
        """获取目标类型的重新生成动作

        Args:
            target_type: 目标内容类型

        Returns:
            重新生成动作字符串(如 'Chapter.RegenerationRequested')
        """

    @abstractmethod
    def should_confirm_consistency(self, result_data: dict[str, Any]) -> bool:
        """判断一致性检查结果是否应确认

        支持多种判断方式:布尔值(ok/passed)或分数比较(score >= threshold)。

        Args:
            result_data: 一致性检查的结果数据

        Returns:
            True 表示一致性检查通过,False 表示未通过
        """


class ConfigBasedWorkflowRules(IWorkflowRules):
    """基于配置文件的工作流规则实现

    作为过渡期的桥接实现,连接新的业务规则接口和现有的配置系统。
    允许系统在迁移到静态规则之前继续使用 JSON 配置文件。

    设计权衡:
    - 向后兼容: 支持现有配置文件,减少迁移风险
    - 灵活性: 允许通过修改配置文件调整规则,无需重新部署
    - 维护成本: 配置文件和代码需要保持同步
    """

    def __init__(self, config: Any) -> None:
        """初始化配置驱动的规则实现

        Args:
            config: 现有的配置对象,包含事件映射、任务前缀等配置项
        """
        self._config = config

    def get_target_for_event(self, event_type: str) -> str | None:
        """根据生成事件类型获取目标内容类型

        从配置对象的 EVENT_TARGET_MAPPING 中查找映射关系。

        Args:
            event_type: 事件类型

        Returns:
            目标类型,若未配置则返回 None
        """
        return self._config.EVENT_TARGET_MAPPING.get(event_type)

    def get_task_prefix(self, task_type: str) -> str:
        """获取任务类型对应的前缀标识

        优先使用配置文件中的映射,若未配置则使用默认映射。

        Args:
            task_type: 任务类型

        Returns:
            任务前缀字符串
        """
        # 提供默认映射作为后备,确保常用任务类型有合理的前缀
        default_mapping = {
            "quality_review": "Review.Quality.Evaluation",
            "consistency_check": "Review.Consistency.Check",
        }
        return self._config.TASK_PREFIX_MAPPING.get(task_type, default_mapping.get(task_type, "Unknown"))

    def evaluate_quality_review(self, request: QualityReviewRequest) -> WorkflowDecision:
        """评估质量审核并返回决策结果

        实现三阶段决策逻辑:
        1. 质量通过 → 确认内容
        2. 达到最大重试次数 → 标记失败
        3. 质量未达标但可重试 → 触发重新生成

        Args:
            request: 质量审核请求

        Returns:
            包含决策结果和后续动作的决策对象
        """
        # 第一优先级: 质量达标,确认内容并进入下一阶段
        if request.score >= request.threshold:
            action = self.get_confirmation_action(request.target_type)
            return WorkflowDecision(
                result=ReviewResult.APPROVED,
                action=action,
                reason=f"Score {request.score} >= threshold {request.threshold}",
            )

        # 第二优先级: 已达最大重试次数,停止重试并标记失败
        # 注意: attempts + 1 是因为 attempts 从 0 开始计数
        if request.attempts + 1 >= request.max_attempts:
            action = self.get_failure_action(request.target_type)
            return WorkflowDecision(
                result=ReviewResult.REJECTED_FAILED,
                action=action,
                reason=f"Max attempts ({request.max_attempts}) reached",
            )

        # 第三优先级: 质量未达标但仍有重试机会,触发内容重新生成
        action = self.get_regeneration_action(request.target_type)
        return WorkflowDecision(
            result=ReviewResult.REJECTED_RETRY,
            action=action,
            reason=f"Score {request.score} < threshold {request.threshold}, attempts: {request.attempts + 1}",
        )

    def get_confirmation_action(self, target_type: str) -> str:
        """获取目标类型的确认动作

        从配置中查找确认动作,若未配置则使用通用默认值。

        Args:
            target_type: 目标内容类型

        Returns:
            确认动作字符串
        """
        return self._config.TARGET_CONFIRMATION_ACTIONS.get(target_type, "Stage.Confirmed")

    def get_failure_action(self, target_type: str) -> str:
        """获取目标类型的失败动作

        从配置中查找失败动作,若未配置则使用通用默认值。

        Args:
            target_type: 目标内容类型

        Returns:
            失败动作字符串
        """
        return self._config.TARGET_FAILURE_ACTIONS.get(target_type, "Stage.Failed")

    def get_regeneration_action(self, target_type: str) -> str:
        """获取目标类型的重新生成动作

        从配置中查找重新生成动作,若未配置则使用通用默认值。

        Args:
            target_type: 目标内容类型

        Returns:
            重新生成动作字符串
        """
        return self._config.TARGET_REGENERATION_ACTIONS.get(target_type, "Stage.RegenerationRequested")

    def should_confirm_consistency(self, result_data: dict[str, Any]) -> bool:
        """判断一致性检查结果是否应确认

        支持三种判断方式,按优先级依次尝试:
        1. 布尔字段: ok 或 passed 为 True
        2. 分数比较: score >= threshold
        3. 类型转换失败时返回 False

        Args:
            result_data: 一致性检查的结果数据

        Returns:
            True 表示一致性检查通过
        """
        # 优先检查布尔字段,兼容不同的结果格式
        ok = bool(result_data.get("ok") or result_data.get("passed"))
        if not ok:
            # 布尔字段为 False 时,尝试分数比较
            score = result_data.get("score", 0.0)
            threshold = result_data.get("threshold", 1.0)
            try:
                ok = float(score) >= float(threshold)
            except (ValueError, TypeError):
                # 类型转换失败时返回 False,避免异常导致整个流程中断
                # 这是一种容错设计,确保系统在数据格式异常时仍能继续运行
                ok = False
        return ok


class StaticWorkflowRules(IWorkflowRules):
    """静态工作流规则实现,无需外部配置文件

    将业务规则直接嵌入代码中,消除对 JSON 配置文件的依赖。
    使用集中化的常量定义避免硬编码值,便于维护。

    设计优势:
    - 性能: 无配置文件读取开销,启动更快
    - 可靠性: 避免配置文件丢失或格式错误导致的运行时错误
    - 类型安全: 利用 IDE 和类型检查工具发现错误
    - 版本控制: 规则变更与代码一起管理,便于回溯

    适用场景:
    - 规则相对稳定,不需要频繁调整
    - 部署环境标准化,无需针对不同环境调整规则
    - 追求更高的运行时性能和可靠性
    """

    def get_target_for_event(self, event_type: str) -> str | None:
        """根据生成事件类型获取目标内容类型

        使用 WORKFLOW_DEFAULTS 中的静态映射关系。

        Args:
            event_type: 事件类型

        Returns:
            目标类型,若事件类型未知则返回 None
        """
        return WORKFLOW_DEFAULTS.EVENT_TARGET_MAPPING.get(event_type)

    def get_task_prefix(self, task_type: str) -> str:
        """获取任务类型对应的前缀标识

        使用预定义的常量构建映射,避免在多处重复字符串字面量。

        Args:
            task_type: 任务类型

        Returns:
            任务前缀字符串
        """
        # 使用常量而非字符串字面量,便于统一管理和修改
        task_mapping = {
            "quality_review": WORKFLOW_DEFAULTS.QUALITY_REVIEW_PREFIX,
            "consistency_check": WORKFLOW_DEFAULTS.CONSISTENCY_CHECK_PREFIX,
        }
        return task_mapping.get(task_type, "Unknown")

    def evaluate_quality_review(self, request: QualityReviewRequest) -> WorkflowDecision:
        """评估质量审核并返回决策结果

        实现与 ConfigBasedWorkflowRules 相同的三阶段决策逻辑,
        但使用静态默认值替代配置文件中的阈值。

        Args:
            request: 质量审核请求

        Returns:
            包含决策结果和后续动作的决策对象
        """
        # 使用请求中的值,若未提供则回退到预定义的默认值
        # 这种设计允许在特定场景下覆盖默认配置,同时保持整体一致性
        threshold = request.threshold or WORKFLOW_DEFAULTS.QUALITY_THRESHOLD
        max_attempts = request.max_attempts or WORKFLOW_DEFAULTS.MAX_ATTEMPTS

        # 第一优先级: 质量达标,确认内容
        if request.score >= threshold:
            action = self.get_confirmation_action(request.target_type)
            return WorkflowDecision(
                result=ReviewResult.APPROVED, action=action, reason=f"Score {request.score} >= threshold {threshold}"
            )

        # 第二优先级: 已达最大重试次数,标记失败
        if request.attempts + 1 >= max_attempts:
            action = self.get_failure_action(request.target_type)
            return WorkflowDecision(
                result=ReviewResult.REJECTED_FAILED, action=action, reason=f"Max attempts ({max_attempts}) reached"
            )

        # 第三优先级: 质量未达标但可重试,触发重新生成
        action = self.get_regeneration_action(request.target_type)
        return WorkflowDecision(
            result=ReviewResult.REJECTED_RETRY,
            action=action,
            reason=f"Score {request.score} < threshold {threshold}, attempts: {request.attempts + 1}",
        )

    def get_confirmation_action(self, target_type: str) -> str:
        """获取目标类型的确认动作

        从 WORKFLOW_DEFAULTS 的静态映射中查找。

        Args:
            target_type: 目标内容类型

        Returns:
            确认动作字符串
        """
        return WORKFLOW_DEFAULTS.CONFIRMATION_ACTIONS.get(target_type, "Stage.Confirmed")

    def get_failure_action(self, target_type: str) -> str:
        """获取目标类型的失败动作

        从 WORKFLOW_DEFAULTS 的静态映射中查找。

        Args:
            target_type: 目标内容类型

        Returns:
            失败动作字符串
        """
        return WORKFLOW_DEFAULTS.FAILURE_ACTIONS.get(target_type, "Stage.Failed")

    def get_regeneration_action(self, target_type: str) -> str:
        """获取目标类型的重新生成动作

        从 WORKFLOW_DEFAULTS 的静态映射中查找。

        Args:
            target_type: 目标内容类型

        Returns:
            重新生成动作字符串
        """
        return WORKFLOW_DEFAULTS.REGENERATION_ACTIONS.get(target_type, "Stage.RegenerationRequested")

    def should_confirm_consistency(self, result_data: dict[str, Any]) -> bool:
        """判断一致性检查结果是否应确认

        实现与 ConfigBasedWorkflowRules 相同的判断逻辑,
        但在缺少 threshold 时使用静态默认值。

        支持三种判断方式:
        1. 布尔字段: ok 或 passed 为 True
        2. 分数比较: score >= threshold
        3. 类型转换失败时返回 False

        Args:
            result_data: 一致性检查的结果数据

        Returns:
            True 表示一致性检查通过
        """
        # 优先检查布尔字段
        ok = bool(result_data.get("ok") or result_data.get("passed"))
        if not ok:
            # 尝试分数比较,若结果数据中未提供阈值则使用默认值
            score = result_data.get("score", 0.0)
            threshold = result_data.get("threshold", WORKFLOW_DEFAULTS.CONSISTENCY_THRESHOLD)
            try:
                ok = float(score) >= float(threshold)
            except (ValueError, TypeError):
                # 容错处理:类型转换失败时返回 False
                # 避免因数据格式问题导致工作流中断
                ok = False
        return ok
