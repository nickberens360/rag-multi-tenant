import { test as setup, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const authFile = path.join(__dirname, '.auth', 'admin.json');

// Ensure .auth directory exists
const authDir = path.dirname(authFile);
if (!fs.existsSync(authDir)) {
  fs.mkdirSync(authDir, { recursive: true });
}

setup('authenticate as admin', async ({ page }) => {
  console.log('🔐 Setting up admin authentication...');
  
  // Navigate to login page
  await page.goto('/login');
  
  // Wait for Vue app to load and hydrate
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(2000); // Give Vue time to render
  
  // Wait for form fields - target the actual input elements within Vuetify components
  await expect(page.locator('[data-testid="username"] input')).toBeVisible({ timeout: 10000 });
  await expect(page.locator('[data-testid="password"] input')).toBeVisible({ timeout: 10000 });
  
  // Fill in credentials
  const username = process.env.ADMIN_DEFAULT_USERNAME || 'admin';
  const password = process.env.ADMIN_DEFAULT_PASSWORD || 'admin123456789';
  
  console.log(`Logging in as: ${username}`);
  
  // Target the actual input elements within the Vuetify wrapper
  await page.locator('[data-testid="username"] input').fill(username);
  await page.locator('[data-testid="password"] input').fill(password);
  
  // Click login button
  await expect(page.locator('[data-testid="login-button"]')).toBeVisible({ timeout: 10000 });
  
  // Submit form and wait for navigation
  await Promise.all([
    page.waitForURL(url => !url.toString().includes('/login'), { timeout: 15000 }),
    page.locator('[data-testid="login-button"]').click(),
  ]);
  
  // Wait for page to load completely
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(2000);
  
  // Verify we're logged in by checking for admin content
  const hasAdminContent = await page.locator('nav, [data-testid="admin-nav"], .v-navigation-drawer, .v-main, .v-app-bar').count() > 0;
  const isNotOnLogin = !page.url().includes('/login');
  
  if (!hasAdminContent || !isNotOnLogin) {
    // Take screenshot for debugging
    await page.screenshot({ path: 'test-results/login-failure.png', fullPage: true });
    throw new Error(`Login appears to have failed. URL: ${page.url()}, hasAdminContent: ${hasAdminContent}, isNotOnLogin: ${isNotOnLogin}`);
  }
  
  // Save authentication state
  await page.context().storageState({ path: authFile });
  
  console.log(`✅ Admin authentication completed. Saved to: ${authFile}`);
  console.log(`Current URL: ${page.url()}`);
});

setup.describe.configure({ mode: 'serial' });