# 部署运维指南

## 回滚步骤详细设计

```yaml
rollback:
  steps:
    - name: 停止流量
      command: kubectl scale deploy/api --replicas=0
    - name: 回滚数据库
      command: alembic downgrade -1
    - name: 回滚应用镜像
      command: kubectl rollout undo deploy/api
    - name: 恢复流量并验证
      command: |
        kubectl scale deploy/api --replicas=2
        ./scripts/smoke-test.sh
      success_criteria:
        - http_2xx_rate > 0.99
        - p95_latency_ms < 3000
```

## 容量参数配置

```yaml
capacity:
  resources:
    requests: { cpu: '500m', memory: '512Mi' }
    limits: { cpu: '2000m', memory: '2Gi' }
  concurrency:
    max_connections: 1000
    max_requests_per_second: 500
    max_concurrent_requests: 100
  queues:
    outbox_sender: { max_size: 20000, batch: 100, max_delay: 60s }
  pools:
    database: { min_size: 10, max_size: 100, max_idle_time: 300s }
    redis: { min_size: 5, max_size: 50 }
  rate_limits:
    - key: 'user_id'
      limit: 60
      window: 60s
```

### 自动伸缩参数

```yaml
autoscaling:
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        { name: cpu, target: { type: Utilization, averageUtilization: 70 } }
    - type: Resource
      resource:
        { name: memory, target: { type: Utilization, averageUtilization: 80 } }
```

## 测试策略

### 测试目标

- 降低质量风险；保障对话与事件链路端到端稳定；满足 NFR 延迟目标

### 风险矩阵（摘要）

| 区域       | 风险 | 必须            | 可选 |
| ---------- | ---- | --------------- | ---- |
| 会话一致性 | 高   | 单元、集成、E2E | -    |
| 事件可靠性 | 高   | 契约、集成      | 弹性 |
| 图一致性   | 中   | 集成、属性      | -    |
| 向量检索   | 中   | 集成            | 性能 |

### 按层最小化

- 单元：Outbox 序列化、命令幂等、映射函数、错误分类
- 契约：API OpenAPI 契约、事件 Envelope 契约
- 集成：Kafka/Redis/Neo4j/Milvus 依赖的最小可用路径
- E2E（≤3）：创世主流程；断线重连 SSE；低分重试到 DLT

### CI 门控与退出标准

- PR：单元+契约 必须通过；暂存：集成+E2E 必须通过；Sev1/Sev2=0

## 测试点设计

### 单元测试（示例）

```typescript
describe('orchestrator.mapDomainToCapability', () => {
  it('将 Theme.Requested 映射到 Outliner 任务', () => {
    // Arrange / Act / Assert
  })
})
```

### 集成测试（示例）

```python
def test_end_to_end_flow(client, kafka, redis):
    # 1. 创建会话 → 2. 提交消息 → 3. 消费任务 → 4. 回流领域事件 → 5. SSE 下行
    ...
```

## 部署细节

### CI/CD Pipeline（建议）

```yaml
stages: [build, test, deploy]
build:
  stage: build
  script:
    - pnpm install
    - pnpm backend lint && pnpm frontend lint
    - docker build -t $IMAGE:$CI_COMMIT_SHA apps/backend
test:
  stage: test
  script:
    - pnpm backend test
    - pnpm frontend test
deploy:
  stage: deploy
  script:
    - kubectl set image deploy/api api=$IMAGE:$CI_COMMIT_SHA
    - kubectl rollout status deploy/api
    - ./scripts/smoke-test.sh
```

## 依赖管理

### 外部依赖

| 依赖       | 版本 | 用途           | 降级方案     |
| ---------- | ---- | -------------- | ------------ |
| PostgreSQL | 14+  | 会话/事件表    | 只读降级     |
| Redis      | 7+   | 缓存与 SSE     | 降级为无 SSE |
| Kafka      | 3.x+ | 事件总线       | 暂存 Outbox  |
| Neo4j      | 5.x+ | 知识图谱与校验 | 关闭校验     |
| Milvus     | 2.4+ | 嵌入检索       | 关闭向量检索 |

### 版本兼容性（运行环境）

```json
{
  "python": ">=3.11",
  "node": ">=20",
  "pnpm": ">=9"
}
```

## 与HLD的关系

- 统一遵循 HLD 的架构与事件命名；表结构与 Topic 映射完全对齐
- NFR：首 token < 3s、能力生成 < 5s；指标与容量配置已在本 LLD 细化

## 交付物

- 完整接口签名（API/Orchestrator/Agents/SSE）
- 状态机与 ER 图
- 数据结构定义与 DDL 摘要
- 异常矩阵与重试实现
- 回滚步骤与容量配置
- 测试策略与关键测试点
- 部署与依赖矩阵