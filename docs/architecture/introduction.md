# Introduction

本文档概述了“多智能体网络小说自动写作系统”的完整全栈架构，包括后端服务、前端实现及其集成方式。它将作为所有AI开发智能体的唯一技术事实来源，确保整个技术栈的一致性。

## 启动模板或现有项目

本项目将采用**分步模板策略**进行初始化。我们将使用 **Vite** 官方提供的 **React + TypeScript** 模板来创建前端应用，并将其集成到一个手动配置的、基于 **pnpm workspaces** 的Monorepo中。后端Python服务将在此Monorepo中从头开始设置。

## Change Log

| Date | Version | Description | Author |
| :--- | :------ | :---------- | :----- |
|      | 1.0     | Initial Draft | Winston (Architect) |
|      | 1.1     | 集成Neo4j管理世界观关系 | Winston (Architect) |
|      | 1.2     | 根据PRD v1.3和front-end-spec v1.2更新，重点调整数据模型、API接口、数据库模式以支持项目仪表盘和项目级知识库。 | Winston (Architect) |
