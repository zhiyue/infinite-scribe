# 契约测试

契约测试通过测试应用程序与外部服务之间的实际契约/接口，验证外部服务集成是否正确工作。

## 目录结构

```
tests/contract/
├── conftest.py                    # 契约测试统一配置和夹具
├── external/clients/
│   ├── pact/
│   │   ├── consumer_tests/        # 使用 Pact 的消费者契约测试
│   │   ├── pacts/                 # 生成的 pact 契约文件
│   │   └── pact_logs/             # Pact 日志文件
│   └── test_*_contract.py         # 接口/行为契约测试
```

## 契约测试类型

### 1. 接口契约测试

验证实现是否正确履行接口契约的测试：

- **位置**: `tests/contract/external/clients/test_*_contract.py`
- **目的**: 确保接口的所有实现表现一致
- **工具**: 使用 pytest 和 mocking 进行隔离测试

### 2. Pact 消费者测试

定义我们的应用（消费者）与外部 API（提供者）之间契约的测试：

- **位置**: `tests/contract/external/clients/pact/consumer_tests/`
- **目的**: 生成定义预期 API 交互的 pact 文件
- **工具**: Pact 框架 + pytest
- **输出**: `pacts/` 目录中的 JSON pact 文件

## 运行契约测试

### 接口契约测试

```bash
# 运行所有契约测试
pytest tests/contract/ -v

# 运行特定提供者的契约测试
pytest tests/contract/external/clients/test_embedding_provider_contract.py -v
```

### Pact 消费者测试

```bash
# 首先安装 pact-python v3（FFI）
cd apps/backend
uv add --group dev pact-python==3.0.0a1

# 运行 pact 消费者测试（生成 pact 文件）
uv run pytest tests/contract/external/clients/pact/consumer_tests -m contract -v

# 查看生成的 pact 文件
ls tests/contract/external/clients/pact/pacts/
```

## Pact 工作流程

1. **消费者测试**: 定义与外部 API 的预期交互
2. **Pact 生成**: 测试运行时生成 JSON pact 文件
3. **Pact 共享**: 与提供者团队共享 pact 文件（通过 Pact Broker 或 git）
4. **提供者验证**: 外部服务团队验证其 API 是否满足契约

## 最佳实践

### 接口契约测试

- 测试所有实现是否满足相同的接口契约
- 使用 mocking 将测试与外部依赖隔离
- 专注于行为和类型正确性，而非实现细节

### Pact 消费者测试

- 定义应用程序实际使用的现实交互
- 使用 Pact v3 匹配器（match.like, match.each_like, match.regex）进行灵活匹配
- 包含成功和错误场景
- 保持交互专注且原子化

## CI/CD 集成

- 契约测试应在 CI 中运行以捕获破坏性更改
- Pact 文件可以上传到 Pact Broker 进行契约共享
- 提供者验证可以集成到外部服务的 CI 中

## 故障排除

### Pact 测试失败

- 确保已安装 pact-python v3: `cd apps/backend && uv add --group dev pact-python==3.0.0a1`
- 检查模拟交互是否与实际请求/响应格式匹配
- 验证 pact 文件是否在正确目录中生成

### 接口测试失败

- 检查是否实现了所有必需的接口方法
- 验证错误处理是否遵循预期模式
- 确保正确的类型注解和返回类型

## 扩展性设计

### Marker-Driven 模式

使用 `@pytest.mark.pact_pair(provider="provider-name")`
标记可以轻松扩展到多个提供者：

```python
@pytest.mark.pact_pair(provider="ollama-api")
@pytest.mark.asyncio
async def test_ollama_embedding(pact_generic):
    # 测试 Ollama 提供者

@pytest.mark.pact_pair(provider="openai-api", client_kwargs={"api_key": "test"})
@pytest.mark.asyncio
async def test_openai_embedding(pact_generic):
    # 测试 OpenAI 提供者
```

### 添加新提供者

1. 在 `conftest.py` 的 `CLIENT_BUILDERS` 中注册构造器
2. 使用 `@pytest.mark.pact_pair` 标记测试
3. 编写与提供者特定的契约测试

## 示例用法

### 运行特定类型的测试

```bash
# 只运行契约相关测试
pytest tests/contract/ -m contract -v

# 运行所有嵌入相关的契约测试
pytest tests/contract/external/clients/ -k embedding -v

# 运行特定的 Pact 消费者测试
pytest tests/contract/external/clients/pact/consumer_tests/test_ollama_embedding_consumer.py -v
```

### 查看生成的契约文件

```bash
# 查看生成的 pact 文件
cat tests/contract/external/clients/pact/pacts/infinite-scribe-backend-ollama-api.json

# 验证契约文件格式
jq . tests/contract/external/clients/pact/pacts/*.json
```
