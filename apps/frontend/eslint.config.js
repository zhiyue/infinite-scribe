import { default as eslint, default as js } from '@eslint/js'
import prettierConfig from 'eslint-config-prettier/flat'
import prettierPluginRecommended from 'eslint-plugin-prettier/recommended'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import { globalIgnores } from 'eslint/config'
import globals from 'globals'
import tseslint from 'typescript-eslint'

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
  eslint.configs.recommended,
  ...tseslint.configs.recommended,
  globalIgnores(['dist']),
  customTsConfig,
  prettierPluginRecommended,
  prettierConfig,
)
