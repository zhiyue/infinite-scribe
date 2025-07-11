# 任务清单

## 待办事项

### 基础设施设置
- [x] ⭐ 创建 queryClient 配置文件 (`src/lib/queryClient.ts`) - **优先级: 高**
- [x] ⭐ 在 App.tsx 中添加 QueryClientProvider - **优先级: 高**
- [x] 配置 React Query DevTools（开发环境） - **优先级: 中**

### 创建核心 Hooks
- [x] ⭐ 创建 useCurrentUser hook - **优先级: 高**
- [x] ⭐ 添加 TypeScript 类型定义 - **优先级: 高**
- [x] 创建 useLogin mutation hook - **优先级: 高**
- [x] 创建 useLogout mutation hook - **优先级: 高**
- [x] 创建 useUpdateProfile mutation hook（含乐观更新） - **优先级: 中**

### 改造认证系统
- [x] ⭐ 修改 useAuth hook，移除 user 状态存储 - **优先级: 高**
- [x] ⭐ 更新 login 方法，添加 queryClient.setQueryData - **优先级: 高**
- [x] ⭐ 更新 logout 方法，添加缓存清理逻辑 - **优先级: 高**
- [x] 实现 handleTokenExpired 方法 - **优先级: 高**
- [x] 处理 token 自动刷新的缓存同步 - **优先级: 中**

### API 服务层适配
- [x] 统一 authService 响应格式 - **优先级: 高**
- [x] 添加全局 401 错误拦截器 - **优先级: 高**
- [x] 配置请求重试策略 - **优先级: 中**
- [x] 实现错误格式化工具函数 - **优先级: 中**

### 组件迁移（按风险顺序）
#### 第一批：低风险组件
- [x] 迁移导航栏用户信息显示 - **优先级: 高**
- [x] 迁移 Profile 页面（只读） - **优先级: 高**
- [x] 迁移 Dashboard 欢迎信息 - **优先级: 中**

#### 第二批：中风险组件
- [x] ⭐ 迁移 RequireAuth 组件 - **优先级: 高**
- [x] 迁移 ChangePassword 页面 - **优先级: 中**

#### 第三批：高风险组件
- [x] 迁移登录页面流程 - **优先级: 高**
- [x] 迁移注册页面流程 - **优先级: 中**
- [x] 迁移 token 刷新逻辑 - **优先级: 高**

### 优化和增强
- [x] 为不同资源配置特定的缓存时间 - **优先级: 中**
- [ ] 实现关键数据的预取（首页加载） - **优先级: 低**
- [ ] 添加离线支持和数据持久化 - **优先级: 低**
- [ ] 实现后台标签页数据同步 - **优先级: 低**

### 测试（目标覆盖率：85%+）
- [ ] ⭐ 编写 useCurrentUser hook 单元测试 - **优先级: 高**
- [ ] 编写 mutation hooks 单元测试 - **优先级: 高**
- [ ] 编写缓存行为的集成测试 - **优先级: 高**
- [ ] 更新现有的认证 E2E 测试 - **优先级: 高**
- [ ] 添加多标签页同步测试 - **优先级: 中**
- [ ] 执行完整的回归测试 - **优先级: 高**

### 文档和清理
- [x] 编写 TanStack Query 使用规范 - **优先级: 中**
- [ ] 更新组件中的代码注释 - **优先级: 低**
- [x] 移除 useAuth 中的废弃代码 - **优先级: 中**
- [x] 创建迁移检查清单 - **优先级: 中**
- [ ] 更新项目 README - **优先级: 低**

## 进行中
- [ ] 更新现有的认证 E2E 测试 - **优先级: 高**

## 已完成
- [x] 根据最佳实践文档更新实现方案
- [x] 在 App.tsx 中添加 QueryClientProvider
- [x] 配置 React Query DevTools（开发环境）
- [x] 创建 queryClient 配置文件（含查询键管理）
- [x] 创建 useAuthQuery.ts（useCurrentUser、usePermissions、useSessions）
- [x] 创建 useAuthMutations.ts（useLogin、useLogout、useUpdateProfile、useRefreshToken）
- [x] 扩展 useAuthMutations.ts 添加所有认证相关 mutations
- [x] 修改 useAuth hook，移除 user 状态存储
- [x] 更新 login 方法，添加 queryClient.setQueryData
- [x] 更新 logout 方法，添加缓存清理逻辑
- [x] 实现 handleTokenExpired 方法
- [x] 处理 token 自动刷新的缓存同步
- [x] 迁移所有组件使用 TanStack Query（Profile、ChangePassword、EmailVerification、Register、ForgotPassword、ResetPassword）
- [x] 统一 authService 响应格式
- [x] 配置智能请求重试策略
- [x] 为不同资源配置特定的缓存时间
- [x] 编写 TanStack Query 使用规范