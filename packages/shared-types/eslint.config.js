export default [
  {
    files: ['src/**/*.ts', 'src/**/*.tsx'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
    },
    rules: {
      // 基础规则，暂时宽松设置，专注于语法检查
      'no-unused-vars': 'off', // TypeScript 会检查这个
      'no-console': 'warn',
    },
    ignores: ['dist/**', 'node_modules/**'],
  },
];