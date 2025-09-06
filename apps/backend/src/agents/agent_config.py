"""Agent 配置定义

定义所有 agent 的 Kafka 主题映射和配置（单一真相源）。

注意：具体 Agent 类不应在代码中重复声明 consume/produce 主题，统一在此处集中维护，
或未来迁移至 Settings/TOML。提供轻量的类型化访问辅助函数。
"""

from __future__ import annotations

from typing import TypedDict


class AgentTopicConfig(TypedDict, total=False):
    consume: list[str]
    produce: list[str]


# Agent 主题配置
AGENT_TOPICS: dict[str, AgentTopicConfig] = {
    # 领域总线（Facts）：genesis.session.events（仅中央协调者消费/产出）
    # 能力总线（Capabilities）：各 Agent 的 tasks/events
    # Orchestrator-like director（示例）：消费领域与各能力结果；产出能力任务
    "director": {
        "consume": [
            "genesis.session.events",
            "genesis.outline.events",
            "genesis.writer.events",
            "genesis.review.events",
            "genesis.world.events",
            "genesis.character.events",
            "genesis.plot.events",
            "genesis.factcheck.events",
            "genesis.rewriter.events",
            "genesis.worldsmith.events",
        ],
        "produce": [
            "genesis.outline.tasks",
            "genesis.writer.tasks",
            "genesis.review.tasks",
            "genesis.world.tasks",
            "genesis.character.tasks",
            "genesis.plot.tasks",
            "genesis.factcheck.tasks",
            "genesis.rewriter.tasks",
            "genesis.worldsmith.tasks",
        ],
    },
    # Domain Orchestrator: 消费领域事实 + 能力结果；产出能力任务（任务总线）
    # 明确列出多个域前缀主题（方案B，不使用正则订阅）
    "orchestrator": {
        "consume": [
            # Domain bus
            "genesis.session.events",
            # Capability events
            "genesis.outline.events",
            "genesis.writer.events",
            "genesis.review.events",
            "genesis.world.events",
            "genesis.character.events",
            "genesis.plot.events",
            "genesis.factcheck.events",
            "genesis.rewriter.events",
            "genesis.worldsmith.events",
        ],
        "produce": [
            # Capability tasks (agent bus)
            "genesis.outline.tasks",
            "genesis.writer.tasks",
            "genesis.review.tasks",
            "genesis.world.tasks",
            "genesis.character.tasks",
            "genesis.plot.tasks",
            "genesis.factcheck.tasks",
            "genesis.rewriter.tasks",
            "genesis.worldsmith.tasks",
        ],
    },
    # Capability agents
    "outliner": {"consume": ["genesis.outline.tasks"], "produce": ["genesis.outline.events"]},
    "writer": {"consume": ["genesis.writer.tasks"], "produce": ["genesis.writer.events"]},
    "critic": {"consume": ["genesis.review.tasks"], "produce": ["genesis.review.events"]},
    "characterexpert": {"consume": ["genesis.character.tasks"], "produce": ["genesis.character.events"]},
    "worldbuilder": {"consume": ["genesis.world.tasks"], "produce": ["genesis.world.events"]},
    "plotmaster": {"consume": ["genesis.plot.tasks"], "produce": ["genesis.plot.events"]},
    "factchecker": {"consume": ["genesis.factcheck.tasks"], "produce": ["genesis.factcheck.events"]},
    "rewriter": {"consume": ["genesis.rewriter.tasks"], "produce": ["genesis.rewriter.events"]},
    "worldsmith": {"consume": ["genesis.worldsmith.tasks"], "produce": ["genesis.worldsmith.events"]},
}

# Agent 依赖关系
AGENT_DEPENDENCIES = {
    "director": [],  # Director 不依赖其他 agent
    "outliner": ["director"],  # Outliner 依赖 Director
    "writer": ["outliner", "characterexpert", "worldbuilder"],
    "critic": ["writer"],
    "characterexpert": ["director"],
    "worldbuilder": ["director"],
    "plotmaster": ["director"],
    "factchecker": ["writer", "worldbuilder", "characterexpert"],
    "rewriter": ["critic", "factchecker"],
    "worldsmith": ["worldbuilder"],
}

# Agent 启动优先级(数字越小优先级越高)
AGENT_PRIORITY = {
    "director": 1,
    "characterexpert": 2,
    "worldbuilder": 2,
    "plotmaster": 2,
    "outliner": 3,
    "writer": 4,
    "critic": 5,
    "factchecker": 5,
    "rewriter": 6,
    "worldsmith": 7,
}


def get_agent_topics(agent: str) -> tuple[list[str], list[str]]:
    """Get (consume, produce) topics for a given agent name.

    Returns empty lists when not configured.
    """
    cfg = AGENT_TOPICS.get(to_config_key(agent), {})
    return list(cfg.get("consume", []) or []), list(cfg.get("produce", []) or [])


# Aliases to bridge canonical snake_case ids and existing config keys / directories
AGENT_ALIASES: dict[str, str] = {
    # canonical -> config key
    "character_expert": "characterexpert",
    "fact_checker": "factchecker",
    "world_builder": "worldbuilder",
}

CANONICAL_IDS: dict[str, str] = {
    # config key -> canonical
    "characterexpert": "character_expert",
    "factchecker": "fact_checker",
}


def canonicalize_agent_id(name: str) -> str:
    s = name.strip().lower().replace("-", "_")
    # Map config key to canonical if needed
    return CANONICAL_IDS.get(s, s)


def to_config_key(name: str) -> str:
    """Map incoming id (possibly canonical) to config/module key"""
    s = canonicalize_agent_id(name)
    return AGENT_ALIASES.get(s, s)


def canonical_id_from_config_key(key: str) -> str:
    return CANONICAL_IDS.get(key, key)


def list_available_agents() -> list[str]:
    """List canonical agent ids available by configuration"""
    return sorted(canonical_id_from_config_key(k) for k in AGENT_TOPICS)


def validate_agent_config() -> None:
    """Validate agent configuration at startup.

    Logs warnings for agents with no topics configured.
    """
    import logging

    logger = logging.getLogger(__name__)

    for agent_id, config in AGENT_TOPICS.items():
        consume = config.get("consume", [])
        produce = config.get("produce", [])

        if not consume and not produce:
            logger.warning(f"Agent '{agent_id}' has no topics configured")
        elif not consume:
            logger.info(f"Agent '{agent_id}' has no consume topics (producer-only)")
        elif not produce:
            logger.info(f"Agent '{agent_id}' has no produce topics (consumer-only)")
