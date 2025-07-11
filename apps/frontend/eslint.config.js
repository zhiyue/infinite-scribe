import { default as eslint, default as js } from '@eslint/js'
import prettierConfig from 'eslint-config-prettier/flat'
import prettierPluginRecommended from 'eslint-plugin-prettier/recommended'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import { globalIgnores } from 'eslint/config'
import globals from 'globals'
import tseslint from 'typescript-eslint'

/* -------------------------- ① 忽略规则 -------------------------- */
const ignoreBlock = {
  ignores: [
    // 依赖
    'node_modules/**',
    '.pnp',
    '.pnp.js',

    // 构建产物
    'dist/**',
    'build/**',
    'out/**',
    '.next/**',
    '.nuxt/**',
    '*.tsbuildinfo',

    // 测试覆盖率
    'coverage/**',
    '.nyc_output/**',

    // 缓存
    '.cache/**',
    '.temp/**',
    '.tmp/**',
    '.turbo/**',

    // IDE
    '.vscode/**',
    '.idea/**',

    // OS
    '.DS_Store',
    'Thumbs.db',

    // 环境 & 日志
    '.env',
    '.env.*',
    '*.log',

    // Python
    '__pycache__/**',
    '*.py[cod]',
    '.pytest_cache/**',
    '.mypy_cache/**',

    // 通用配置文件
    '*.config.js',
    '*.config.ts',
    '!eslint.config.js', // 反向排除：仍检查本文件
    '!.prettierrc.js',

    // 版本控制 & 钩子
    '.git/**',
    '.husky/**',

    // 基础设施、脚本
    'infrastructure/**',
    'scripts/*.js',

    // e2e 测试目录
    'e2e/**',
    '.prettierrc.cjs',
    // 忽略 shadcn 组件
    'src/components/ui',
  ],
}

/* ------------------------ ② TS/React 配置 ------------------------ */
const customTsConfig = {
  files: ['**/*.{ts,tsx}'],
  extends: [
    js.configs.recommended,
    tseslint.configs.stylistic,
    tseslint.configs.recommendedTypeChecked,
    reactHooks.configs['recommended-latest'],
    reactRefresh.configs.vite,
  ],
  languageOptions: {
    ecmaVersion: 2020,
    globals: globals.browser,
    parserOptions: {
      project: true,
      projectService: {
        allowDefaultProject: ['vitest.config.ts', 'vite.config.ts'],
      },
      tsconfigRootDir: import.meta.dir,
    },
  },
  rules: {
    indent: ['error', 2],
  },
}

export default tseslint.config(
  ignoreBlock,
  eslint.configs.recommended,
  ...tseslint.configs.recommended,
  globalIgnores(['dist']),
  customTsConfig,
  prettierPluginRecommended,
  prettierConfig,
)
