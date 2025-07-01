#!/usr/bin/env python3
"""Agents 主入口脚本

使用方法:
    # 启动所有 agents
    python -m src.agents.main

    # 启动指定的 agents
    python -m src.agents.main writer critic

    # 列出所有可用的 agents
    python -m src.agents.main --list
"""

import argparse
import logging
import sys

from .agent_config import AGENT_DEPENDENCIES, AGENT_PRIORITY
from .launcher import AVAILABLE_AGENTS, run

logger = logging.getLogger(__name__)


def print_agents_info():
    """打印所有 agents 的详细信息"""
    print("\n可用的 Agents:")
    print("-" * 60)

    # 按优先级排序
    sorted_agents = sorted(AVAILABLE_AGENTS, key=lambda x: AGENT_PRIORITY.get(x, 999))

    for agent in sorted_agents:
        priority = AGENT_PRIORITY.get(agent, "未定义")
        deps = AGENT_DEPENDENCIES.get(agent, [])
        deps_str = ", ".join(deps) if deps else "无"

        print(f"  {agent:<15} 优先级: {priority:<3} 依赖: {deps_str}")

    print("-" * 60)


def validate_agent_names(agent_names: list[str]) -> bool:
    """验证 agent 名称是否有效"""
    invalid = [name for name in agent_names if name not in AVAILABLE_AGENTS]
    if invalid:
        print(f"\n错误: 无效的 agent 名称: {invalid}")
        print(f"可用的 agents: {AVAILABLE_AGENTS}")
        return False
    return True


def check_dependencies(agent_names: list[str]) -> list[str]:
    """检查并添加必要的依赖 agents"""
    required_agents = set(agent_names)

    # 递归添加所有依赖
    def add_dependencies(agent: str):
        deps = AGENT_DEPENDENCIES.get(agent, [])
        for dep in deps:
            if dep not in required_agents:
                required_agents.add(dep)
                add_dependencies(dep)

    for agent in agent_names:
        add_dependencies(agent)

    # 返回按优先级排序的列表
    return sorted(list(required_agents), key=lambda x: AGENT_PRIORITY.get(x, 999))


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Infinite Scribe Agent 启动器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                    # 启动所有 agents
  %(prog)s writer critic      # 启动 writer 和 critic agents
  %(prog)s --list             # 列出所有可用的 agents
  %(prog)s --with-deps writer # 启动 writer 及其所有依赖
        """,
    )

    parser.add_argument("agents", nargs="*", help="要启动的 agent 名称列表(不指定则启动所有)")

    parser.add_argument("--list", "-l", action="store_true", help="列出所有可用的 agents 及其信息")

    parser.add_argument("--with-deps", "-d", action="store_true", help="自动包含所需的依赖 agents")

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="日志级别 (默认: INFO)",
    )

    args = parser.parse_args()

    # 设置日志级别
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # 处理 --list 选项
    if args.list:
        print_agents_info()
        sys.exit(0)

    # 确定要启动的 agents
    agent_names = args.agents if args.agents else None

    if agent_names:
        # 验证 agent 名称
        if not validate_agent_names(agent_names):
            sys.exit(1)

        # 如果需要,添加依赖
        if args.with_deps:
            original = agent_names.copy()
            agent_names = check_dependencies(agent_names)
            added = set(agent_names) - set(original)
            if added:
                logger.info(f"自动添加依赖 agents: {sorted(added)}")

    # 运行 agents
    try:
        logger.info("启动 Infinite Scribe Agents...")
        run(agent_names)
    except KeyboardInterrupt:
        logger.info("收到中断信号,正在停止...")
    except Exception as e:
        logger.error(f"运行出错: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
