# Infrastructure and Deployment

## 基础设施即代码 (Infrastructure as Code - IaC)

*   **工具:** **Terraform** 
    *   **版本:** Terraform `~1.7.0`
*   **位置:** 所有IaC代码将存放在Monorepo的 `infrastructure/` 目录下。
*   **方法:**
    *   为每个环境（开发、预发布、生产）创建独立的Terraform工作区。
    *   核心基础设施（如VPC、Kafka集群、PostgreSQL, Milvus, **Neo4j实例**）将作为基础模块进行管理。
    *   应用服务（如Agent容器、API网关）的部署将引用这些基础模块。

## 部署策略

*   **策略:** **基于容器的蓝绿部署 (Blue/Green Deployment)** 或 **金丝雀发布 (Canary Releases)**。
*   **CI/CD平台:** **GitHub Actions**。
*   **流水线配置:** 位于 `.github/workflows/main.yml`。
    *   **阶段:** 代码检出 -> Lint/Test -> 构建Docker镜像 -> 推送镜像 -> (可选)安全扫描 -> Terraform应用 -> 部署服务 -> E2E测试 -> 流量切换/增加。

## 环境

| 环境名称 | 用途 | 部署方式 | 数据库/事件总线/图库 |
| :--- | :--- | :--- | :--- |
| **本地 (Local)** | 日常开发与单元测试 | `docker-compose up` | 本地Docker容器 (含Neo4j) |
| **开发 (Development)** | 共享的开发/集成测试环境 | CI/CD自动部署 (来自`develop`分支) | 专用的云上开发实例 (含Neo4j) |
| **预发布 (Staging)** | 模拟生产环境，进行UAT和E2E测试 | CI/CD自动部署 (来自`release/*`分支或手动触发) | 生产环境的精确副本 (含Neo4j，数据可能脱敏) |
| **生产 (Production)** | 最终用户访问的实时环境 | CI/CD手动批准部署 (来自`main`分支) | 高可用的生产级云实例 (含Neo4j) |

## 环境提升流程
```mermaid
graph LR
    A[本地开发] -->|提交到 feature/* 分支| B(GitHub PR)
    B -->|合并到 develop 分支| C[开发环境自动部署]
    C -->|通过集成测试| D(创建 release/* 分支)
    D -->|合并到 release/* 分支| E[预发布环境自动部署]
    E -->|通过UAT/E2E测试| F(创建部署到生产的PR)
    F -->|批准并合并到 main 分支| G[生产环境手动批准部署]
```

## 回滚策略

*   **主要方法:** 蓝绿切换, Docker镜像回滚。
*   **触发条件:** 关键KPI恶化, E2E测试失败, 大量用户负面反馈。
*   **恢复时间目标 (RTO):** 生产环境回滚操作应在 **15分钟内** 完成。
