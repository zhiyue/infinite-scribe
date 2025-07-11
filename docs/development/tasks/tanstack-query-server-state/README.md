# 服务端数据同步使用 TanStack Query 管理服务器状态

## 任务背景
当前项目使用 axios + Zustand 管理认证和用户数据，虽然已安装 TanStack Query，但仅在健康检查中使用。这种方案存在以下问题：
- 用户数据可能同时存储在 Zustand 和其他地方，造成数据不一致
- 缺少自动的缓存管理、后台数据同步、乐观更新等高级特性
- 修改用户资料等操作需要手动同步多处数据

## 目标
1. 将所有服务器数据（Server State）统一交给 TanStack Query 管理，实现单一数据源（Single Source of Truth）
2. Zustand 只负责会话控制（token、isAuthenticated、login/logout 函数）
3. 避免数据双写问题，防止组件间显示不一致
4. 利用 TanStack Query 的缓存、失效、重新验证、乐观更新等内置能力

## 相关文件
- `/apps/frontend/src/hooks/useAuth.ts` - 当前认证 hook（需要改造）
- `/apps/frontend/src/services/auth.ts` - 认证服务
- `/apps/frontend/src/services/api.ts` - API 服务基类
- `/apps/frontend/src/App.tsx` - 应用主入口（需要添加 QueryClientProvider）
- `/apps/frontend/src/main.tsx` - React 根组件
- `/apps/frontend/src/hooks/useHealthCheck.ts` - 现有的 TanStack Query 使用示例

## 参考资料
- TanStack Query 文档：https://tanstack.com/query/latest
- Zustand 文档：https://github.com/pmndrs/zustand
- React Query 数据同步模式：https://tkdodo.eu/blog/react-query-as-a-state-manager