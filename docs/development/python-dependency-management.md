# Python 依赖管理说明

## 统一环境方式

本项目采用**统一Python环境**的管理方式，所有后端服务共享相同的依赖配置。

### 核心原则

1. **单一 pyproject.toml**
   - 位置：后端目录 `apps/backend/pyproject.toml`
   - 包含所有后端服务的依赖
   - 统一管理后端Python依赖

2. **单一虚拟环境**
   - 位置：后端目录 `apps/backend/.venv`
   - 所有后端服务共享同一个Python环境
   - 确保依赖版本一致性

3. **使用 uv 包管理器**
   
   项目使用 [uv](https://github.com/astral-sh/uv) 作为 Python 包管理器，相比 pip 的优势：
   - ⚡ **极快的速度**：比 pip 快 10-100 倍
   - 🔒 **自动生成锁文件**：确保依赖版本一致
   - 📦 **内置虚拟环境管理**：无需单独安装 virtualenv
   - 🔄 **智能缓存**：避免重复下载
   
   ```bash
   # 创建虚拟环境
   uv venv
   
   # 安装所有依赖（包括开发依赖）
   uv sync --dev
   
   # 仅安装生产依赖
   uv sync
   
   # 添加新依赖
   uv add package-name
   
   # 添加开发依赖
   uv add --dev package-name
   
   # 更新依赖
   uv sync --upgrade
   ```

### 项目结构

```
infinite-scribe/
├── apps/
│   └── backend/
│       ├── .venv/          # 后端虚拟环境
│       ├── pyproject.toml  # 后端依赖配置
│       ├── uv.lock         # 锁定的依赖版本
│       ├── src/            # 源代码
│       ├── tests/          # 测试代码
│       └── Dockerfile      # 容器配置
└── packages/               # 共享包
```

### Docker 构建

Docker构建时需要从后端目录作为上下文：

```yaml
# docker-compose.yml
api-gateway:
  build:
    context: apps/backend  # 使用后端目录作为构建上下文
    dockerfile: Dockerfile
```

### 开发流程

1. **初始化环境**
   ```bash
   cd /path/to/infinite-scribe/apps/backend
   uv venv
   uv sync --dev
   ```

2. **激活环境**
   ```bash
   cd apps/backend
   source .venv/bin/activate  # Linux/Mac
   # or
   .venv\Scripts\activate     # Windows
   ```

3. **运行测试**
   ```bash
   cd apps/backend
   python -m pytest tests/
   ```

4. **运行服务**
   ```bash
   cd apps/backend
   python -m src.api.main
   ```

### 注意事项

- 后端Python依赖统一在 `apps/backend/pyproject.toml` 中管理
- 使用 `apps/backend/.venv` 虚拟环境进行开发
- Docker构建时确保使用后端目录作为上下文路径
- 开发时始终在后端目录中进行Python环境管理