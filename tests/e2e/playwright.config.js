import { defineConfig, devices } from '@playwright/test';

/**
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: '.',
  
  // Run tests in files in parallel, but run tests within a file sequentially
  fullyParallel: false,
  
  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,
  
  // Retry on CI only
  retries: process.env.CI ? 2 : 0,
  
  // Single worker for database consistency
  workers: 1,
  
  // Test timeout
  timeout: 30 * 1000,
  expect: {
    // Timeout for assertions
    timeout: 10 * 1000,
  },
  
  // Reporter configuration
  reporter: [
    // HTML reporter for detailed results
    ['html', { outputFolder: 'test-results/html-report' }],
    // Line reporter for CI/console output
    ['line'],
    // JSON reporter for further processing
    ['json', { outputFile: 'test-results/results.json' }],
  ],
  
  // Global test configuration
  use: {
    // Base URL for the admin frontend
    baseURL: 'http://localhost:3000',
    
    // Browser settings
    headless: !process.env.DEBUG,
    viewport: { width: 1280, height: 720 },
    
    // Collect trace when retrying the failed test
    trace: 'on-first-retry',
    
    // Record video on failure
    video: 'retain-on-failure',
    
    // Take screenshot on failure
    screenshot: 'only-on-failure',
    
    // Ignore HTTPS errors (for local development)
    ignoreHTTPSErrors: true,
    
    // Global timeout for actions
    actionTimeout: 15 * 1000,
    navigationTimeout: 30 * 1000,
  },

  // Global setup and teardown
  globalSetup: './global-setup.js',
  globalTeardown: './global-teardown.js',
  
  // Projects configuration for different browser testing
  projects: [
    // Setup project for authentication state
    {
      name: 'setup',
      testMatch: /.*\.setup\.js/,
    },
    
    // Main desktop tests with Chrome
    {
      name: 'desktop-chrome',
      use: { 
        ...devices['Desktop Chrome'],
        // Use saved authentication state
        storageState: 'test-results/.auth/admin.json',
      },
      dependencies: ['setup'],
    },
    
    // Mobile testing (optional)
    {
      name: 'mobile-safari',
      use: { 
        ...devices['iPhone 12'],
        storageState: 'test-results/.auth/admin.json',
      },
      dependencies: ['setup'],
      // Only run on CI or when specifically requested
      grep: process.env.MOBILE_TESTS ? /.*/ : /never-match/,
    },
    
    // Performance testing project
    {
      name: 'performance',
      testMatch: /.*performance\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'test-results/.auth/admin.json',
        // Performance-specific settings
        video: 'off',
        screenshot: 'off',
      },
      dependencies: ['setup'],
    },
  ],

  // Output directory
  outputDir: 'test-results/artifacts',
  
  // Web server configuration
  webServer: [
    {
      command: 'npm run admin:backend',
      port: 8000,
      reuseExistingServer: !process.env.CI,
      timeout: 120 * 1000,
      env: {
        NODE_ENV: 'test',
        ADMIN_DEFAULT_USERNAME: 'admin',
        ADMIN_DEFAULT_PASSWORD: 'admin123456789',
      },
    },
    {
      command: 'npm run admin:frontend',
      port: 3000,
      reuseExistingServer: !process.env.CI,
      timeout: 120 * 1000,
      env: {
        NODE_ENV: 'test',
        VITE_API_BASE_URL: 'http://localhost:8000/admin',
      },
    },
  ],
});