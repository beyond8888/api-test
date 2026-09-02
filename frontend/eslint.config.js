import antfu from '@antfu/eslint-config'

const base = antfu({
  vue: true,
  typescript: true,
  // Disable almost all style/formatting rules so linting focuses on real
  // quality issues while the existing project is incrementally cleaned up.
  rules: {
    'no-console': 'off',
    'node/prefer-global/process': 'off',
    'ts/no-empty-object-type': 'off',
    'vue/component-name-in-template-casing': 'off',
    'vue/custom-event-name-casing': 'off',
    'vue/singleline-html-element-content-newline': 'off',
    'vue/html-self-closing': 'off',
    'vue/html-closing-bracket-spacing': 'off',
    'vue/html-closing-bracket-newline': 'off',
    'vue/html-indent': 'off',
    'vue/first-attribute-linebreak': 'off',
    'vue/attributes-order': 'off',
    'vue/block-order': 'off',
    'vue/quote-props': 'off',
    'perfectionist/sort-imports': 'off',
    'perfectionist/sort-object-keys': 'off',
    'perfectionist/sort-named-imports': 'off',
    'jsonc/sort-keys': 'off',
    'style/no-multi-spaces': 'off',
    'style/arrow-parens': 'off',
    'style/brace-style': 'off',
    'style/member-delimiter-style': 'off',
    'style/eol-last': 'off',
    'style/quote-props': 'off',
    'style/comma-dangle': 'off',
    'style/max-statements-per-line': 'off',
    'style/indent': 'off',
    'style/semi': 'off',
    'antfu/if-newline': 'off',
    'antfu/consistent-list-newline': 'off',
    'antfu/top-level-function': 'off',
    'unicorn/escape-case': 'off',
    'regexp/use-ignore-case': 'off',
    'import/newline-after-import': 'off',
    'import/consistent-type-specifier-style': 'off',
    // Script engine intentionally uses `new Function(...)` as a sandbox.
    'no-new-func': 'off',
    // Vue <script setup> hoists declarations; this rule produces false
    // positives for code written in the natural top-down narrative order.
    'ts/no-use-before-define': 'off',
  },
})

export default base.append({
  // Project has 300+ explicit-any usages; tackle them in a dedicated typing
  // pass. For now linting should focus on real bugs, not typing debt.
  rules: {
    'ts/no-explicit-any': 'off',
  },
})
