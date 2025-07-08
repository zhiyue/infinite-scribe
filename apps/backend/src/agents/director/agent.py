"""Director Agent 实现"""

import logging
from typing import Any

from ..base import BaseAgent

logger = logging.getLogger(__name__)


class DirectorAgent(BaseAgent):
    """Director Agent - 负责协调和指导创作流程"""

    def __init__(self):
        # 定义消费和生产的 Kafka 主题
        consume_topics = [
            "project.start.request",  # 项目启动请求
            "project.status.request",  # 项目状态查询
            "agent.coordination.request",  # Agent 协调请求
        ]
        produce_topics = [
            "agent.task.assignment",  # 任务分配
            "project.status.update",  # 项目状态更新
            "story.outline.request",  # 大纲请求(发给 outliner)
        ]

        super().__init__(name="director", consume_topics=consume_topics, produce_topics=produce_topics)

    async def process_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """处理消息"""
        message_type = message.get("type")
        logger.info(f"Director agent 处理消息类型: {message_type}")

        if message_type == "start_project":
            return await self._handle_start_project(message)
        elif message_type == "review_progress":
            return await self._handle_review_progress(message)
        elif message_type == "coordinate_agents":
            return await self._handle_coordinate_agents(message)
        else:
            logger.warning(f"未知的消息类型: {message_type}")
            return None

    async def _handle_start_project(self, message: dict[str, Any]) -> dict[str, Any]:
        """处理项目启动"""
        project_id = message.get("project_id")
        project_config = message.get("config", {})

        logger.info(f"启动新项目: {project_id}")

        # TODO: 实现项目启动逻辑
        # 1. 创建项目记录
        # 2. 初始化项目状态
        # 3. 分配初始任务

        # 发送大纲创建请求给 outliner
        outline_request = {
            "type": "create_outline",
            "project_id": project_id,
            "genre": project_config.get("genre"),
            "theme": project_config.get("theme"),
            "_topic": "story.outline.request",
        }

        return outline_request

    async def _handle_review_progress(self, message: dict[str, Any]) -> dict[str, Any]:
        """处理进度审查"""
        project_id = message.get("project_id")

        logger.info(f"审查项目进度: {project_id}")

        # TODO: 实现进度审查逻辑
        # 1. 收集各 agent 的状态
        # 2. 汇总进度信息
        # 3. 生成进度报告

        return {
            "type": "progress_report",
            "project_id": project_id,
            "status": "in_progress",
            "completion": 45,
            "_topic": "project.status.update",
        }

    async def _handle_coordinate_agents(self, message: dict[str, Any]) -> dict[str, Any]:
        """处理 agent 协调"""
        task_type = message.get("task_type")
        agents_involved = message.get("agents", [])

        logger.info(f"协调任务: {task_type}, 涉及 agents: {agents_involved}")

        # TODO: 实现 agent 协调逻辑
        # 1. 分析任务需求
        # 2. 确定执行顺序
        # 3. 分配具体任务

        return {
            "type": "task_assigned",
            "assignments": [
                {"agent": "writer", "task": "write_chapter", "priority": 1},
                {"agent": "critic", "task": "review_chapter", "priority": 2},
            ],
            "_topic": "agent.task.assignment",
        }

    async def on_start(self):
        """启动时的初始化"""
        logger.info("Director agent 正在初始化...")
        # TODO: 加载项目状态、初始化资源等

    async def on_stop(self):
        """停止时的清理"""
        logger.info("Director agent 正在清理资源...")
        # TODO: 保存状态、释放资源等
