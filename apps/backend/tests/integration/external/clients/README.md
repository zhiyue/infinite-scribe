# External Client Integration Tests

本目录包含与外部服务的真实集成测试。

## 测试文件

- `test_ollama_embedding_integration.py` - Ollama embedding服务的集成测试

## 配置特性

### 仅本地运行 (CI自动跳过)

这些集成测试通过**环境变量检测**自动跳过CI执行：

```python
pytestmark = [
    pytest.mark.skipif(
        os.getenv("CI") is not None or os.getenv("GITHUB_ACTIONS") is not None,
        reason="Ollama integration tests only run locally",
    ),
    pytest.mark.integration,
]
```

**GitHub Actions 自动跳过:** GitHub Actions 默认设置 `GITHUB_ACTIONS=true`，测试会自动跳过  
**其他CI系统:** 设置 `CI=true` 环境变量即可跳过测试

### Fixture冲突避免

本目录使用独立的`conftest.py`来避免与主集成测试fixture的冲突：
- 覆盖有问题的邮件服务模拟fixture
- 提供独立的测试环境，不依赖其他集成测试的共享fixture

## 环境变量

- `TEST_OLLAMA_URL` - 覆盖默认的Ollama URL (默认: `http://localhost:11434`)
- `TEST_OLLAMA_MODEL` - 覆盖默认模型 (默认: `nomic-embed-text`)
- `CI` 或 `GITHUB_ACTIONS` - 设置时测试将被跳过

## 运行测试

### 本地开发

```bash
# 运行所有Ollama集成测试 (如果Ollama不可用将跳过)
uv run pytest tests/integration/external/clients/test_ollama_embedding_integration.py -v

# 运行特定测试
uv run pytest tests/integration/external/clients/test_ollama_embedding_integration.py::TestOllamaEmbeddingIntegration::test_single_embedding_generation -v

# 使用自定义Ollama URL
TEST_OLLAMA_URL=http://localhost:11434 uv run pytest tests/integration/external/clients/test_ollama_embedding_integration.py -v
```

### CI环境

```bash
# 测试在CI中将被跳过
CI=true uv run pytest tests/integration/external/clients/test_ollama_embedding_integration.py -v
# 输出: 11 skipped in 0.11s
```

## 测试覆盖范围

集成测试覆盖以下方面：

1. **连接健康检查** - 验证Ollama服务连通性
2. **单文本嵌入** - 为单个文本生成嵌入
3. **批量嵌入** - 为多个文本生成嵌入
4. **嵌入一致性** - 相同文本产生一致的嵌入
5. **文本差异化** - 不同文本产生不同的嵌入
6. **Unicode支持** - 处理国际字符和表情符号
7. **长文本处理** - 处理较长的文本段落
8. **输入验证** - 输入验证（空文本等）
9. **错误处理** - 无效模型和服务错误
10. **并发请求** - 多个同时请求
11. **提供者属性** - 元数据和字符串表示

## Ollama设置

要运行这些测试，您需要在本地安装并运行Ollama：

```bash
# 安装Ollama (macOS/Linux)
curl -fsSL https://ollama.ai/install.sh | sh

# 启动Ollama服务
ollama serve

# 拉取嵌入模型
ollama pull nomic-embed-text
```

## 测试行为

- **服务可用**: 测试针对真实的Ollama实例执行
- **服务不可用**: 测试被优雅跳过并提供信息性消息
- **CI环境**: 所有测试被跳过以避免外部依赖
- **验证测试**: 总是运行（不需要外部服务）

## 为什么是集成测试？

这些是真正的集成测试，因为它们：
- 测试与真实外部服务(Ollama)的集成
- 验证网络通信和协议正确性
- 测试实际的服务响应和错误处理
- 确保嵌入质量和一致性

与组件测试不同，这些测试不使用模拟，而是验证与实际服务的真实集成。