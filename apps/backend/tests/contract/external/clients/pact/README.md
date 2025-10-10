# Pact 消费者契约测试（pact-python v3 / FFI）

## 概述

使用 Pact v3（基于 Rust FFI）定义消费者契约，生成符合 V3/V4 规范结构的 pact 文件（matchingRules 按 body/header 分区，而非 V2 的扁平路径）。

核心原则：只测试客户端真正依赖的接口形状与关键业务行为；避免把基础设施/网络问题混入契约。

## 推荐测试结构（v3 DSL）

```python
import pytest
from pact import match

pytestmark = [
    pytest.mark.contract,
    pytest.mark.pact_pair(provider="ollama-api"),
    pytest.mark.asyncio,
]

async def test_single_input_embedding_contract(pact, external_client_builder):
    (
        pact.upon_receiving("a request for single text embedding")
        .given("Ollama embedding model is available")
        .with_request("POST", "/api/embed")
        .with_header("Content-Type", match.regex("application/json; charset=utf-8", regex=r"^application/json(;.*)?$"), part="Request")
        .with_body({"model": "nomic-embed-text", "input": "Hello world"}, part="Request")
        .will_respond_with(200)
        .with_header("Content-Type", match.regex("application/json; charset=utf-8", regex=r"^application/json(;.*)?$"))
        .with_body({"embedding": match.each_like(0.1, min=1)})
    )

    with pact.serve() as srv:
        client = external_client_builder(str(srv.url))
        async with client.session():
            assert await client.get_embedding("Hello world")
```

断言保持最小化（存在即真）：结构与类型由匹配器保证。

## 环境准备

```bash
cd apps/backend
uv add --group dev pact-python==3.0.0a1
```

## 目录结构

```
tests/contract/external/clients/pact/
├── consumer_tests/
│   ├── conftest.py        # v3 夹具（pact.serve + 会后聚合）
│   └── test_*.py
└── pacts/
    └── {consumer}-{provider}.json
```

## 运行

```bash
cd apps/backend
uv run pytest tests/contract -m contract -v
```

## V4 结构示例（节选）

```json
{
  "interactions": [
    {
      "description": "a request for single text embedding",
      "providerStates": [{"name": "Ollama embedding model is available"}],
      "request": {
        "method": "POST",
        "path": "/api/embed",
        "headers": {"Content-Type": ["application/json; charset=utf-8"]},
        "body": {"contentType": "application/json;charset=utf-8", "encoded": false, "content": {"model": "nomic-embed-text", "input": "Hello"}},
        "matchingRules": {"header": {"Content-Type": {"combine": "AND", "matchers": [{"match": "regex", "regex": "^application/json(;.*)?$"}]}}}
      },
      "response": {
        "status": 200,
        "headers": {"Content-Type": ["application/json; charset=utf-8"]},
        "body": {"contentType": "application/json;charset=utf-8", "encoded": false, "content": {"embedding": [0.1]}}
      },
      "type": "Synchronous/HTTP"
    }
  ]
}
```

## 契约校验（Provider Verification）

生成的 pact 文件可以使用 pact_verifier_cli 工具对提供方进行校验。

### 安装校验工具

从 [pact-standalone](https://github.com/pact-foundation/pact-standalone) 获取 pact_verifier_cli 工具。

### 校验命令示例

```bash
# 校验 Ollama API 契约
pact_verifier_cli \
  --file tests/contract/external/clients/pacts/infinite-scribe-backend-ollama-api.json \
  --hostname 127.0.0.1 \
  --port 11434

# 校验其他服务契约
pact_verifier_cli \
  --file tests/contract/external/clients/pacts/{consumer}-{provider}.json \
  --hostname {provider_host} \
  --port {provider_port}
```

### 校验流程

1. **确保服务运行**: 提供方服务（如 Ollama）需要在指定地址运行
2. **执行校验**: 运行 pact_verifier_cli 命令
3. **检查结果**: 校验工具会逐个验证 pact 文件中的交互
4. **处理失败**: 如有失败，检查提供方实现或更新契约

### 校验参数说明

- `--file`: pact 文件路径
- `--hostname`: 提供方服务主机地址
- `--port`: 提供方服务端口
- `--provider-states-setup-url`: 提供方状态设置端点（可选）

## 常见问题

- 没有生成 pact：确保在 backend 目录下运行，并在 `with pact.serve():` 内发起真实请求
- 匹配器缺失：使用 v3 的 `pact.match` API（like/regex/each_like）
- 合并覆盖：本仓库已实现"按测试输出 + 会后聚合"，避免 merge 丢失匹配器
- 校验失败：检查提供方服务是否正常运行，或契约是否需要更新

