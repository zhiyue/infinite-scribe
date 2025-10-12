"""Orchestrator 编排代理模块

该模块提供编排代理(OrchestratorAgent)的核心实现和注册功能。
编排代理负责协调多个专业代理之间的工作流程,包括:
- 接收用户请求并分析意图
- 根据意图路由到相应的专业代理
- 管理代理间的协作和数据流转
- 聚合多个代理的响应结果

模块初始化时会自动将 OrchestratorAgent 注册到全局代理注册表中,
使其可以被代理工厂和服务发现机制使用。
"""

from __future__ import annotations

from src.agents.orchestrator.agent import OrchestratorAgent
from src.agents.registry import register_agent

# 在模块导入时自动注册编排代理
# 这确保了编排代理在应用启动时即可被服务发现和代理工厂识别
register_agent("orchestrator", OrchestratorAgent)

__all__ = ["OrchestratorAgent"]
