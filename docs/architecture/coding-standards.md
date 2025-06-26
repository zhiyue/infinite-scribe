# Coding Standards

## 核心标准

*   **语言与运行时版本:** Python `~3.11`, TypeScript `~5.2.2`, Node.js `~20.x.x`。
*   **代码风格与Linting:**
    *   **Python:** `Ruff` (Linter), `Black` (Formatter)。
    *   **TypeScript/JavaScript:** `ESLint` (共享配置), `Prettier` (共享配置)。
    *   **强制执行:** Git提交钩子和CI流水线。
*   **测试文件组织:** Python (`test_*.py` 或 `*_test.py`), TypeScript (`*.test.ts(x)` 或 `*.spec.ts(x)`), 与被测模块同级。

## 命名约定

| 元素 | 约定 | Python示例 | TypeScript示例 |
| :--- | :--- | :--- | :--- |
| 变量 | snake_case (Py), camelCase (TS) | `user_name` | `userName` |
| 函数/方法 | snake_case (Py), camelCase (TS) | `get_user_data()` | `getUserData()` |
| 类名 | PascalCase | `UserDataProcessor` | `UserDataProcessor` |
| 常量 | UPPER_SNAKE_CASE | `MAX_RETRIES` | `MAX_RETRIES` |
| 文件名 (Py) | snake_case.py | `user_service.py` | N/A |
| 文件名 (TS) | kebab-case.ts 或 PascalCase.tsx | N/A | `user-service.ts`, `UserProfile.tsx` |
| Pydantic模型字段 | snake_case | `class User(BaseModel): user_id: UUID` | N/A |

## 关键规则 (AI智能体必须严格遵守)

*   **1. 禁止硬编码敏感信息:** 通过环境变量或配置服务加载。
*   **2. 严格的类型提示:** Python类型提示, TypeScript `strict`模式。
*   **3. 优先使用异步/非阻塞IO:** Python后端使用 `async/await`。
*   **4. 结构化日志记录:** 使用项目定义的结构化日志格式，含相关ID。
*   **5. 错误处理规范:** 遵循定义的错误处理策略。
*   **6. 遵循Monorepo结构:** 代码放置在正确位置，共享代码在 `packages/`。
*   **7. 事件驱动通信:** Agent间通信必须通过Kafka。
*   **8. 幂等性设计:** 事件消费者逻辑必须幂等。
*   **9. Neo4j操作封装:** 对Neo4j的操作应通过专门的知识图谱服务或共享库进行封装 (例如在 `packages/common-utils/py_utils/neo4j_connector.py`)，避免在各个Agent中直接编写复杂的Cypher查询。所有查询必须与 `novel_id` 关联。

## 语言特定指南

*   **Python:** 依赖在 `requirements.txt` 或 `pyproject.toml` 中声明。建议独立虚拟环境。
*   **TypeScript:** 利用 `tsconfig.json` 的 `paths` 别名引用共享包。
