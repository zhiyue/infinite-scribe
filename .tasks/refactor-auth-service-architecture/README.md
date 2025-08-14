# 重构 AuthService 类架构实现高内聚低耦合

## 任务背景

当前的 `AuthService` 类存在严重的架构设计问题，主要体现在：

1. **硬编码依赖**: 直接实例化 axios、localStorage 等依赖，无法替换或测试
2. **单例模式问题**: 导出单例实例，测试时存在状态共享问题
3. **职责过多**: 违反单一职责原则，承担了 token 管理、API 调用、拦截器处理、存储管理、路由跳转等多重职责
4. **强耦合**: 与浏览器 API 强耦合，难以进行单元测试

这些问题导致代码难以测试、维护和扩展，违反了软件设计的 SOLID 原则。

## 目标

1. **实现职责分离**: 将 AuthService 分解为多个专职服务类
2. **引入依赖注入**: 通过依赖注入降低模块间耦合
3. **提高可测试性**: 使所有组件都可以轻松进行单元测试
4. **保持向后兼容**: 确保现有 API 接口不变，避免影响现有代码
5. **改善代码质量**: 遵循 SOLID 原则，提高代码可维护性

## 相关文件

### 主要文件
- `apps/frontend/src/services/auth.ts` - 当前的 AuthService 实现
- `apps/frontend/src/hooks/useAuth.ts` - 使用 AuthService 的 React Hook
- `apps/frontend/src/hooks/test-utils.ts` - 测试工具文件

### 预期新增文件
- `apps/frontend/src/services/auth/` - 新的认证服务模块目录
- `apps/frontend/src/services/auth/types.ts` - 接口定义
- `apps/frontend/src/services/auth/token-manager.ts` - Token 管理服务
- `apps/frontend/src/services/auth/storage.ts` - 存储服务抽象
- `apps/frontend/src/services/auth/navigation.ts` - 导航服务抽象
- `apps/frontend/src/services/auth/http-client.ts` - HTTP 客户端抽象
- `apps/frontend/src/services/auth/auth-service.ts` - 重构后的主服务类
- `apps/frontend/src/services/auth/factory.ts` - 服务工厂函数

### 相关测试文件
- `apps/frontend/src/services/auth/__tests__/` - 新的测试目录
- 现有测试文件的更新

## 成功标准

1. **架构改进**: AuthService 类职责单一，依赖关系清晰
2. **测试覆盖**: 所有新模块都有完整的单元测试
3. **向后兼容**: 现有 useAuth Hook 和相关代码无需修改
4. **代码质量**: 通过所有 ESLint 和 TypeScript 检查
5. **性能保持**: 重构后性能不下降

## 参考资料

- [SOLID 原则](https://en.wikipedia.org/wiki/SOLID)
- [依赖注入模式](https://en.wikipedia.org/wiki/Dependency_injection)
- [单一职责原则](https://en.wikipedia.org/wiki/Single-responsibility_principle)
- [测试驱动开发最佳实践](https://en.wikipedia.org/wiki/Test-driven_development)