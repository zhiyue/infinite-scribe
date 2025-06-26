# Test Strategy and Standards

## 测试理念
*   **测试驱动开发 (TDD) / 行为驱动开发 (BDD) - 鼓励但不强制。**
*   **覆盖率目标:** 单元测试核心逻辑 **85%**。集成测试覆盖关键交互。
*   **测试金字塔:** (如图所示)
    ```text
            /\
           /  \
          /E2E \  
         /______\
        /        \
       /集成测试 \ 
      /__________\
     /            \
    /  单元测试    \ 
   /______________\
    ```

## 测试类型与组织
### 1. 单元测试 (Unit Tests)
*   **框架:** Python: `Pytest ~8.1.0`; TypeScript: `Vitest ~1.4.0`。
*   **文件约定:** (如编码标准中所述)。
*   **模拟库:** Python: `unittest.mock`, `pytest-mock`; TypeScript: `Vitest`内置。
*   **AI要求:** 为所有公开函数/方法生成测试，覆盖正常、边界、错误情况，遵循AAA，模拟所有外部依赖。
### 2. 集成测试 (Integration Tests)
*   **范围:** API网关与Agent交互, Agent与Kafka交互, Agent与数据库(PG, Milvus, Neo4j)交互。
*   **位置:** 各自服务的 `tests/integration` 目录。
*   **测试基础设施:** 使用 `testcontainers` 启动临时的PG, Milvus, Neo4j, Kafka实例。模拟LiteLLM或测试与真实LiteLLM(模拟后端)的集成。
### 3. 端到端测试 (End-to-End Tests)
*   **框架:** Playwright `~1.42.0`。
*   **范围:** MVP阶段覆盖“创世流程”和“单章节生成与查看”。
*   **环境:** 预发布 (Staging) 环境。

## 测试数据管理
*   **单元测试:** 硬编码模拟数据。
*   **集成测试:** 数据工厂/固件创建数据，测试后清理/回滚。
*   **端到端测试:** 专用可重置E2E数据库或测试用例自管理数据。

## 持续测试
*   **CI集成:** 单元、集成测试在每次提交/PR时自动运行 (GitHub Actions)。E2E测试在合并到`develop`/`release`后触发。
*   **性能测试 (后MVP):** `k6` 或 `Locust`。
*   **安全测试 (后MVP):** SAST/DAST工具。
