"""Agent 实现模板

使用说明:
1. 复制此文件到对应的 agent 目录
2. 将 TemplateAgent 重命名为 XxxAgent(如 DirectorAgent)
3. 实现具体的业务逻辑
4. 在 __init__.py 中导出 Agent 类
"""

import asyncio
import logging
from typing import Any

from ..base import BaseAgent

logger = logging.getLogger(__name__)


class TemplateAgent(BaseAgent):
    """Agent 模板类 - 请修改为具体的 Agent 描述"""

    def __init__(self, name: str):
        super().__init__(name)
        self.is_running = False

        # TODO: 初始化 agent 特定的配置和资源
        # 例如:模型配置、数据库连接、缓存等

    async def process_message(self, message: dict[str, Any]) -> dict[str, Any]:
        """处理消息

        Args:
            message: 输入消息,通常包含:
                - type: 消息类型
                - content: 消息内容
                - metadata: 元数据

        Returns:
            处理结果字典
        """
        logger.info(f"{self.name} 正在处理消息: {message.get('type', 'unknown')}")

        # TODO: 实现具体的消息处理逻辑
        message_type = message.get("type")

        if message_type == "example_type":
            return await self._handle_example_type(message)
        else:
            logger.warning(f"未知的消息类型: {message_type}")
            return {
                "status": "error",
                "agent": self.name,
                "message": f"未知的消息类型: {message_type}",
            }

    async def _handle_example_type(self, message: dict[str, Any]) -> dict[str, Any]:
        """处理特定类型的消息"""
        # TODO: 实现具体的处理逻辑
        return {"status": "success", "agent": self.name, "result": "处理完成"}

    async def start(self):
        """启动 Agent"""
        logger.info(f"启动 {self.name} agent")
        self.is_running = True

        try:
            # TODO: 初始化连接
            # await self._connect_to_message_queue()
            # await self._subscribe_to_topics()

            # 主循环
            while self.is_running:
                # TODO: 实现消息获取和处理
                # message = await self._get_next_message()
                # if message:
                #     result = await self.process_message(message)
                #     await self._send_result(result)

                # 临时:模拟工作
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"{self.name} agent 运行出错: {e}", exc_info=True)
        finally:
            await self._cleanup()
            logger.info(f"{self.name} agent 已停止")

    async def stop(self):
        """停止 Agent"""
        logger.info(f"正在停止 {self.name} agent")
        self.is_running = False

    async def _cleanup(self):
        """清理资源"""
        # TODO: 实现资源清理
        # - 断开连接
        # - 保存状态
        # - 释放资源
        pass
