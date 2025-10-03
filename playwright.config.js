import { defineConfig, devices } from '@playwright/test';

/**
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30000,
  expect: {
    timeout: 5000,
  },
  fullyParallel: false, // Sequential for database consistency
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1, // Single worker to avoid database conflicts
  reporter: [
    ['html'],
    ['json', { outputFile: 'test-results/results.json' }],
    ['junit', { outputFile: 'test-results/junit.xml' }],
  ],
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 10000,
    navigationTimeout: 15000,
    // Pass environment variables to tests
    extraHTTPHeaders: {
      'Accept': 'application/json',
    },
  },

  projects: [
    // Setup project to handle authentication
    {
      name: 'setup',
      testMatch: /.*\.setup\.js/,
      use: {
        ...devices['Desktop Chrome'],
      },
    },

    // Unauthenticated tests (login/auth flows)
    {
      name: 'unauthenticated',
      use: {
        ...devices['Desktop Chrome'],
        // No storageState - starts fresh without authentication
      },
      testMatch: /.*auth-flow.*\.spec\.js|.*auth-specific.*\.spec\.js|.*auth\.spec\.js/,
    },

    // Main e2e test project with authenticated state
    {
      name: 'admin-e2e',
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'tests/e2e/.auth/admin.json',
      },
      dependencies: ['setup'],
      testIgnore: /.*auth-flow.*\.spec\.js|.*auth-specific.*\.spec\.js|.*auth\.spec\.js/, // Exclude auth tests
    },

    // Mobile testing
    {
      name: 'mobile-admin',
      use: {
        ...devices['iPhone 13'],
        storageState: 'tests/e2e/.auth/admin.json',
      },
      dependencies: ['setup'],
      testMatch: /.*mobile.*\.spec\.js/,
    },

    // Performance testing
    {
      name: 'performance',
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'tests/e2e/.auth/admin.json',
      },
      dependencies: ['setup'],
      testMatch: /.*performance.*\.spec\.js/,
    },
  ],

  // Global test setup/teardown
  globalSetup: './tests/e2e/global-setup.js',
  globalTeardown: './tests/e2e/global-teardown.js',

  webServer: [
    {
      command: 'ENVIRONMENT=testing npm run admin:backend',
      port: 8000,
      reuseExistingServer: !process.env.CI,
      env: {
        ...process.env,
        ENVIRONMENT: 'testing',
        ALLOW_DB_RESET: 'true',
      },
    },
    {
      command: 'npm run admin:frontend',
      port: 3000,
      reuseExistingServer: !process.env.CI,
    },
  ],
});