"""统一的 Agent 启动器"""

import asyncio
import importlib
import logging
import signal
import sys
from collections.abc import Callable
from typing import Any

from ..agents.base import BaseAgent
from .agent_config import (
    AGENT_PRIORITY,
    AGENT_TOPICS,
    canonicalize_agent_id,
    list_available_agents,
    to_config_key,
    validate_agent_config,
)
from .registry import get_registered_agent


class AgentsLoadError(Exception):
    """Exception raised when agents fail to load properly"""

    pass


logger = logging.getLogger(__name__)

# 从配置中获取所有可用的 agents（返回 canonical snake_case ids）
AVAILABLE_AGENTS = list_available_agents()


class AgentLauncher:
    """Agent 启动器类"""

    def __init__(self):
        self.agents: dict[str, BaseAgent] = {}
        self.running = False
        self._signal_cleanup: Callable[[], None] | None = None

    def load_agent(self, agent_name: str) -> BaseAgent | None:
        """动态加载指定的 agent"""
        try:
            canonical_name = canonicalize_agent_id(agent_name)
            module_key = to_config_key(agent_name)
            # 优先使用显式注册表
            reg_cls = get_registered_agent(canonical_name)
            if reg_cls is not None and issubclass(reg_cls, BaseAgent):
                topics = AGENT_TOPICS.get(module_key, {})
                consume_topics = topics.get("consume", [])
                produce_topics = topics.get("produce", [])
                instance = reg_cls(name=canonical_name, consume_topics=consume_topics, produce_topics=produce_topics)
                logger.info(f"成功从注册表加载 agent: {canonical_name}")
                return instance
            # 尝试从 agent 模块导入
            try:
                module = importlib.import_module(f"..agents.{module_key}", package=__name__)

                # 生成候选类名，兼容 snake_case 和单词形式
                def snake_to_pascal(name: str) -> str:
                    return "".join(part.capitalize() for part in name.split("_"))

                candidates = [
                    f"{snake_to_pascal(canonical_name)}Agent",
                    f"{canonical_name.capitalize()}Agent",
                ]

                agent_class: type[Any] | None = None
                for cls_name in candidates:
                    agent_class = getattr(module, cls_name, None)
                    if agent_class is not None:
                        break

                # Fallback: scan module for first BaseAgent subclass if naming doesn't match
                if agent_class is None:
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name, None)
                        try:
                            if isinstance(attr, type) and issubclass(attr, BaseAgent) and attr is not BaseAgent:
                                agent_class = attr
                                break
                        except Exception:
                            continue

                if agent_class and issubclass(agent_class, BaseAgent):
                    # 获取主题配置
                    topics = AGENT_TOPICS.get(module_key, {})
                    consume_topics = topics.get("consume", [])
                    produce_topics = topics.get("produce", [])
                    # 创建 agent 实例
                    agent_instance = agent_class(
                        name=canonical_name, consume_topics=consume_topics, produce_topics=produce_topics
                    )
                    logger.info(f"成功加载 agent: {agent_name}")
                    return agent_instance
                elif agent_class is not None:
                    logger.error(f"模块 {agent_name} 中的类不是 BaseAgent 子类，忽略: {agent_class}")
            except (ImportError, AttributeError):
                pass

            # 如果没有找到具体实现,创建一个通用的 agent
            logger.info(f"使用通用 Agent 实现: {agent_name}")

            # 获取主题配置
            topics = AGENT_TOPICS.get(module_key, {})
            consume_topics = topics.get("consume", [])
            produce_topics = topics.get("produce", [])

            if not consume_topics:
                logger.warning(f"Agent {agent_name} 没有配置消费主题")

            # 创建一个匿名的 Agent 类
            class GenericAgent(BaseAgent):
                async def process_message(
                    self, message: dict[str, Any], context: dict[str, Any] | None = None
                ) -> dict[str, Any] | None:
                    logger.info(f"{agent_name} 处理消息: {message.get('type', 'unknown')}")
                    # 通用处理逻辑
                    return {
                        "status": "processed",
                        "agent": agent_name,
                        "message_type": message.get("type"),
                    }

            return GenericAgent(name=canonical_name, consume_topics=consume_topics, produce_topics=produce_topics)

        except Exception as e:
            logger.error(f"加载 agent {agent_name} 时出错: {e}")
            return None

    def load_agents(self, agent_names: list[str] | None = None) -> None:
        """加载指定的 agents,如果未指定则加载所有 agents"""
        # Validate agent configuration at startup
        validate_agent_config()

        if agent_names is None:
            agent_names = AVAILABLE_AGENTS

        # 验证 agent 名称
        canon = [canonicalize_agent_id(n) for n in agent_names]
        invalid_agents = [name for name in canon if name not in AVAILABLE_AGENTS]
        if invalid_agents:
            logger.error(f"无效的 agent 名称: {invalid_agents}")
            logger.info(f"可用的 agents: {AVAILABLE_AGENTS}")
            raise AgentsLoadError(f"Invalid agent names: {invalid_agents}. Available agents: {AVAILABLE_AGENTS}")

        # 按优先级排序 agents
        sorted_agents = sorted(canon, key=lambda x: AGENT_PRIORITY.get(to_config_key(x), 999))

        # 加载每个 agent
        for agent_name in sorted_agents:
            agent = self.load_agent(agent_name)
            if agent:
                # 存储使用 canonical 名称
                self.agents[canonicalize_agent_id(agent_name)] = agent

        if not self.agents:
            logger.error("没有成功加载任何 agent")
            raise AgentsLoadError("No agents were successfully loaded")

        logger.info(f"成功加载 {len(self.agents)} 个 agents: {list(self.agents.keys())}")

    async def start_all(self) -> None:
        """启动所有已加载的 agents"""
        self.running = True
        tasks: list[asyncio.Task[Any]] = []

        for name, agent in self.agents.items():
            logger.info(f"启动 agent: {name}")
            task = asyncio.create_task(agent.start())
            tasks.append(task)

        # 等待所有 agents 启动完成
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"启动 agents 时出错: {e}")
            # 取消任务并确保收敛
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            await self.stop_all()

    async def stop_all(self) -> None:
        """停止所有运行中的 agents"""
        self.running = False
        tasks: list[asyncio.Task[Any]] = []

        for name, agent in self.agents.items():
            if agent.is_running or agent.consumer or agent.producer:
                logger.info(f"停止 agent: {name}")
                task = asyncio.create_task(agent.stop())
                tasks.append(task)

        # 等待所有 agents 停止
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("所有 agents 已停止")

    def setup_signal_handlers(self, enable: bool = True) -> None:
        """
        设置信号处理器

        :param enable: 是否启用信号处理器。当被外部orchestrator管理时应设为False
        """
        if not enable:
            logger.info("Signal handlers disabled - managed by external orchestrator")
            return

        # 复用统一信号处理工具，避免与外层 orchestrator 冲突
        try:
            from src.launcher.signal_utils import register_shutdown_handler

            async def on_shutdown() -> None:
                logger.info("收到终止信号，准备停止所有 agents ...")
                await self.stop_all()

            cleanup = register_shutdown_handler(on_shutdown)
            self._signal_cleanup = cleanup
            logger.info("Agent signal handlers registered via signal_utils")
        except Exception as e:
            # 回退到基本信号处理（不建议，但确保最小可用性）
            logger.warning(f"信号工具注册失败，回退到基础 signal 处理: {e}")

            def signal_handler(sig, frame):
                logger.info(f"收到信号 {sig},正在停止 agents...")
                task = asyncio.create_task(self.stop_all())
                _ = task

            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            logger.info("Agent signal handlers registered: SIGINT,SIGTERM (fallback)")

    def cleanup_signal_handlers(self) -> None:
        """清理注册的信号处理器（用于测试或自管理时）"""
        try:
            if self._signal_cleanup is not None:
                self._signal_cleanup()
                self._signal_cleanup = None
                logger.info("Agent signal handlers cleaned up")
        except Exception as e:
            logger.warning(f"Failed to cleanup signal handlers: {e}")


async def main(agent_names: list[str] | None = None):
    """主函数"""
    launcher = AgentLauncher()

    # 设置信号处理
    launcher.setup_signal_handlers()

    # 加载 agents
    launcher.load_agents(agent_names)

    # 启动所有 agents
    try:
        await launcher.start_all()
    except KeyboardInterrupt:
        logger.info("收到键盘中断信号")
    finally:
        await launcher.stop_all()


def run(agent_names: list[str] | None = None):
    """运行 agent 启动器"""
    asyncio.run(main(agent_names))


if __name__ == "__main__":
    # 从命令行参数获取要启动的 agents
    import argparse

    parser = argparse.ArgumentParser(description="Agent 启动器")
    parser.add_argument("agents", nargs="*", help="要启动的 agent 名称列表(不指定则启动所有)")
    parser.add_argument("--list", action="store_true", help="列出所有可用的 agents")

    args = parser.parse_args()

    if args.list:
        print("可用的 agents:")
        for agent in AVAILABLE_AGENTS:
            print(f"  - {agent}")
        sys.exit(0)

    # 运行启动器
    agent_names = args.agents if args.agents else None
    run(agent_names)
