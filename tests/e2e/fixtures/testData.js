/**
 * Test data fixtures for followup question management e2e tests
 */

const testCategories = [
  {
    name: 'test_technical',
    displayName: 'Test Technical',
    description: 'Technical questions for testing',
    icon: 'code',
    sortOrder: 1,
    questions: [
      'What programming languages do you use?',
      'How do you approach system architecture?',
      'What development tools do you prefer?',
    ]
  },
  {
    name: 'test_personal',
    displayName: 'Test Personal',
    description: 'Personal questions for testing',
    icon: 'account',
    sortOrder: 2,
    questions: [
      'What is your background?',
      'How can I contact you?',
      'What are your interests?',
    ]
  },
  {
    name: 'test_creative',
    displayName: 'Test Creative',
    description: 'Creative questions for testing',
    icon: 'palette',
    sortOrder: 3,
    questions: [
      'Can you show me your artwork?',
      'What design tools do you use?',
    ]
  }
];

const testSettings = {
  enabled: true,
  serviceType: 'static',
  maxQuestions: 3,
};

const testUsers = {
  admin: {
    username: process.env.ADMIN_DEFAULT_USERNAME || 'admin',
    password: process.env.ADMIN_DEFAULT_PASSWORD || 'admin123456789',
    role: 'admin'
  },
  testUser: {
    username: process.env.ADMIN_TEST_USERNAME || 'test_user',
    password: process.env.ADMIN_TEST_PASSWORD || 'StrongTest4$',
    role: 'viewer'
  }
};

// Test data for different scenarios
const scenarios = {
  // Basic CRUD operations
  basicCategory: {
    name: 'test_basic',
    displayName: 'Basic Test Category',
    description: 'A basic category for testing CRUD operations',
    icon: 'help-circle',
    sortOrder: 10
  },

  // Category with questions
  categoryWithQuestions: {
    ...testCategories[0],
    questions: [
      'Test question 1',
      'Test question 2',
      'Test question 3'
    ]
  },

  // Invalid data for validation testing
  invalidCategory: {
    name: '', // Empty name should fail
    displayName: 'Invalid Category',
    description: 'This should fail validation',
  },

  // Edge cases
  edgeCase: {
    name: 'test_' + 'x'.repeat(100), // Very long name
    displayName: 'Edge Case Category',
    description: 'Testing edge cases',
    icon: 'test',
  },

  // Bulk operations
  bulkCategories: [
    {
      name: 'bulk_test_1',
      displayName: 'Bulk Test 1',
      description: 'First bulk test category',
    },
    {
      name: 'bulk_test_2',
      displayName: 'Bulk Test 2', 
      description: 'Second bulk test category',
    },
    {
      name: 'bulk_test_3',
      displayName: 'Bulk Test 3',
      description: 'Third bulk test category',
    }
  ]
};

// Performance test data
const performanceData = {
  largeCategory: {
    name: 'performance_test',
    displayName: 'Performance Test Category',
    description: 'Category with many questions for performance testing',
    questions: Array.from({ length: 50 }, (_, i) => `Performance test question ${i + 1}`)
  },

  manyCategories: Array.from({ length: 20 }, (_, i) => ({
    name: `perf_category_${i + 1}`,
    displayName: `Performance Category ${i + 1}`,
    description: `Performance test category number ${i + 1}`,
    questions: Array.from({ length: 5 }, (_, j) => `Question ${j + 1} for category ${i + 1}`)
  }))
};

// API endpoints for testing
const apiEndpoints = {
  base: 'http://localhost:8000/admin',
  auth: {
    login: '/auth/login',
    logout: '/auth/logout',
    me: '/auth/me'
  },
  settings: {
    followup: '/settings/followup',
    reset: '/settings/followup/reset'
  },
  categories: {
    list: '/settings/followup/categories',
    create: '/settings/followup/categories',
    update: (id) => `/settings/followup/categories/${id}`,
    delete: (id) => `/settings/followup/categories/${id}/delete`,
    stats: (id) => `/settings/followup/categories/${id}/stats`
  },
  questions: {
    list: '/settings/followup/questions',
    create: '/settings/followup/questions',
    update: (id) => `/settings/followup/questions/${id}`,
    delete: (id) => `/settings/followup/questions/${id}`,
    bulk: '/settings/followup/questions/bulk'
  }
};

// Selectors for consistent element targeting
const selectors = {
  // General UI elements
  loading: '.v-progress-circular, [data-testid="loading"]',
  dialog: '.v-dialog:visible',
  toast: '.v-snackbar, .v-alert, .toast',
  
  // Forms
  textInput: 'input[type="text"]',
  textarea: 'textarea',
  select: '.v-select',
  checkbox: '.v-checkbox input',
  switch: '.v-switch input',
  slider: '.v-slider input',
  
  // Buttons
  button: '.v-btn',
  primaryButton: '.v-btn--color-primary',
  dangerButton: '.v-btn--color-error',
  
  // Cards and lists
  card: '.v-card',
  listItem: '.v-list-item',
  accordion: '.v-expansion-panels',
  accordionPanel: '.v-expansion-panel',
  
  // Navigation
  nav: '.v-navigation-drawer',
  appBar: '.v-app-bar',
  breadcrumbs: '.v-breadcrumbs',
  
  // Followup specific
  followup: {
    metricsCard: '.metric-card',
    settingsCard: '.settings-card',
    categoriesCard: '.categories-card',
    bulkActionsCard: '.bulk-actions-card',
    emptyState: '.empty-state',
    categoryAccordion: '[data-testid="category-accordion"]',
    questionList: '.v-list',
  }
};

export {
  testCategories,
  testSettings,
  testUsers,
  scenarios,
  performanceData,
  apiEndpoints,
  selectors
};