# 完整数据示例

本文档提供创世阶段各个数据结构的完整示例，展示数据在 Command_Box、Domain_Events 和 Event_Outbox 三个表中的存储格式。

## 初始灵感阶段 (Stage 0)

### 1. 开始创世会话

#### Command_Box 记录

```json
{
    "id": "cmd-box-001",
    "command_id": "cmd-123",
    "command_type": "Command.Genesis.Session.Start",
    "aggregate_id": "session-456",
    "aggregate_type": "GenesisSession",
    "payload": {
        "user_id": "user-789",
        "initial_input": "我想写一个关于时间旅行的科幻小说",
        "preferences": {
            "genre": "sci-fi",
            "length": "medium",
            "style": "modern"
        }
    },
    "correlation_id": "flow-001",
    "causation_id": null,
    "user_id": "user-789",
    "status": "COMPLETED",
    "created_at": "2024-01-15T10:25:00Z",
    "processed_at": "2024-01-15T10:25:01Z",
    "error_message": null,
    "retry_count": 0,
    "metadata": {
        "client_ip": "192.168.1.100",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "request_id": "req-789",
        "session_info": {
            "tab_id": "tab-456",
            "browser_session": "bs-123"
        }
    }
}
```

#### Domain_Events 记录

```json
{
    "id": "domain-event-001",
    "event_id": "event-001",
    "event_type": "Genesis.Session.Started",
    "aggregate_id": "session-456",
    "aggregate_type": "GenesisSession",
    "aggregate_version": 1,
    "payload": {
        "session_id": "session-456",
        "novel_id": "novel-789",
        "stage": "Stage_0",
        "user_id": "user-789",
        "content": {
            "initial_input": "我想写一个关于时间旅行的科幻小说",
            "preferences": {
                "genre": "sci-fi",
                "length": "medium",
                "style": "modern"
            }
        },
        "timestamp": "2024-01-15T10:25:00Z"
    },
    "correlation_id": "flow-001",
    "causation_id": "cmd-123",
    "user_id": "user-789",
    "occurred_at": "2024-01-15T10:25:01Z",
    "metadata": {
        "version": 1,
        "source": "genesis-orchestrator",
        "trace_id": "trace-001",
        "processing_node": "genesis-worker-01",
        "processing_time_ms": 150
    }
}
```

#### Event_Outbox 记录

```json
{
    "id": "outbox-001",
    "event_id": "event-001",
    "topic": "genesis.session.events",
    "partition_key": "session-456",
    "headers": {
        "event_type": "Genesis.Session.Started",
        "content_type": "application/json",
        "correlation_id": "flow-001",
        "causation_id": "cmd-123",
        "aggregate_id": "session-456",
        "aggregate_type": "GenesisSession",
        "user_id": "user-789",
        "source": "genesis-orchestrator",
        "trace_id": "trace-001",
        "timestamp": "2024-01-15T10:25:01Z",
        "schema_version": "1.0"
    },
    "payload": {
        "event_id": "event-001",
        "event_type": "Genesis.Session.Started",
        "aggregate_id": "session-456",
        "aggregate_type": "GenesisSession",
        "aggregate_version": 1,
        "payload": {
            "session_id": "session-456",
            "novel_id": "novel-789",
            "stage": "Stage_0",
            "user_id": "user-789",
            "content": {
                "initial_input": "我想写一个关于时间旅行的科幻小说",
                "preferences": {
                    "genre": "sci-fi",
                    "length": "medium",
                    "style": "modern"
                }
            },
            "timestamp": "2024-01-15T10:25:00Z"
        },
        "correlation_id": "flow-001",
        "causation_id": "cmd-123",
        "user_id": "user-789",
        "occurred_at": "2024-01-15T10:25:01Z",
        "metadata": {
            "version": 1,
            "source": "genesis-orchestrator",
            "trace_id": "trace-001",
            "processing_node": "genesis-worker-01",
            "processing_time_ms": 150
        }
    },
    "status": "PUBLISHED",
    "created_at": "2024-01-15T10:25:01Z",
    "published_at": "2024-01-15T10:25:02Z",
    "retry_count": 0,
    "error_message": null
}
```

### 2. 请求生成创意种子

#### Command_Box 记录

