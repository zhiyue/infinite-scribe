# 后端脚本目录

本目录包含 InfiniteScribe 后端项目的各种开发和维护脚本，用于简化开发、部署和数据库管理任务。

## 📁 目录结构

```
apps/backend/scripts/
├── README.md                          # 本文件
├── README_API_GATEWAY.md              # API Gateway 运行指南
├── apply_db_functions.py              # 数据库函数和触发器应用脚本
├── verify_tables.py                   # 数据库表验证脚本
├── type-check.sh                      # 代码类型检查脚本
├── create_db_functions.sql            # 数据库函数创建SQL（完整版）
├── create_db_functions_clean.sql      # 数据库函数创建SQL（清洁版）
├── run-api-gateway-simple.sh          # 简单API Gateway启动脚本
├� run-api-gateway-local.sh            # 本地开发API Gateway启动脚本
└── run-api-gateway-dev.sh             # 开发环境API Gateway启动脚本
```

## 🛠️ 主要脚本

### 数据库管理脚本

#### 1. apply_db_functions.py
**用途**: 应用数据库触发器和函数的自动化脚本

**功能**:
- 创建时间戳自动更新触发器 (`update_updated_at_column`)
- 创建版本号自动递增触发器 (`increment_version`)
- 创建领域事件保护机制 (`prevent_domain_event_modification`)
- 创建小说进度更新函数 (`update_novel_completed_chapters`)
- 创建事件发件箱相关函数
- 创建异步任务统计视图

**使用方法**:
```bash
# 在项目根目录运行
cd apps/backend
python scripts/apply_db_functions.py
```

#### 2. verify_tables.py
**用途**: 验证数据库中的表是否已成功创建

**功能**:
- 检查ORM定义的表与数据库实际表的差异
- 按类别分组显示表状态（核心业务、创世流程、架构机制、用户认证）
- 检查枚举类型的创建状态
- 提供详细的验证报告

**使用方法**:
```bash
# 在项目根目录运行
cd apps/backend
python scripts/verify_tables.py
```

### 代码质量检查脚本

#### 3. type-check.sh
**用途**: 运行完整的代码类型检查流程

**功能**:
- **Ruff**: 语法检查和基本代码质量检查
- **MyPy**: Python类型检查
- **Pyright**: 严格类型检查

**使用方法**:
```bash
# 在项目根目录运行
cd apps/backend
chmod +x scripts/type-check.sh
./scripts/type-check.sh
```

### API Gateway 运行脚本

#### 4. run-api-gateway-simple.sh
**用途**: 最简单的API Gateway启动方式，不检查外部服务

**使用方法**:
```bash
./scripts/run-api-gateway-simple.sh
```

#### 5. run-api-gateway-local.sh
**用途**: 本地开发环境启动脚本，使用本地配置

**特点**:
- 自动切换到 `.env.local` 配置
- 检查远程服务连接（但不强制要求）
- 提供详细的启动信息

**使用方法**:
```bash
./scripts/run-api-gateway-local.sh
```

#### 6. run-api-gateway-dev.sh
**用途**: 开发服务器环境启动脚本，连接到远程基础设施

**特点**:
- 自动切换到 `.env.dev` 配置
- 强制检查远程服务连接
- 适合使用远程开发基础设施的场景

**使用方法**:
```bash
./scripts/run-api-gateway-dev.sh
```

## 🚀 快速开始

### 1. 数据库初始化
```bash
# 应用数据库函数和触发器
cd apps/backend
python scripts/apply_db_functions.py

# 验证表创建状态
python scripts/verify_tables.py
```

### 2. 启动开发服务
```bash
# 选择合适的启动脚本
./scripts/run-api-gateway-local.sh    # 本地开发
./scripts/run-api-gateway-dev.sh      # 开发服务器
```

### 3. 代码质量检查
```bash
# 运行类型检查
./scripts/type-check.sh
```

## 📋 详细指南

- **API Gateway 详细使用指南**: 请参考 [README_API_GATEWAY.md](./README_API_GATEWAY.md)
- **数据库函数详情**: 查看 [create_db_functions.sql](./create_db_functions.sql) 了解完整的SQL定义
- **环境配置**: 确保在根目录有正确的 `.env.*` 配置文件

## 🔧 环境要求

- Python 3.11+
- uv 包管理器
- PostgreSQL 数据库连接
- 必要的环境变量配置

## 🐛 常见问题

### 数据库连接问题
- 确保数据库服务正在运行
- 检查 `.env` 文件中的数据库连接配置
- 确认数据库用户权限

### 脚本权限问题
```bash
# 给shell脚本添加执行权限
chmod +x scripts/*.sh
```

### 依赖问题
```bash
# 安装项目依赖
cd apps/backend
uv sync --all-extras
```

## 📝 开发指南

### 添加新脚本
1. 脚本文件应该具有明确的单一职责
2. 添加适当的注释和文档
3. 包含错误处理和用户友好的错误信息
4. 更新本README文件以包含新脚本的说明

### 脚本命名规范
- Python脚本: 使用下划线命名法，如 `apply_db_functions.py`
- Shell脚本: 使用下划线命名法，如 `type-check.sh`
- SQL文件: 使用下划线命名法，如 `create_db_functions.sql`

---

**注意**: 本目录中的脚本主要用于开发和部署环境，生产环境使用时请进行充分测试。