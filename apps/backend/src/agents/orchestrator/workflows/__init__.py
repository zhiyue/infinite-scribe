"""工作流配置和编排工具模块

该模块提供编排代理的工作流配置和事件处理核心组件,包括:

1. 事件操作(EventAction/EventActionBuilder):
   - 定义对事件的具体操作和响应行为
   - 提供构建器模式用于灵活构建复杂事件操作链

2. 工作流配置(WorkflowConfig/EventHandlerConfig):
   - 定义工作流的整体配置和行为规则
   - 配置特定事件类型的处理策略

3. 工作流路由(WorkflowRouting):
   - 定义事件到代理的路由规则
   - 支持基于条件的动态路由决策

4. 工作流阈值(WorkflowThresholds):
   - 定义工作流执行的性能和资源限制
   - 用于控制并发度、超时时间等关键指标

这些组件共同构成了事件驱动架构的核心配置层,
支持灵活的工作流定义和运行时行为调整。
"""

from .actions import EventAction, EventActionBuilder
from .config import EventHandlerConfig, WorkflowConfig, WorkflowRouting, WorkflowThresholds

__all__ = [
    "EventAction",
    "EventActionBuilder",
    "EventHandlerConfig",
    "WorkflowConfig",
    "WorkflowRouting",
    "WorkflowThresholds",
]
