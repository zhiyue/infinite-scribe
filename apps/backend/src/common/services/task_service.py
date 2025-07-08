"""
异步任务管理服务

管理创世流程中的异步任务,包括任务创建、进度更新、状态管理等。
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from src.common.services.postgres_service import postgres_service
from src.common.services.sse_service import sse_service

logger = logging.getLogger(__name__)


class TaskStatus:
    """任务状态常量"""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class GenesisTaskType:
    """创世任务类型常量"""

    CONCEPT_GENERATION = "concept_generation"
    CONCEPT_REFINEMENT = "concept_refinement"
    STORY_GENERATION = "story_generation"
    STORY_REFINEMENT = "story_refinement"
    WORLDVIEW_GENERATION = "worldview_generation"
    CHARACTER_GENERATION = "character_generation"
    PLOT_GENERATION = "plot_generation"


class TaskService:
    """异步任务管理服务"""

    def __init__(self):
        self.running_tasks: dict[UUID, asyncio.Task] = {}

    async def create_task(
        self,
        session_id: UUID,
        target_stage: str,
        task_type: str,
        input_data: dict[str, Any],
        agent_type: str | None = None,
        estimated_duration_seconds: int | None = None,
    ) -> UUID:
        """创建新的异步任务"""

        task_id = uuid4()

        # 插入任务记录到数据库
        query = """
        INSERT INTO genesis_tasks (
            id, session_id, target_stage, task_type, status,
            progress, input_data, agent_type, estimated_duration_seconds,
            created_at, updated_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        """

        now = datetime.utcnow()
        await postgres_service.execute(
            query,
            (
                task_id,
                session_id,
                target_stage,
                task_type,
                TaskStatus.PENDING,
                0.0,
                json.dumps(input_data),
                agent_type,
                estimated_duration_seconds,
                now,
                now,
            ),
        )

        logger.info(f"Created task {task_id} for session {session_id}, type: {task_type}")
        return task_id

    async def start_task(self, task_id: UUID, message: str = "任务已开始"):
        """启动任务"""

        # 更新任务状态为运行中
        query = """
        UPDATE genesis_tasks
        SET status = $1, started_at = $2, updated_at = $3, message = $4
        WHERE id = $5
        """

        now = datetime.utcnow()
        await postgres_service.execute(query, (TaskStatus.RUNNING, now, now, message, task_id))

        # 获取任务信息用于SSE推送
        task_info = await self.get_task_info(task_id)
        if task_info:
            await sse_service.send_task_started(task_id, task_info["session_id"], message)

        logger.info(f"Started task {task_id}")

    async def update_progress(self, task_id: UUID, progress: float, stage: str, message: str):
        """更新任务进度"""

        # 更新数据库
        query = """
        UPDATE genesis_tasks
        SET progress = $1, current_stage = $2, message = $3, updated_at = $4
        WHERE id = $5
        """

        await postgres_service.execute(query, (progress, stage, message, datetime.utcnow(), task_id))

        # 获取任务信息用于SSE推送
        task_info = await self.get_task_info(task_id)
        if task_info:
            await sse_service.send_progress_update(task_id, task_info["session_id"], progress, stage, message)

        logger.debug(f"Updated task {task_id} progress: {progress:.2f} - {message}")

    async def complete_task(
        self,
        task_id: UUID,
        result_data: dict[str, Any],
        result_step_id: UUID | None = None,
        event_type: str = "task_complete",
    ):
        """完成任务"""

        # 计算实际执行时间
        task_info = await self.get_task_info(task_id)
        actual_duration = None
        if task_info and task_info.get("started_at"):
            started_at = task_info["started_at"]
            actual_duration = int((datetime.utcnow() - started_at).total_seconds())

        # 更新数据库
        query = """
        UPDATE genesis_tasks
        SET status = $1, progress = $2, result_data = $3, result_step_id = $4,
            completed_at = $5, updated_at = $6, actual_duration_seconds = $7
        WHERE id = $8
        """

        now = datetime.utcnow()
        await postgres_service.execute(
            query,
            (
                TaskStatus.COMPLETED,
                1.0,
                json.dumps(result_data),
                result_step_id,
                now,
                now,
                actual_duration,
                task_id,
            ),
        )

        # SSE推送完成事件
        if task_info:
            await sse_service.send_task_complete(task_id, task_info["session_id"], result_data, event_type)

        # 清理运行中的任务引用
        if task_id in self.running_tasks:
            del self.running_tasks[task_id]

        logger.info(f"Completed task {task_id}")

    async def fail_task(self, task_id: UUID, error_data: dict[str, Any]):
        """标记任务失败"""

        # 计算实际执行时间
        task_info = await self.get_task_info(task_id)
        actual_duration = None
        if task_info and task_info.get("started_at"):
            started_at = task_info["started_at"]
            actual_duration = int((datetime.utcnow() - started_at).total_seconds())

        # 更新数据库
        query = """
        UPDATE genesis_tasks
        SET status = $1, error_data = $2, completed_at = $3, updated_at = $4,
            actual_duration_seconds = $5
        WHERE id = $6
        """

        now = datetime.utcnow()
        await postgres_service.execute(
            query, (TaskStatus.FAILED, json.dumps(error_data), now, now, actual_duration, task_id)
        )

        # SSE推送错误事件
        if task_info:
            await sse_service.send_task_error(task_id, task_info["session_id"], error_data)

        # 清理运行中的任务引用
        if task_id in self.running_tasks:
            del self.running_tasks[task_id]

        logger.error(f"Failed task {task_id}: {error_data}")

    async def cancel_task(self, task_id: UUID):
        """取消任务"""

        # 取消运行中的异步任务
        if task_id in self.running_tasks:
            self.running_tasks[task_id].cancel()
            del self.running_tasks[task_id]

        # 更新数据库状态
        query = """
        UPDATE genesis_tasks
        SET status = $1, updated_at = $2
        WHERE id = $3 AND status IN ($4, $5)
        """

        await postgres_service.execute(
            query,
            (
                TaskStatus.CANCELLED,
                datetime.utcnow(),
                task_id,
                TaskStatus.PENDING,
                TaskStatus.RUNNING,
            ),
        )

        logger.info(f"Cancelled task {task_id}")

    async def get_task_info(self, task_id: UUID) -> dict[str, Any] | None:
        """获取任务信息"""

        query = """
        SELECT id, session_id, target_stage, task_type, status, progress,
               current_stage, message, input_data, result_data, error_data,
               agent_type, estimated_duration_seconds, actual_duration_seconds,
               created_at, updated_at, started_at, completed_at
        FROM genesis_tasks
        WHERE id = $1
        """

        result = await postgres_service.execute(query, (task_id,))
        if not result:
            return None

        return result[0]

    async def get_session_active_tasks(self, session_id: UUID) -> list[dict[str, Any]]:
        """获取会话的活跃任务"""

        query = """
        SELECT id, task_type, status, progress, current_stage, message,
               created_at, updated_at, started_at
        FROM genesis_tasks
        WHERE session_id = $1 AND status IN ($2, $3)
        ORDER BY created_at DESC
        """

        result = await postgres_service.execute(query, (session_id, TaskStatus.PENDING, TaskStatus.RUNNING))

        return result

    async def cleanup_old_tasks(self, days: int = 30):
        """清理旧的已完成任务"""

        query = f"""
        DELETE FROM genesis_tasks
        WHERE status IN ($1, $2, $3)
        AND completed_at < NOW() - INTERVAL '{days} days'
        """

        result = await postgres_service.execute(query, (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED))

        logger.info(f"Cleaned up old tasks, affected rows: {len(result)}")

    async def get_task_performance_stats(self, days: int = 7) -> dict[str, Any]:
        """获取任务性能统计"""

        query = f"""
        SELECT
            task_type,
            COUNT(*) as total_tasks,
            COUNT(CASE WHEN status = 'COMPLETED' THEN 1 END) as completed_tasks,
            COUNT(CASE WHEN status = 'FAILED' THEN 1 END) as failed_tasks,
            AVG(CASE WHEN actual_duration_seconds IS NOT NULL
                THEN actual_duration_seconds END) as avg_duration_seconds,
            MAX(actual_duration_seconds) as max_duration_seconds
        FROM genesis_tasks
        WHERE created_at >= NOW() - INTERVAL '{days} days'
        GROUP BY task_type
        ORDER BY total_tasks DESC
        """

        result = await postgres_service.execute(query)

        stats = {
            "period_days": days,
            "task_types": result,
            "summary": {
                "total_tasks": sum(row["total_tasks"] for row in result),
                "total_completed": sum(row["completed_tasks"] for row in result),
                "total_failed": sum(row["failed_tasks"] for row in result),
            },
        }

        if stats["summary"]["total_tasks"] > 0:
            stats["summary"]["success_rate"] = stats["summary"]["total_completed"] / stats["summary"]["total_tasks"]

        return stats


# 全局任务服务实例
task_service = TaskService()
