"""Agent 配置定义

定义所有 agent 的 Kafka 主题映射和配置
"""

# Agent 主题配置
AGENT_TOPICS: dict[str, dict[str, list[str]]] = {
    "director": {
        "consume": [
            "project.start.request",  # 项目启动请求
            "project.status.request",  # 项目状态查询
            "agent.coordination.request",  # Agent 协调请求
        ],
        "produce": [
            "agent.task.assignment",  # 任务分配
            "project.status.update",  # 项目状态更新
            "story.outline.request",  # 大纲请求(发给 outliner)
        ],
    },
    "outliner": {
        "consume": [
            "story.outline.request",  # 大纲创建请求
            "outline.revision.request",  # 大纲修订请求
        ],
        "produce": [
            "story.outline.response",  # 大纲响应
            "story.write.request",  # 写作请求(发给 writer)
        ],
    },
    "writer": {
        "consume": [
            "story.write.request",  # 写作请求
            "story.rewrite.request",  # 重写请求
        ],
        "produce": [
            "story.write.response",  # 写作响应
            "story.review.request",  # 评审请求(发给 critic)
        ],
    },
    "critic": {
        "consume": [
            "story.review.request",  # 评审请求
            "review.update.request",  # 评审更新请求
        ],
        "produce": [
            "story.review.response",  # 评审响应
            "story.rewrite.request",  # 重写请求(发给 writer)
            "story.approved",  # 批准的内容
        ],
    },
    "characterexpert": {
        "consume": [
            "character.create.request",  # 角色创建请求
            "character.analysis.request",  # 角色分析请求
            "character.consistency.check",  # 角色一致性检查
        ],
        "produce": [
            "character.profile.response",  # 角色档案响应
            "character.suggestion",  # 角色建议
            "story.write.guidance",  # 写作指导(发给 writer)
        ],
    },
    "worldbuilder": {
        "consume": [
            "world.create.request",  # 世界构建请求
            "world.expand.request",  # 世界扩展请求
            "world.consistency.check",  # 世界一致性检查
        ],
        "produce": [
            "world.setting.response",  # 世界设定响应
            "world.detail.update",  # 世界细节更新
            "story.write.context",  # 写作上下文(发给 writer)
        ],
    },
    "plotmaster": {
        "consume": [
            "plot.design.request",  # 情节设计请求
            "plot.twist.request",  # 情节转折请求
            "plot.consistency.check",  # 情节一致性检查
        ],
        "produce": [
            "plot.structure.response",  # 情节结构响应
            "plot.event.suggestion",  # 情节事件建议
            "story.outline.guidance",  # 大纲指导(发给 outliner)
        ],
    },
    "factchecker": {
        "consume": [
            "fact.verify.request",  # 事实验证请求
            "consistency.check.request",  # 一致性检查请求
        ],
        "produce": [
            "fact.verification.response",  # 验证响应
            "inconsistency.alert",  # 不一致警告
            "story.correction.request",  # 修正请求
        ],
    },
    "rewriter": {
        "consume": [
            "content.rewrite.request",  # 内容重写请求
            "style.adjustment.request",  # 风格调整请求
            "content.polish.request",  # 内容润色请求
        ],
        "produce": [
            "content.rewrite.response",  # 重写响应
            "content.final.version",  # 最终版本
        ],
    },
    "worldsmith": {
        "consume": [
            "worldsmith.task.request",  # Worldsmith 任务请求
            "world.integration.request",  # 世界整合请求
        ],
        "produce": [
            "worldsmith.task.response",  # 任务响应
            "world.update.notification",  # 世界更新通知
        ],
    },
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
