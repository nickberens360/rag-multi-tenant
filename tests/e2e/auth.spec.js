import { test, expect } from '@playwright/test';
import LoginPage from './pages/LoginPage.js';
import AdminLayoutPage from './pages/AdminLayoutPage.js';

// Use setup project for authentication state
test.use({ storageState: { cookies: [], origins: [] } }); // Clear auth for these tests

test.describe('Admin Authentication Flow', () => {
  let loginPage;
  let adminLayoutPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    adminLayoutPage = new AdminLayoutPage(page);
    await loginPage.goto();
  });

  test('successful login with valid credentials', async ({ page }) => {
    const username = process.env.ADMIN_DEFAULT_USERNAME || 'admin';
    const password = process.env.ADMIN_DEFAULT_PASSWORD || 'admin123456789';
    
    const result = await loginPage.login(username, password);
    
    expect(result.success).toBe(true);
    expect(await loginPage.isLoggedIn()).toBe(true);
    
    // Verify redirect to admin area (URL should not contain /login)
    await page.waitForURL(url => !url.toString().includes('/login'), { timeout: 10000 });
    
    // Verify admin layout loads
    await adminLayoutPage.waitForLoad();
    expect(await adminLayoutPage.isAuthenticated()).toBe(true);
  });

  test('failed login with invalid credentials', async ({ page }) => {
    const result = await loginPage.login('invalid_user', 'invalid_password');
    
    expect(result.success).toBe(false);
    expect(result.error).toContain('Invalid');
    expect(await loginPage.isLoggedIn()).toBe(false);
    
    // Should remain on login page
    expect(page.url()).toContain('/login');
  });

  test('failed login with empty credentials', async ({ page }) => {
    const result = await loginPage.login('', '');
    
    expect(result.success).toBe(false);
    expect(await loginPage.isLoggedIn()).toBe(false);
  });

  test('session persistence across page reload', async ({ page }) => {
    const username = process.env.ADMIN_DEFAULT_USERNAME || 'admin';
    const password = process.env.ADMIN_DEFAULT_PASSWORD || 'admin123456789';
    
    // Login successfully
    await loginPage.login(username, password);
    expect(await loginPage.isLoggedIn()).toBe(true);
    
    // Reload page and verify session persists
    await page.reload();
    await adminLayoutPage.waitForLoad();
    expect(await adminLayoutPage.isAuthenticated()).toBe(true);
  });

  test('logout functionality', async ({ page }) => {
    const username = process.env.ADMIN_DEFAULT_USERNAME || 'admin';
    const password = process.env.ADMIN_DEFAULT_PASSWORD || 'admin123456789';
    
    // Login first
    await loginPage.login(username, password);
    
    // Wait for dashboard to load and verify we're logged in
    await page.waitForURL(url => !url.toString().includes('/login'), { timeout: 15000 });
    await expect(page.locator('.v-navigation-drawer')).toBeVisible({ timeout: 5000 });
    
    // Logout using the user menu
    await page.locator('.user-profile-section').click();
    await page.waitForTimeout(500);
    await page.getByText('Logout').click();
    
    // Wait for the redirect to login page
    await page.waitForURL('**/login', { timeout: 5000 });
    
    // Verify we're on login page and not authenticated
    expect(page.url()).toContain('/login');
    expect(await loginPage.isLoggedIn()).toBe(false);
  });

  test('protected route access without authentication', async ({ page }) => {
    // Try to access protected route directly
    await page.goto('/settings/followup', { waitUntil: 'domcontentloaded' });
    
    // Should be redirected to login
    await expect(page).toHaveURL(/.*login/, { timeout: 10000 });
  });

  test('authentication with remember redirect', async ({ page }) => {
    const username = process.env.ADMIN_DEFAULT_USERNAME || 'admin';
    const password = process.env.ADMIN_DEFAULT_PASSWORD || 'admin123456789';
    
    // Try to access specific page while unauthenticated
    await page.goto('/settings/followup', { waitUntil: 'domcontentloaded' });
    
    // Should redirect to login
    await expect(page).toHaveURL(/.*login/, { timeout: 10000 });
    
    // Now login
    await loginPage.login(username, password);
    
    // Should be redirected to dashboard or settings (both are valid)
    await page.waitForURL(url => !url.toString().includes('/login'), { timeout: 15000 });
    const currentUrl = page.url();
    expect(currentUrl.includes('/settings') || currentUrl.endsWith('/') || currentUrl.includes('/dashboard')).toBeTruthy();
  });

  test.skip('visual regression - login page', async ({ page }) => {
    // Skip visual regression for now as it requires baseline screenshots
    // Wait for page to be fully loaded
    await page.waitForSelector('[data-testid="username"] input', { state: 'visible' });
    await page.waitForTimeout(1000);
    
    // Take a screenshot for visual comparison
    await expect(page).toHaveScreenshot('login-page.png', { maxDiffPixels: 100 });
  });

  test('performance - login response time', async ({ page }) => {
    const username = process.env.ADMIN_DEFAULT_USERNAME || 'admin';
    const password = process.env.ADMIN_DEFAULT_PASSWORD || 'admin123456789';
    
    const startTime = Date.now();
    
    const result = await loginPage.login(username, password);
    
    const loginTime = Date.now() - startTime;
    
    // Check if login was successful and completed within reasonable time
    expect(result.success).toBe(true);
    expect(loginTime).toBeLessThan(10000); // Should complete within 10 seconds
  });
});