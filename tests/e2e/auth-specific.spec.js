import { test, expect } from '@playwright/test';

test.describe('Authentication Flows', () => {
  
  // Use fresh context without saved auth state
  test.use({ storageState: { cookies: [], origins: [] } });
  
  test('login with valid credentials', async ({ page }) => {
    await page.goto('/login');
    
    // Verify login page loads
    await expect(page.locator('[data-testid="username"] input')).toBeVisible();
    await expect(page.locator('[data-testid="password"] input')).toBeVisible();
    
    await page.locator('[data-testid="username"] input').fill('admin');
    await page.locator('[data-testid="password"] input').fill('admin123456789');
    
    // Wait for button to be enabled and click
    await expect(page.locator('[data-testid="login-button"]')).toBeEnabled();
    await page.click('[data-testid="login-button"]');
    
    // Wait for redirect after successful login
    await page.waitForURL(url => !url.toString().includes('/login'), { timeout: 15000 });
    
    // Verify we're redirected to admin dashboard (check for admin interface elements)
    await expect(page).toHaveURL(/.*\/admin|.*\//);
    const adminElements = await page.locator('nav, .v-navigation-drawer, .v-app-bar').count();
    expect(adminElements).toBeGreaterThan(0);
  });
  
  test('login with invalid credentials', async ({ page }) => {
    await page.goto('/login');
    
    await page.locator('[data-testid="username"] input').fill('admin');
    await page.locator('[data-testid="password"] input').fill('wrong-password');
    
    // Wait for button to be enabled and click
    await expect(page.locator('[data-testid="login-button"]')).toBeEnabled();
    await page.click('[data-testid="login-button"]');
    
    // Wait for error to appear
    await page.waitForTimeout(2000);
    
    // Verify we're still on login page
    expect(page.url()).toContain('/login');
    
    // Verify error message appears (use the same selector as auth-flow.spec.js)
    const errorAlert = page.locator('.v-alert').filter({ hasText: 'Invalid username or password' });
    await expect(errorAlert).toBeVisible({ timeout: 5000 });
  });
  
  test('logout functionality', async ({ page }) => {
    // First login
    await page.goto('/login');
    await page.locator('[data-testid="username"] input').fill('admin');
    await page.locator('[data-testid="password"] input').fill('admin123456789');
    
    await expect(page.locator('[data-testid="login-button"]')).toBeEnabled();
    await page.click('[data-testid="login-button"]');
    
    // Wait for successful login and dashboard to load
    await page.waitForURL(url => !url.toString().includes('/login'), { timeout: 15000 });
    await page.waitForTimeout(1000); // Wait for page to fully load
    
    // Click on the user profile section to open dropdown menu
    const userProfileSection = page.locator('.user-profile-section');
    await userProfileSection.click();
    
    // Wait for dropdown menu to appear
    await page.waitForTimeout(500);
    
    // Click logout option in the dropdown
    const logoutOption = page.getByText('Logout');
    await logoutOption.click();
    
    // Verify redirected to login
    await page.waitForURL(url => url.toString().includes('/login'), { timeout: 10000 });
    await expect(page.locator('[data-testid="username"] input')).toBeVisible();
  });
});