# Prefect v3 使用指南

## 服务架构

InfiniteScribe 使用 Prefect v3 进行工作流编排，包含以下组件：

1. **Prefect API Server** - 提供 REST API 和 Web UI
2. **Background Service** - 处理调度、通知等后台任务
3. **Worker** - 执行实际的工作流任务
4. **PostgreSQL** - 存储工作流元数据

### 架构图

```
┌─────────────┐     ┌──────────────┐     ┌────────────┐
│   Web UI    │────▶│   API Server │────▶│ PostgreSQL │
└─────────────┘     └──────────────┘     └────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │  Background  │
                    │   Service    │
                    └──────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │    Worker    │ ◀── 执行实际任务
                    └──────────────┘
```

**重要**: Worker 是必需的，因为它负责实际执行您的 Python 工作流代码！

## 访问地址

- **Web UI**: http://192.168.2.201:4200
- **API**: http://192.168.2.201:4200/api
- **API 文档**: http://192.168.2.201:4200/docs
- **查看 Worker**: 在 UI 中点击 "Work Pools" → "default-pool"
- **监控任务**: 在 UI 中查看 "Flow Runs"

## 快速开始

### 1. 创建工作流

在 `flows/` 目录下创建 Python 文件：

```python
from prefect import flow, task

@task
def process_novel_chapter(chapter_id: str):
    # 处理章节逻辑
    return f"Processed chapter {chapter_id}"

@flow(name="novel-processing")
def process_novel(novel_id: str):
    chapters = ["ch1", "ch2", "ch3"]
    for chapter in chapters:
        process_novel_chapter(chapter)
```

### 2. 部署工作流

```python
from prefect import serve

deployment = process_novel.to_deployment(
    name="novel-processor",
    work_pool_name="default-pool"
)

serve(deployment)
```

### 3. 运行工作流

通过 API 触发：
```bash
curl -X POST http://192.168.2.201:4200/api/deployments/novel-processor/create_flow_run \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"novel_id": "123"}}'
```

或在 Python 代码中：
```python
from prefect import get_client

async def run_flow():
    async with get_client() as client:
        deployment = await client.read_deployment_by_name("novel-processing/novel-processor")
        flow_run = await client.create_flow_run_from_deployment(
            deployment_id=deployment.id,
            parameters={"novel_id": "123"}
        )
```

## Worker 管理

### 查看 Worker 状态
```bash
docker compose logs prefect-worker
```

### 重启 Worker
```bash
docker compose restart prefect-worker
```

### 扩展 Worker
可以启动多个 Worker 容器来增加并发处理能力。

## 最佳实践

1. **任务设计**
   - 保持任务原子性和幂等性
   - 使用适当的重试策略
   - 记录关键操作日志

2. **错误处理**
   - 使用 Prefect 的内置重试机制
   - 设置合理的超时时间
   - 配置失败通知

3. **性能优化**
   - 使用任务并发执行
   - 合理设置 Worker 数量
   - 监控资源使用情况

## 集成示例

### 与 Kafka 集成
```python
from prefect import flow, task
from kafka import KafkaConsumer

@task
def consume_kafka_events():
    consumer = KafkaConsumer(
        'novel-events',
        bootstrap_servers='192.168.2.201:9092'
    )
    for message in consumer:
        yield message.value

@flow
def process_kafka_stream():
    for event in consume_kafka_events():
        # 处理事件
        pass
```

### 与 Milvus 集成
```python
from prefect import task
from pymilvus import connections

@task
def store_embeddings(embeddings, novel_id):
    connections.connect(host='192.168.2.201', port='19530')
    # 存储向量逻辑
```

## 故障排查

1. **Worker 无法连接到 API**
   - 检查网络配置
   - 验证 PREFECT_API_URL 环境变量

2. **任务执行失败**
   - 查看 Worker 日志
   - 检查 Python 依赖
   - 验证文件路径

3. **UI 无法访问**
   - 确保防火墙允许 4200 端口
   - 检查 CORS 配置