"""工作流常量定义模块

本模块集中管理编排器(Orchestrator)工作流的所有常量配置,避免在代码库中使用硬编码值。
这些常量用于质量审查、一致性检查、事件路由和工作流状态转换等核心业务逻辑。
"""

from typing import Final


class WorkflowDefaults:
    """工作流默认配置类

    定义编排器工作流中使用的所有默认值和映射关系,包括:
    - 质量评审阈值: 用于判断生成内容是否达到质量标准
    - 任务前缀: 用于在分布式任务系统中标识特定类型的审查任务
    - 事件映射: 将业务事件映射到对应的目标实体类型
    - 动作映射: 定义不同工作流状态下的事件类型(确认、失败、重新生成)
    """

    # === 质量控制阈值 ===
    # 质量评分阈值,低于此值的内容需要重新生成或人工审核
    # 采用10分制评分,7.5分确保生成内容具有较高的可用性
    QUALITY_THRESHOLD: Final[float] = 7.5

    # 最大重试次数,防止无限循环重新生成
    # 3次重试是在质量保证和系统响应速度之间的平衡点
    MAX_ATTEMPTS: Final[int] = 3

    # 一致性检查阈值,用于验证生成内容与上下文的一致性程度
    # 1.0表示完全一致,适用于需要严格逻辑一致性的场景(如角色设定、主题定义)
    CONSISTENCY_THRESHOLD: Final[float] = 1.0

    # === 任务标识前缀 ===
    # 质量评审任务前缀,用于在任务队列中识别质量评估任务
    QUALITY_REVIEW_PREFIX: Final[str] = "Review.Quality.Evaluation"

    # 一致性检查任务前缀,用于在任务队列中识别一致性验证任务
    CONSISTENCY_CHECK_PREFIX: Final[str] = "Review.Consistency.Check"

    # === 事件到实体类型的映射 ===
    # 将业务领域事件映射到标准化的实体类型,便于统一处理不同来源的相同类型实体
    # 这种映射模式支持多种事件格式对应同一实体,提供了灵活的事件路由机制
    EVENT_TARGET_MAPPING: Final[dict[str, str]] = {
        "Character.Design.Generated": "character",  # 角色设计生成事件
        "Character.Generated": "character",          # 角色生成完成事件
        "Outliner.Theme.Generated": "theme",        # 大纲器主题生成事件
        "Theme.Generated": "theme",                  # 主题生成完成事件
        "Inquiry.Response.Generated": "inquiry",    # 问询响应生成事件
    }

    # === 实体确认动作映射 ===
    # 定义各实体类型通过质量审查后发出的确认事件
    # 确认事件标志着内容生成工作流的成功完成
    CONFIRMATION_ACTIONS: Final[dict[str, str]] = {
        "character": "Character.Confirmed",
        "theme": "Theme.Confirmed",
        "inquiry": "Inquiry.Confirmed",
    }

    # === 实体失败动作映射 ===
    # 定义各实体类型在超过最大重试次数后仍未通过审查时发出的失败事件
    # 失败事件触发降级处理或人工介入流程
    FAILURE_ACTIONS: Final[dict[str, str]] = {
        "character": "Character.Failed",
        "theme": "Theme.Failed",
        "inquiry": "Inquiry.Failed",
    }

    # === 实体重新生成动作映射 ===
    # 定义各实体类型在质量审查失败但仍在重试限制内时发出的重新生成请求事件
    # 重新生成事件触发新一轮的内容生成流程
    REGENERATION_ACTIONS: Final[dict[str, str]] = {
        "character": "Character.RegenerationRequested",
        "theme": "Theme.RegenerationRequested",
        "inquiry": "Inquiry.RegenerationRequested",
    }


# 全局工作流常量实例
# 提供单例访问点,确保整个应用使用一致的工作流配置
WORKFLOW_DEFAULTS = WorkflowDefaults()


class WorkflowValidationError(ValueError):
    """工作流配置验证失败异常

    当工作流配置参数不符合业务规则时抛出此异常。
    继承自ValueError以保持与标准库异常体系的一致性。
    """


def validate_quality_threshold(threshold: float) -> None:
    """验证质量阈值的有效性

    质量阈值必须在0.0到10.0之间,对应10分制评分体系。
    此范围确保评分值的语义一致性和可比性。

    Args:
        threshold: 待验证的质量阈值

    Raises:
        WorkflowValidationError: 当阈值超出有效范围时抛出
    """
    if not (0.0 <= threshold <= 10.0):
        raise WorkflowValidationError(f"Quality threshold must be between 0.0 and 10.0, got {threshold}")


def validate_max_attempts(attempts: int) -> None:
    """验证最大重试次数的有效性

    重试次数必须为正整数,至少允许一次尝试。
    零或负数的重试次数在业务逻辑上无意义。

    Args:
        attempts: 待验证的最大重试次数

    Raises:
        WorkflowValidationError: 当重试次数小于1时抛出
    """
    if attempts < 1:
        raise WorkflowValidationError(f"Max attempts must be positive, got {attempts}")


def validate_consistency_threshold(threshold: float) -> None:
    """验证一致性阈值的有效性

    一致性阈值必须为非负数,0.0表示无一致性要求,值越大要求越严格。
    负数的一致性阈值在语义上不合理。

    Args:
        threshold: 待验证的一致性阈值

    Raises:
        WorkflowValidationError: 当阈值为负数时抛出
    """
    if threshold < 0.0:
        raise WorkflowValidationError(f"Consistency threshold must be non-negative, got {threshold}")


def validate_workflow_thresholds(
    quality_threshold: float, max_attempts: int, consistency_threshold: float
) -> list[str]:
    """批量验证所有工作流阈值参数

    对质量阈值、重试次数和一致性阈值进行统一验证,收集所有验证错误。
    采用非中断式验证策略,即使某个参数验证失败也会继续验证其他参数,
    最终返回完整的错误列表,便于一次性反馈所有配置问题。

    Args:
        quality_threshold: 质量评分阈值
        max_attempts: 最大重试次数
        consistency_threshold: 一致性检查阈值

    Returns:
        包含所有验证错误信息的列表,空列表表示验证通过

    Note:
        此函数不抛出异常,而是返回错误列表,由调用方决定如何处理验证结果
    """
    errors = []

    # 验证质量阈值,捕获异常并记录错误信息
    try:
        validate_quality_threshold(quality_threshold)
    except WorkflowValidationError as e:
        errors.append(str(e))

    # 验证重试次数,捕获异常并记录错误信息
    try:
        validate_max_attempts(max_attempts)
    except WorkflowValidationError as e:
        errors.append(str(e))

    # 验证一致性阈值,捕获异常并记录错误信息
    try:
        validate_consistency_threshold(consistency_threshold)
    except WorkflowValidationError as e:
        errors.append(str(e))

    return errors