```json
{
    "id": "cmd-box-002",
    "command_id": "cmd-456",
    "command_type": "Command.Genesis.Session.Seed.Request",
    "aggregate_id": "session-456",
    "aggregate_type": "GenesisSession",
    "payload": {
        "session_id": "session-456",
        "user_id": "user-789",
        "user_input": "我想写一个关于时间旅行的科幻小说",
        "preferences": {
            "genre": "sci-fi",
            "length": "medium",
            "style": "modern"
        },
        "context": {
            "previous_attempts": 0,
            "iteration_number": 1,
            "user_expectations": "创新的时间旅行概念，避免陈词滥调"
        }
    },
    "correlation_id": "flow-001",
    "causation_id": "event-001",
    "user_id": "user-789",
    "status": "COMPLETED",
    "created_at": "2024-01-15T10:26:00Z",
    "processed_at": "2024-01-15T10:30:00Z",
    "error_message": null,
    "retry_count": 0,
    "metadata": {
        "expected_processing_time_ms": 5000,
        "actual_processing_time_ms": 4200,
        "assigned_agent": "outliner-agent",
        "priority": "normal"
    }
}
```

### 3. AI提出高概念方案

#### Domain_Events 记录

```json
{
    "id": "domain-event-002",
    "event_id": "event-456",
    "event_type": "Genesis.Session.ConceptProposed",
    "aggregate_id": "session-456",
    "aggregate_type": "GenesisSession",
    "aggregate_version": 3,
    "payload": {
        "session_id": "session-456",
        "novel_id": "novel-789",
        "stage": "Stage_0",
        "user_id": "user-789",
        "content": {
            "concept_id": "concept-123",
            "title": "时间的囚徒",
            "premise": "一位物理学家在研究量子力学时意外发现了时间旅行的秘密，但每次穿越都会创造新的时间线，他必须在无数个平行宇宙中寻找回到原始时间线的方法。",
            "genre": "科幻悬疑",
            "target_audience": "成人读者",
            "themes": [
                "时间与命运的悖论",
                "科学发现的道德责任",
                "选择与后果的蝴蝶效应"
            ],
            "tone": "紧张悬疑，哲学思辨",
            "estimated_length": "中篇小说(8-12万字)",
            "unique_elements": [
                "多时间线叙事结构",
                "量子物理学理论基础",
                "道德选择的蝴蝶效应",
                "平行宇宙的视觉化呈现"
            ],
            "hook": "如果每一个选择都会分裂出新的现实，那么哪一个现实才是真实的？",
            "potential_conflicts": [
                "时间悖论的逻辑自洽性",
                "角色在多重现实中的身份认知",
                "拯救原始时间线的道德代价"
            ]
        },
        "quality_score": 8.5,
        "generation_metadata": {
            "model_version": "gpt-4-turbo",
            "generation_time_ms": 2340,
            "confidence_score": 0.87,
            "iteration_count": 2,
            "prompt_tokens": 1250,
            "completion_tokens": 890,
            "temperature": 0.8
        },
        "timestamp": "2024-01-15T10:30:00Z"
    },
    "correlation_id": "flow-001",
    "causation_id": "cmd-456",
    "user_id": "user-789",
    "occurred_at": "2024-01-15T10:30:00Z",
    "metadata": {
        "version": 1,
        "source": "outliner-agent",
        "trace_id": "trace-001",
        "agent_context": {
            "model_parameters": {
                "temperature": 0.8,
                "max_tokens": 2048,
                "top_p": 0.9
            },
            "prompt_version": "v2.1",
            "creativity_boost": true
        }
    }
}
```

## 立意主题阶段 (Stage 1)

### 1. 请求生成主题

#### Command_Box 记录

```json
{
    "id": "cmd-box-003",
    "command_id": "cmd-789",
    "command_type": "Command.Genesis.Session.Theme.Request",
    "aggregate_id": "session-456",
    "aggregate_type": "GenesisSession",
    "payload": {
        "session_id": "session-456",
        "novel_id": "novel-789",
        "user_id": "user-789",
        "concept_context": {
            "concept_id": "concept-123",
            "confirmed_title": "时间的囚徒",
            "confirmed_premise": "一位物理学家在研究量子力学时意外发现了时间旅行的秘密...",
            "confirmed_themes": [
                "时间与命运的悖论",
                "科学发现的道德责任",
                "选择与后果的蝴蝶效应"
            ]
        },
        "user_requirements": {
            "depth_preference": "deep",
            "philosophical_focus": "时间旅行的伦理问题",
            "emotional_tone": "思辨与悬疑并重",
            "target_depth": "让读者思考科技进步与人性的关系"
        },
        "additional_context": {
            "inspiration_sources": ["《黑镜》", "《星际穿越》", "《蝴蝶效应》"],
            "avoid_cliches": ["简单的时间循环", "预定论宿命感"]
        }
    },
    "correlation_id": "flow-001",
    "causation_id": "event-confirm-concept-123",
    "user_id": "user-789",
    "status": "COMPLETED",
    "created_at": "2024-01-15T10:45:00Z",
    "processed_at": "2024-01-15T10:48:00Z",
    "error_message": null,
    "retry_count": 0,
    "metadata": {
        "stage_transition": {
            "from": "Stage_0",
            "to": "Stage_1"
        },
        "previous_quality_score": 8.5,
        "complexity_requested": "high"
    }
}
```

