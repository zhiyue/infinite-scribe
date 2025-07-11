import { default as eslint, default as js } from '@eslint/js'
import vitest from '@vitest/eslint-plugin'
import prettierConfig from 'eslint-config-prettier/flat'
import vitestGlobals from 'eslint-config-vitest-globals/flat'
import jestDom from 'eslint-plugin-jest-dom'
import prettierPluginRecommended from 'eslint-plugin-prettier/recommended'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import testingLibrary from 'eslint-plugin-testing-library'
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
    '*.config.{js,ts,cjs}', // 忽略项目根目录下的配置文件
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
    '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
    '@typescript-eslint/no-explicit-any': 'warn', // 对 'any' 类型发出警告，而不是错误
    'no-console': 'warn', // 提醒移除 console.log
  },
}
/* ------------------------ ③ Vitest 测试文件专属配置------------------------ */
const viteTsConfig = {
  files: ['**/*.{test,spec}.{js,ts,jsx,tsx}'], // **只对测试文件生效**
  plugins: {
    vitest,
    'testing-library': testingLibrary,
    'jest-dom': jestDom,
  },
  languageOptions: {
    globals: {
      ...vitest.environments.env.globals, // 注入 describe, it, expect 等 Vitest 全局变量
    },
  },
  rules: {
    // --- Vitest 推荐规则 ---
    ...vitest.configs.recommended.rules,

    // --- Testing Library 推荐规则 ---
    ...testingLibrary.configs.react.rules,
    ...jestDom.configs.recommended.rules,

    // --- 规则定制 (Overrides) ---
    // 在测试环境中，一些通用规则可能需要放宽
    /* 放宽类型限制 */
    // a. 允许在测试文件中使用 any 类型，因为 mock 时非常常用
    '@typescript-eslint/no-explicit-any': 'off',
    // b. 允许在测试文件中使用非空断言 (`!`)，方便处理测试数据
    '@typescript-eslint/no-non-null-assertion': 'off',
    // c. 允许测试文件中包含未使用的变量，有时为了保持接口一致性需要定义但未使用
    '@typescript-eslint/no-unused-vars': 'off',

    // d. 定制 Vitest 规则：强制测试用例名称以 "should" 开头
    /* Vitest 质量守门 */
    'vitest/no-conditional-tests': 'error',
    'vitest/no-focused-tests': 'error',
    'vitest/consistent-test-it': ['error', { fn: 'it', withinDescribe: 'it' }],
    'vitest/require-top-level-describe': 'error',

    /* Testing Library 细节 */
    // e. 定制 Testing Library 规则
    'testing-library/render-result-naming-convention': 'off', // 关闭对 render 返回结果的命名限制
    'testing-library/prefer-screen-queries': 'warn',
  },
}

export default tseslint.config(
  vitestGlobals(),
  ignoreBlock,
  eslint.configs.recommended,
  ...tseslint.configs.recommended,
  globalIgnores(['dist']),
  customTsConfig,
  viteTsConfig,
  prettierPluginRecommended,
  prettierConfig,
)
