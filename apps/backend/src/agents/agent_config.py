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


# Agent 主题配置 - 中央管理所有 Agent 的 Kafka 消息路由
AGENT_TOPICS: dict[str, AgentTopicConfig] = {
    # 领域总线（Facts）：genesis.session.events（仅中央协调者消费/产出）
    # 能力总线（Capabilities）：各 Agent 的 tasks/events
    # Director 是中央协调者，负责分发任务和收集结果
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
            "genesis.inquiry.events",
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
            "genesis.inquiry.tasks",
        ],
    },
    # Orchestrator 是域级协调器，处理跨领域的协调任务
    # 采用明确列举主题的方式，避免正则表达式订阅的复杂性
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
            "genesis.inquiry.events",
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
            "genesis.inquiry.tasks",
        ],
    },
    # 以下是能力型 Agent，每个 Agent 专注于特定的小说创作能力
    "outliner": {"consume": ["genesis.outline.tasks"], "produce": ["genesis.outline.events"]},  # 大纲制作
    "writer": {"consume": ["genesis.writer.tasks"], "produce": ["genesis.writer.events"]},  # 内容写作
    "critic": {"consume": ["genesis.review.tasks"], "produce": ["genesis.review.events"]},  # 内容审查
    "characterexpert": {"consume": ["genesis.character.tasks"], "produce": ["genesis.character.events"]},  # 角色塑造
    "worldbuilder": {"consume": ["genesis.world.tasks"], "produce": ["genesis.world.events"]},  # 世界构建
    "plotmaster": {"consume": ["genesis.plot.tasks"], "produce": ["genesis.plot.events"]},  # 情节设计
    "factchecker": {"consume": ["genesis.factcheck.tasks"], "produce": ["genesis.factcheck.events"]},  # 事实校验
    "rewriter": {"consume": ["genesis.rewriter.tasks"], "produce": ["genesis.rewriter.events"]},  # 内容重写
    "worldsmith": {"consume": ["genesis.worldsmith.tasks"], "produce": ["genesis.worldsmith.events"]},  # 世界设定
    # 分析和知识更新管道 - 基于 LLM 的内容分析和知识抽取
    "content_analyzer": {
        "consume": ["genesis.writer.events"],  # 分析写作输出内容
        "produce": ["genesis.analyzer.events"],
    },
    "knowledge_updater": {
        "consume": ["genesis.analyzer.events"],  # 基于分析结果更新知识库
        "produce": ["genesis.knowledge.events"],
    },
    # 查询处理 Agent - 处理用户的问题和查询请求
    "inquiry": {
        "consume": ["genesis.inquiry.tasks"],
        "produce": ["genesis.inquiry.events"],
    },
}

# Agent 依赖关系 - 定义 Agent 启动和运行的先后顺序
AGENT_DEPENDENCIES = {
    "director": [],  # Director 是核心协调者，不依赖其他 agent
    "outliner": ["director"],  # 大纲制作需要 Director 分配任务
    "writer": ["outliner", "characterexpert", "worldbuilder"],  # 写作需要大纲、角色和世界设定
    "critic": ["writer"],  # 审查需要先有写作内容
    "characterexpert": ["director"],  # 角色专家接受 Director 指令
    "worldbuilder": ["director"],  # 世界构建者接受 Director 指令
    "plotmaster": ["director"],  # 情节大师接受 Director 指令
    "factchecker": ["writer", "worldbuilder", "characterexpert"],  # 事实校验需要内容、世界和角色信息
    "rewriter": ["critic", "factchecker"],  # 重写需要审查和事实校验结果
    "worldsmith": ["worldbuilder"],  # 世界设定师基于世界构建者的输出
    # 分析器链路依赖关系
    "content_analyzer": ["writer"],  # 内容分析需要写作输出
    "knowledge_updater": ["content_analyzer"],  # 知识更新需要分析结果
    # 查询处理独立运行
    "inquiry": [],  # 查询处理不依赖其他服务
}

# Agent 启动优先级 - 数字越小优先级越高，确保依赖服务先启动
AGENT_PRIORITY = {
    "director": 1,  # 最高优先级，核心协调者
    "characterexpert": 2,  # 基础能力组，并行启动
    "worldbuilder": 2,
    "plotmaster": 2,
    "outliner": 3,  # 需要基础能力组支持
    "writer": 4,  # 需要大纲和基础设定
    "critic": 5,  # 内容后处理组
    "factchecker": 5,
    "rewriter": 6,  # 需要审查和校验结果
    "worldsmith": 7,  # 世界设定深化
    # 分析链路在内容产生后运行
    "content_analyzer": 8,  # 分析写作输出
    "knowledge_updater": 9,  # 更新知识库
    # 查询服务独立运行，优先级最低
    "inquiry": 10,  # 可随时启动的查询服务
}


def get_agent_topics(agent: str) -> tuple[list[str], list[str]]:
    """获取指定 Agent 的消费和生产主题列表

    Args:
        agent: Agent 名称（支持别名和规范名称）

    Returns:
        (consume_topics, produce_topics) 元组，未配置时返回空列表
    """
    cfg = AGENT_TOPICS.get(to_config_key(agent), {})
    return list(cfg.get("consume", []) or []), list(cfg.get("produce", []) or [])


# Agent 别名映射 - 桥接标准蛇形命名和现有配置键/目录名
AGENT_ALIASES: dict[str, str] = {
    # 标准名称 -> 配置键
    "character_expert": "characterexpert",
    "fact_checker": "factchecker",
    "world_builder": "worldbuilder",
}

# 反向映射 - 配置键到标准名称
CANONICAL_IDS: dict[str, str] = {
    # 配置键 -> 标准名称
    "characterexpert": "character_expert",
    "factchecker": "fact_checker",
}


def canonicalize_agent_id(name: str) -> str:
    """将 Agent 名称标准化为蛇形命名格式"""
    s = name.strip().lower().replace("-", "_")
    # 将配置键映射为标准名称（如果需要）
    return CANONICAL_IDS.get(s, s)


def to_config_key(name: str) -> str:
    """将输入 ID（可能是标准名称）映射为配置/模块键"""
    s = canonicalize_agent_id(name)
    return AGENT_ALIASES.get(s, s)


def canonical_id_from_config_key(key: str) -> str:
    """从配置键获取标准 ID"""
    return CANONICAL_IDS.get(key, key)


def list_available_agents() -> list[str]:
    """列出所有可用的标准 Agent ID"""
    return sorted(canonical_id_from_config_key(k) for k in AGENT_TOPICS)


def validate_agent_config() -> None:
    """在启动时验证 Agent 配置

    检查配置完整性，对未配置主题的 Agent 记录警告日志
    """
    import logging

    logger = logging.getLogger(__name__)

    for agent_id, config in AGENT_TOPICS.items():
        consume = config.get("consume", [])
        produce = config.get("produce", [])

        if not consume and not produce:
            logger.warning(f"Agent '{agent_id}' 未配置任何主题")
        elif not consume:
            logger.info(f"Agent '{agent_id}' 无消费主题（仅生产者模式）")
        elif not produce:
            logger.info(f"Agent '{agent_id}' 无生产主题（仅消费者模式）")
