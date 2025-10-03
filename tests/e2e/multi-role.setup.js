import { test as setup } from '@playwright/test';

// Setup for admin user
setup('authenticate as admin', async ({ page }) => {
  await page.goto('/login');
  
  // Wait for Vue app to load
  await page.waitForLoadState('networkidle');
  await page.waitForSelector('input[type="text"]', { state: 'visible', timeout: 15000 });
  
  await page.fill('input[type="text"]', 'admin');
  await page.fill('input[type="password"]', 'admin123456789');
  
  // Use correct button selector - it's not a submit button
  await page.click('button:has-text("Login")');
  
  // Wait for successful authentication
  await page.waitForURL(url => !url.toString().includes('/login'), { timeout: 15000 });
  
  await page.context().storageState({ 
    path: 'test-results/.auth/admin.json' 
  });
});

// Setup for regular user
setup.skip('authenticate as user', async ({ page }) => {
  // TODO: Set up proper test user credentials
  await page.goto('/login');
  
  // Wait for Vue app to load
  await page.waitForLoadState('networkidle');
  await page.waitForSelector('input[type="text"]', { state: 'visible', timeout: 15000 });
  
  await page.fill('input[type="text"]', 'testuser');
  await page.fill('input[type="password"]', 'admin123456789');
  
  // Use correct button selector - it's not a submit button
  await page.click('button:has-text("Login")');
  
  // Wait for successful authentication
  await page.waitForURL(url => !url.toString().includes('/login'), { timeout: 15000 });
  
  await page.context().storageState({ 
    path: 'test-results/.auth/user.json' 
  });
});

// Setup for guest/unauthenticated
setup('no authentication', async ({ page }) => {
  // Navigate to a page to establish context, then save empty state
  await page.goto('/login');
  await page.waitForLoadState('networkidle');
  
  await page.context().storageState({ 
    path: 'test-results/.auth/guest.json' 
  });
});