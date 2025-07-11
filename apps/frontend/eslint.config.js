import js from '@eslint/js'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import { globalIgnores } from 'eslint/config'
import globals from 'globals'
import tseslint from 'typescript-eslint'

export default tseslint.config([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      // tseslint.configs.recommended,
      tseslint.configs.stylistic,
      tseslint.configs.recommended-type-checked,
      reactHooks.configs['recommended-latest'],
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
      projectService: true,
      tsconfigRootDir: import.meta.dir,
    },
    rules: {
      // 设置 indent 规则：2 个空格缩进
      "indent": ["error", 2],
      // 可选：并规定 switch-case 缩进级别
      "indent": ["error", 2, { "SwitchCase": 1 }],
    },
  },
])
