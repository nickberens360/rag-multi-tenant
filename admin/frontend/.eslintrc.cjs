module.exports = {
  root: true,
  env: {
    node: true,
    browser: true,
    es2022: true
  },
  extends: [
    'eslint:recommended',
    '@vue/eslint-config-typescript',
    'plugin:vue/vue3-essential',
    'plugin:vue/vue3-strongly-recommended',
    'plugin:vue/vue3-recommended'
  ],
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module'
  },
  rules: {
    // Code style
    'no-console': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
    'no-debugger': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
    'no-unused-vars': 'warn',
    'prefer-const': 'warn',
    'no-var': 'error',
    
    // Vue specific
    'vue/multi-word-component-names': 'off',
    'vue/no-unused-vars': 'warn',
    'vue/script-setup-uses-vars': 'error',
    'vue/no-setup-props-destructure': 'off',
    
    // Import/export
    'no-duplicate-imports': 'error',
    
    // Best practices
    'eqeqeq': 'warn',
    'no-implicit-coercion': 'warn',
    'prefer-template': 'warn',
    
    // Formatting (handled by Prettier if used)
    'indent': 'off',
    'quotes': 'off',
    'semi': 'off'
  },
  overrides: [
    {
      files: ['*.ts', '*.tsx'],
      rules: {
        '@typescript-eslint/no-unused-vars': 'warn',
        '@typescript-eslint/explicit-function-return-type': 'off',
        '@typescript-eslint/explicit-module-boundary-types': 'off'
      }
    }
  ]
}