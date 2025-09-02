"""统一的 Agent 启动器"""

import asyncio
import importlib
import logging
import signal
import sys
from typing import Any

from ..agents.base import BaseAgent
from .agent_config import AGENT_PRIORITY, AGENT_TOPICS


class AgentsLoadError(Exception):
    """Exception raised when agents fail to load properly"""

    pass


# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 从配置中获取所有可用的 agents
AVAILABLE_AGENTS = list(AGENT_TOPICS.keys())


class AgentLauncher:
    """Agent 启动器类"""

    def __init__(self):
        self.agents: dict[str, BaseAgent] = {}
        self.running = False

    def load_agent(self, agent_name: str) -> BaseAgent | None:
        """动态加载指定的 agent"""
        try:
            # 尝试从 agent 模块导入
            try:
                module = importlib.import_module(f"..agents.{agent_name}", package=__name__)

                # 查找 Agent 类(约定类名为 AgentNameAgent)
                agent_class_name = f"{agent_name.capitalize()}Agent"
                # Dynamic import: allow unknown constructor signature for concrete agents
                agent_class: type[Any] | None = getattr(module, agent_class_name, None)

                if agent_class:
                    # 创建 agent 实例
                    agent_instance = agent_class()
                    logger.info(f"成功加载 agent: {agent_name}")
                    return agent_instance
            except (ImportError, AttributeError):
                pass

            # 如果没有找到具体实现,创建一个通用的 agent
            logger.info(f"使用通用 Agent 实现: {agent_name}")

            # 获取主题配置
            topics = AGENT_TOPICS.get(agent_name, {})
            consume_topics = topics.get("consume", [])
            produce_topics = topics.get("produce", [])

            if not consume_topics:
                logger.warning(f"Agent {agent_name} 没有配置消费主题")

            # 创建一个匿名的 Agent 类
            class GenericAgent(BaseAgent):
                async def process_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
                    logger.info(f"{agent_name} 处理消息: {message.get('type', 'unknown')}")
                    # 通用处理逻辑
                    return {
                        "status": "processed",
                        "agent": agent_name,
                        "message_type": message.get("type"),
                    }

            return GenericAgent(name=agent_name, consume_topics=consume_topics, produce_topics=produce_topics)

        except Exception as e:
            logger.error(f"加载 agent {agent_name} 时出错: {e}")
            return None

    def load_agents(self, agent_names: list[str] | None = None) -> None:
        """加载指定的 agents,如果未指定则加载所有 agents"""
        if agent_names is None:
            agent_names = AVAILABLE_AGENTS

        # 验证 agent 名称
        invalid_agents = [name for name in agent_names if name not in AVAILABLE_AGENTS]
        if invalid_agents:
            logger.error(f"无效的 agent 名称: {invalid_agents}")
            logger.info(f"可用的 agents: {AVAILABLE_AGENTS}")
            raise AgentsLoadError(f"Invalid agent names: {invalid_agents}. Available agents: {AVAILABLE_AGENTS}")

        # 按优先级排序 agents
        sorted_agents = sorted(agent_names, key=lambda x: AGENT_PRIORITY.get(x, 999))

        # 加载每个 agent
        for agent_name in sorted_agents:
            agent = self.load_agent(agent_name)
            if agent:
                self.agents[agent_name] = agent

        if not self.agents:
            logger.error("没有成功加载任何 agent")
            raise AgentsLoadError("No agents were successfully loaded")

        logger.info(f"成功加载 {len(self.agents)} 个 agents: {list(self.agents.keys())}")

    async def start_all(self) -> None:
        """启动所有已加载的 agents"""
        self.running = True
        tasks = []

        for name, agent in self.agents.items():
            logger.info(f"启动 agent: {name}")
            task = asyncio.create_task(agent.start())
            tasks.append(task)

        # 等待所有 agents 启动完成
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"启动 agents 时出错: {e}")
            await self.stop_all()

    async def stop_all(self) -> None:
        """停止所有运行中的 agents"""
        self.running = False
        tasks = []

        for name, agent in self.agents.items():
            logger.info(f"停止 agent: {name}")
            task = asyncio.create_task(agent.stop())
            tasks.append(task)

        # 等待所有 agents 停止
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("所有 agents 已停止")

    def setup_signal_handlers(self) -> None:
        """设置信号处理器"""

        def signal_handler(sig, frame):
            logger.info(f"收到信号 {sig},正在停止 agents...")
            task = asyncio.create_task(self.stop_all())
            # 任务会在事件循环中运行，不需要等待
            _ = task

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


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