### 2. AI提出主题方案

#### Domain_Events 记录

```json
{
    "id": "domain-event-003",
    "event_id": "event-789",
    "event_type": "Genesis.Session.Theme.Proposed",
    "aggregate_id": "session-456",
    "aggregate_type": "GenesisSession",
    "aggregate_version": 5,
    "payload": {
        "session_id": "session-456",
        "novel_id": "novel-789",
        "stage": "Stage_1",
        "user_id": "user-789",
        "content": {
            "theme_id": "theme-456",
            "core_theme": "时间与命运的博弈：当科学触及神的领域",
            "sub_themes": [
                {
                    "name": "知识的代价",
                    "description": "每一次科学突破都伴随着不可预知的后果",
                    "examples": ["时间旅行发现导致现实分裂", "拯救一人毁灭世界"]
                },
                {
                    "name": "自由意志的幻象",
                    "description": "在无限的可能性中，选择是否真的存在意义",
                    "examples": ["每个选择都创造新现实", "所有可能都同时存在"]
                },
                {
                    "name": "责任的重量",
                    "description": "拥有改变一切的能力时，不行动也是一种选择",
                    "examples": ["知道灾难却无法阻止", "拯救行为的道德边界"]
                }
            ],
            "philosophical_questions": [
                "如果能改变过去，我们是否应该这样做？",
                "知识的边界在哪里？人类有权知道一切吗？",
                "个人的选择如何影响整个宇宙的命运？",
                "在无限的平行现实中，哪一个'我'才是真实的？",
                "当科学让我们接近神的能力时，我们是否准备好承担神的责任？"
            ],
            "emotional_core": "对未知的敬畏与对责任的恐惧",
            "target_impact": "让读者在享受科幻奇观的同时，深度思考科技发展与人性伦理的关系",
            "narrative_techniques": [
                {
                    "technique": "平行叙事线",
                    "description": "多个时间线同时展开，展现选择的不同结果"
                },
                {
                    "technique": "哲学对话",
                    "description": "角色间的深度讨论推动主题探索"
                },
                {
                    "technique": "道德困境设计",
                    "description": "每个重大情节点都包含复杂的伦理选择"
                },
                {
                    "technique": "象征与隐喻",
                    "description": "用科幻元素象征现实中的伦理问题"
                }
            ],
            "thematic_arc": {
                "opening": "科学发现的兴奋与好奇",
                "rising": "能力增长带来的诱惑与困惑",
                "climax": "面对终极选择的道德考验",
                "resolution": "接受责任与限制的智慧"
            }
        },
        "quality_score": 9.2,
        "generation_metadata": {
            "model_version": "gpt-4-turbo",
            "generation_time_ms": 3200,
            "confidence_score": 0.92,
            "iteration_count": 1,
            "prompt_tokens": 1850,
            "completion_tokens": 1240,
            "temperature": 0.7
        },
        "timestamp": "2024-01-15T10:48:00Z"
    },
    "correlation_id": "flow-001",
    "causation_id": "cmd-789",
    "user_id": "user-789",
    "occurred_at": "2024-01-15T10:48:00Z",
    "metadata": {
        "version": 1,
        "source": "outliner-agent",
        "trace_id": "trace-001",
        "agent_context": {
            "previous_concepts": ["concept-123"],
            "user_feedback": "希望更深入探讨时间旅行的伦理问题",
            "theme_analysis": {
                "complexity_score": 8.9,
                "originality_score": 8.7,
                "market_appeal": 8.3,
                "philosophical_depth": 9.1
            },
            "reference_works_considered": [
                "《黑镜》系列的科技伦理探讨",
                "《星际穿越》的时间哲学",
                "《蝴蝶效应》的因果关系"
            ]
        }
    }
}
```

## 错误处理示例

### 命令处理失败

#### Command_Box 记录（失败状态）

