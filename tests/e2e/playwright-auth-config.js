import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  projects: [
    // Setup projects
    { name: 'setup-admin', testMatch: /.*\.setup\.js/ },
    { name: 'setup-user', testMatch: /user\.setup\.js/ },
    
    // Admin tests
    {
      name: 'admin-tests',
      use: { 
        ...devices['Desktop Chrome'],
        storageState: 'test-results/.auth/admin.json'
      },
      dependencies: ['setup-admin'],
      testMatch: /admin.*\.spec\.js/
    },
    
    // User tests  
    {
      name: 'user-tests',
      use: { 
        ...devices['Desktop Chrome'],
        storageState: 'test-results/.auth/user.json'
      },
      dependencies: ['setup-user'],
      testMatch: /user.*\.spec\.js/
    },
    
    // Unauthenticated tests
    {
      name: 'guest-tests',
      use: { 
        ...devices['Desktop Chrome'],
        storageState: { cookies: [], origins: [] }
      },
      testMatch: /guest.*\.spec\.js|auth.*\.spec\.js/
    },
    
    // Tests that need fresh login each time
    {
      name: 'fresh-auth-tests',
      use: { 
        ...devices['Desktop Chrome'],
        storageState: { cookies: [], origins: [] }
      },
      testMatch: /login.*\.spec\.js|logout.*\.spec\.js/
    }
  ]
});