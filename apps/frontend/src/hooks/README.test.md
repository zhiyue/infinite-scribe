# TanStack Query 测试总结

## 测试覆盖范围

本测试套件为 TanStack Query 服务端状态管理实现提供了全面的单元测试覆盖。

### 测试文件

1. **useAuthQuery.test.ts** - 查询 hooks 的测试
   - 12 个测试用例
   - 覆盖了 `useCurrentUser`、`usePermissions`、`useSessions` 的所有场景

2. **useAuthMutations.test.ts** - 变更 hooks 的测试
   - 12 个测试用例
   - 覆盖了 `useLogin`、`useLogout`、`useUpdateProfile`、`useRefreshToken` 的所有场景
   - 包含集成测试

3. **queryClient.test.ts** - 查询客户端配置的测试
   - 15 个测试用例
   - 覆盖了配置、查询键管理、错误处理等

4. **errorHandler.test.ts** - 错误处理工具的测试
   - 32 个测试用例
   - 覆盖了 `AppError` 类、错误解析、网络错误处理、日志记录和用户友好消息等

### 测试场景覆盖

#### 查询测试 (useAuthQuery)
- ✅ 未认证时不执行查询
- ✅ 认证后正确获取数据
- ✅ 401 错误不重试
- ✅ 其他错误正确重试
- ✅ 数据缓存机制
- ✅ 依赖查询（权限依赖用户角色）
- ✅ 接口不存在时的降级处理
- ✅ 自动刷新机制

#### 变更测试 (useAuthMutations)
- ✅ 登录成功处理
- ✅ 登录失败处理
- ✅ 权限预取逻辑
- ✅ 登出流程（包括错误情况）
- ✅ 乐观更新机制
- ✅ 错误回滚
- ✅ Token 刷新
- ✅ 完整的登录-更新-登出流程集成测试

#### 配置测试 (queryClient)
- ✅ 查询重试逻辑
- ✅ 窗口聚焦行为
- ✅ staleTime 和 gcTime 配置
- ✅ Mutation 错误处理
- ✅ 401 错误自动清理缓存
- ✅ 查询键生成和管理
- ✅ 不同资源的特定配置

#### 错误处理测试 (errorHandler)
- ✅ AppError 类的创建和使用
- ✅ HTTP 状态码到错误码的映射
- ✅ API 响应错误解析
- ✅ 网络错误处理（中止、超时、连接失败）
- ✅ 错误日志记录
- ✅ 用户友好消息生成
- ✅ 错误处理集成场景

### 测试质量保证

1. **Mock 隔离** - 所有外部依赖都被正确 mock
2. **异步处理** - 使用 `waitFor` 和 `act` 正确处理异步操作
3. **错误场景** - 覆盖了各种错误情况
4. **边界条件** - 测试了空数据、接口不存在等边界情况
5. **并发安全** - 测试了查询取消和缓存更新

### 运行测试

```bash
# 运行所有测试
pnpm test

# 运行特定测试文件
pnpm test src/hooks/useAuthQuery.test.ts
pnpm test src/hooks/useAuthMutations.test.ts
pnpm test src/lib/queryClient.test.ts

# 运行测试并查看详细输出
pnpm test -- --reporter=verbose

# 监听模式
pnpm test -- --watch
```

### 测试结果

✅ **总计**: 71 个测试全部通过
- queryClient.test.ts: 15/15 ✅
- useAuthMutations.test.ts: 12/12 ✅
- useAuthQuery.test.ts: 12/12 ✅
- errorHandler.test.ts: 32/32 ✅

### 注意事项

1. 有一个警告信息关于 undefined query data，这是测试错误重试时的预期行为
2. 某些测试可能需要更长的超时时间，已经为相关测试配置了 10 秒超时
3. 测试使用 vitest 框架，配置在 `vitest.config.ts` 中

### 未来改进建议

1. 添加覆盖率报告（需要安装 `@vitest/coverage-v8`）
2. 添加 E2E 测试验证完整的用户流程
3. 添加性能测试验证缓存效率
4. 考虑添加并发测试场景