```json
{
    "id": "cmd-box-004",
    "command_id": "cmd-error-001",
    "command_type": "Command.Genesis.Session.World.Request",
    "aggregate_id": "session-456",
    "aggregate_type": "GenesisSession",
    "payload": {
        "session_id": "session-456",
        "novel_id": "novel-789",
        "user_id": "user-789",
        "theme_context": {
            "theme_id": "theme-456",
            "confirmed_themes": ["知识的代价", "自由意志的幻象"]
        }
    },
    "correlation_id": "flow-001",
    "causation_id": "event-theme-confirmed-456",
    "user_id": "user-789",
    "status": "FAILED",
    "created_at": "2024-01-15T11:00:00Z",
    "processed_at": "2024-01-15T11:02:30Z",
    "error_message": "AI服务暂时不可用：模型调用超时 (timeout: 30s)",
    "retry_count": 3,
    "metadata": {
        "error_details": {
            "error_type": "SERVICE_TIMEOUT",
            "service": "worldbuilder-agent",
            "timeout_duration": "30s",
            "attempted_retries": [
                {
                    "attempt": 1,
                    "timestamp": "2024-01-15T11:00:30Z",
                    "error": "连接超时"
                },
                {
                    "attempt": 2,
                    "timestamp": "2024-01-15T11:01:30Z",
                    "error": "读取超时"
                },
                {
                    "attempt": 3,
                    "timestamp": "2024-01-15T11:02:30Z",
                    "error": "请求超时"
                }
            ]
        },
        "next_retry_at": "2024-01-15T11:05:00Z",
        "max_retries_reached": true
    }
}
```

### 事件发布失败

#### Event_Outbox 记录（失败状态）

```json
{
    "id": "outbox-error-001",
    "event_id": "event-789",
    "topic": "genesis.session.events",
    "partition_key": "session-456",
    "headers": {
        "event_type": "Genesis.Session.Theme.Proposed",
        "content_type": "application/json",
        "correlation_id": "flow-001",
        "causation_id": "cmd-789",
        "aggregate_id": "session-456",
        "aggregate_type": "GenesisSession",
        "user_id": "user-789",
        "source": "outliner-agent",
        "trace_id": "trace-001",
        "timestamp": "2024-01-15T10:48:00Z",
        "schema_version": "1.0"
    },
    "payload": {
        "event_id": "event-789",
        "event_type": "Genesis.Session.Theme.Proposed",
        "aggregate_id": "session-456",
        "aggregate_type": "GenesisSession",
        "aggregate_version": 5,
        "payload": {
            "session_id": "session-456",
            "novel_id": "novel-789",
            "stage": "Stage_1",
            "user_id": "user-789",
            "content": {
                "theme_id": "theme-456",
                "core_theme": "时间与命运的博弈：当科学触及神的领域"
            }
        },
        "correlation_id": "flow-001",
        "causation_id": "cmd-789",
        "user_id": "user-789",
        "occurred_at": "2024-01-15T10:48:00Z",
        "metadata": {
            "version": 1,
            "source": "outliner-agent",
            "trace_id": "trace-001"
        }
    },
    "status": "FAILED",
    "created_at": "2024-01-15T10:48:01Z",
    "published_at": null,
    "retry_count": 2,
    "error_message": "Kafka集群不可用：无法连接到broker [kafka-broker-1:9092, kafka-broker-2:9092]"
}
```

## 数据流追踪示例

### 完整事件链

使用 `correlation_id` 追踪整个创世流程：

```sql
-- 查询流程 flow-001 的完整事件链
SELECT
    'COMMAND' as type,
    command_id as id,
    command_type as event_type,
    status,
    created_at,
    causation_id
FROM command_box
WHERE correlation_id = 'flow-001'

UNION ALL

SELECT
    'EVENT' as type,
    event_id as id,
    event_type,
    'COMPLETED' as status,
    occurred_at,
    causation_id
FROM domain_events
WHERE correlation_id = 'flow-001'

ORDER BY created_at;
```

### 预期结果

```
type    | id           | event_type                        | status     | created_at           | causation_id
--------|--------------|-----------------------------------|------------|---------------------|-------------
COMMAND | cmd-123      | Command.Genesis.Session.Start     | COMPLETED  | 2024-01-15 10:25:00 | null
EVENT   | event-001    | Genesis.Session.Started          | COMPLETED  | 2024-01-15 10:25:01 | cmd-123
COMMAND | cmd-456      | Command.Genesis.Session.Seed.Request | COMPLETED | 2024-01-15 10:26:00 | event-001
EVENT   | event-456    | Genesis.Session.ConceptProposed   | COMPLETED  | 2024-01-15 10:30:00 | cmd-456
COMMAND | cmd-789      | Command.Genesis.Session.Theme.Request | COMPLETED | 2024-01-15 10:45:00 | event-confirm-concept-123
EVENT   | event-789    | Genesis.Session.Theme.Proposed    | COMPLETED  | 2024-01-15 10:48:00 | cmd-789
```

这些示例展示了创世阶段数据在各个表中的完整存储格式，为系统实现提供了详细的参考。