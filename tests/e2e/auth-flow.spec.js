import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test('should login successfully with admin credentials', async ({ page }) => {
    // Navigate to login page
    await page.goto('/login');
    
    // Verify login page loads - target actual input elements
    await expect(page.locator('[data-testid="username"] input')).toBeVisible();
    await expect(page.locator('[data-testid="password"] input')).toBeVisible();
    await expect(page.locator('[data-testid="login-button"]')).toBeVisible();
    
    // Fill in valid credentials
    await page.locator('[data-testid="username"] input').fill('admin');
    await page.locator('[data-testid="password"] input').fill('admin123456789');
    
    // Wait for form validation to complete and button to be enabled
    await expect(page.locator('[data-testid="login-button"]')).toBeEnabled();
    
    // Submit form
    await page.locator('[data-testid="login-button"]').click();
    
    // Wait for redirect after successful login with longer timeout
    await page.waitForURL(url => !url.toString().includes('/login'), { timeout: 15000 });
    
    // Verify we're redirected to admin dashboard
    await expect(page).toHaveURL(/.*\/admin|.*\//); // admin or root path
    
    // Verify admin interface elements are present
    const adminElements = await page.locator('nav, .v-navigation-drawer, .v-app-bar').count();
    expect(adminElements).toBeGreaterThan(0);
  });

  test('should show error with invalid credentials', async ({ page }) => {
    // Navigate to login page
    await page.goto('/login');
    
    // Fill in invalid credentials
    await page.locator('[data-testid="username"] input').fill('invalid');
    await page.locator('[data-testid="password"] input').fill('wrongpassword');
    
    // Wait for form validation to complete and button to be enabled
    await expect(page.locator('[data-testid="login-button"]')).toBeEnabled();
    
    // Submit form
    await page.locator('[data-testid="login-button"]').click();
    
    // Wait a moment for error to appear
    await page.waitForTimeout(2000);
    
    // Verify we're still on login page
    expect(page.url()).toContain('/login');
    
    // Verify error message appears
    const errorAlert = page.locator('.v-alert').filter({ hasText: 'Invalid username or password' });
    await expect(errorAlert).toBeVisible({ timeout: 5000 });
  });

  test('should validate required fields', async ({ page }) => {
    // Navigate to login page
    await page.goto('/login');
    
    // Verify login page loads
    await expect(page.locator('[data-testid="username"] input')).toBeVisible();
    await expect(page.locator('[data-testid="password"] input')).toBeVisible();
    
    // Login button should be disabled when form is empty
    const loginButton = page.locator('[data-testid="login-button"]');
    await expect(loginButton).toBeDisabled();
    
    // Fill in only username
    await page.locator('[data-testid="username"] input').fill('admin');
    // Button should still be disabled with only username filled
    await expect(loginButton).toBeDisabled();
    
    // Clear username and fill only password
    await page.locator('[data-testid="username"] input').clear();
    await page.locator('[data-testid="password"] input').fill('password');
    // Button should still be disabled with only password filled
    await expect(loginButton).toBeDisabled();
    
    // Fill both fields - now button should be enabled
    await page.locator('[data-testid="username"] input').fill('admin');
    await expect(loginButton).toBeEnabled();
  });
});