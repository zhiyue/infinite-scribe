/**
 * 路由配置
 * 集中管理所有路由路径和导航相关配置
 */

/**
 * 应用路由路径配置
 */
export const ROUTES = {
  // 认证相关路由
  auth: {
    login: '/login',
    register: '/register',
    forgotPassword: '/forgot-password',
    resetPassword: '/reset-password',
    changePassword: '/change-password',
    verifyEmail: '/verify-email',
  },

  // 主要功能路由
  dashboard: '/dashboard',
  profile: '/profile',

  // 小说相关路由
  novels: {
    list: '/novels',
    create: '/create-novel',
    detail: (id: string) => `/novels/${id}`,
    genesis: (id: string) => `/novels/${id}/genesis`,
    settings: (id: string) => `/novels/${id}/settings`,
    chapters: (id: string) => `/novels/${id}/chapters`,
    characters: (id: string) => `/novels/${id}/characters`,
    worldview: (id: string) => `/novels/${id}/worldview`,
    outline: (id: string) => `/novels/${id}/outline`,
  },

  // 其他路由
  help: '/help',
  root: '/',

  // 测试路由（仅开发环境）
  test: {
    msw: '/test-msw',
    sse: '/debug/sse',
  },
} as const

/**
 * 导航菜单配置
 */
export const NAV_ITEMS = {
  novel: [
    {
      name: '创世设定',
      path: 'genesis',
      icon: 'Sparkles',
    },
    {
      name: '章节管理',
      path: 'chapters',
      icon: 'Book',
    },
    {
      name: '角色设定',
      path: 'characters',
      icon: 'Users',
    },
    {
      name: '世界观',
      path: 'worldview',
      icon: 'Globe',
    },
    {
      name: '大纲',
      path: 'outline',
      icon: 'FileText',
    },
    {
      name: '设置',
      path: 'settings',
      icon: 'Settings',
    },
  ],
} as const

/**
 * 页面元信息配置
 */
export const PAGE_META = {
  titles: {
    login: '登录 - InfiniteScribe',
    register: '注册 - InfiniteScribe',
    dashboard: '控制台 - InfiniteScribe',
    profile: '个人资料 - InfiniteScribe',
    novels: '我的小说 - InfiniteScribe',
    createNovel: '创建小说 - InfiniteScribe',
    novelDetail: (title: string) => `${title} - InfiniteScribe`,
  },
  descriptions: {
    login: 'AI驱动的智能写作平台',
    register: '加入InfiniteScribe，开启智能创作之旅',
    dashboard: '管理您的小说和创作项目',
    novels: '浏览和管理您的所有小说作品',
  },
} as const

/**
 * 重定向配置
 */
export const REDIRECTS = {
  afterLogin: ROUTES.dashboard,
  afterLogout: ROUTES.auth.login,
  afterRegister: ROUTES.auth.login,
  afterEmailVerification: ROUTES.auth.login,
  afterPasswordReset: ROUTES.auth.login,
  default: ROUTES.dashboard,
} as const

/**
 * 路由权限配置
 */
export const ROUTE_ACCESS = {
  public: [
    ROUTES.auth.login,
    ROUTES.auth.register,
    ROUTES.auth.forgotPassword,
    ROUTES.auth.resetPassword,
    ROUTES.auth.verifyEmail,
  ],
  protected: [
    ROUTES.dashboard,
    ROUTES.profile,
    ROUTES.auth.changePassword,
    ROUTES.novels.list,
    ROUTES.novels.create,
  ],
} as const

/**
 * 路由参数名称
 */
export const ROUTE_PARAMS = {
  novelId: ':id',
  chapterId: ':chapterId',
  characterId: ':characterId',
  sessionId: ':sessionId',
} as const

/**
 * 获取小说详情路由的所有子路由
 */
export function getNovelSubRoutes(id: string) {
  return {
    genesis: ROUTES.novels.genesis(id),
    settings: ROUTES.novels.settings(id),
    chapters: ROUTES.novels.chapters(id),
    characters: ROUTES.novels.characters(id),
    worldview: ROUTES.novels.worldview(id),
    outline: ROUTES.novels.outline(id),
  }
}

/**
 * 判断路由是否需要认证
 */
export function isProtectedRoute(path: string): boolean {
  return !ROUTE_ACCESS.public.includes(path)
}

/**
 * 获取面包屑导航数据
 */
export function getBreadcrumbs(pathname: string): { label: string; path: string }[] {
  const segments = pathname.split('/').filter(Boolean)
  const breadcrumbs: { label: string; path: string }[] = [{ label: '首页', path: '/' }]

  if (segments[0] === 'novels') {
    breadcrumbs.push({ label: '我的小说', path: '/novels' })

    if (segments[1]) {
      // 这里应该从API获取小说标题
      breadcrumbs.push({ label: '小说详情', path: `/novels/${segments[1]}` })

      if (segments[2]) {
        const subRoute = NAV_ITEMS.novel.find((item) => item.path === segments[2])
        if (subRoute) {
          breadcrumbs.push({
            label: subRoute.name,
            path: `/novels/${segments[1]}/${segments[2]}`,
          })
        }
      }
    }
  }

  return breadcrumbs
}

export default ROUTES
