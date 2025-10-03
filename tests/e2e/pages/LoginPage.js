import BasePage from './BasePage.js';

class LoginPage extends BasePage {
  constructor(page) {
    super(page);
    
    // Page elements - updated to work with our Vuetify implementation
    this.usernameInput = page.locator('[data-testid="username"] input');
    this.passwordInput = page.locator('[data-testid="password"] input');
    this.loginButton = page.locator('[data-testid="login-button"]');
    this.errorMessage = page.locator('.v-alert');
    this.loadingIndicator = page.locator('.v-progress-circular, [data-testid="loading"]');
  }

  async goto() {
    await this.navigateTo('/login');
    // Wait for login elements to be visible instead of form
    await this.page.waitForSelector('[data-testid="username"] input', { state: 'visible' });
    await this.page.waitForSelector('[data-testid="password"] input', { state: 'visible' });
  }

  async login(username, password) {
    await this.usernameInput.fill(username);
    await this.passwordInput.fill(password);
    
    // Check if button is enabled (for non-empty credentials) or disabled (for empty credentials)
    const isButtonEnabled = await this.loginButton.isEnabled();
    
    if (!isButtonEnabled) {
      // Button is disabled (empty credentials case)
      return { success: false, error: 'Login button disabled due to empty credentials' };
    }
    
    // Click login and wait for navigation or error
    const navigationPromise = this.page.waitForURL(url => !url.toString().includes('/login'), { timeout: 15000 });
    await this.loginButton.click();
    
    try {
      await navigationPromise;
      await this.waitForLoading();
      return { success: true };
    } catch (error) {
      // Check for error messages
      const errorText = await this.getErrorMessage();
      return { success: false, error: errorText };
    }
  }

  async getErrorMessage() {
    try {
      await this.errorMessage.waitFor({ timeout: 3000 });
      return await this.errorMessage.textContent();
    } catch {
      return null;
    }
  }

  async isLoggedIn() {
    // Check if we're redirected away from login page
    const currentUrl = this.page.url();
    return !currentUrl.includes('/login');
  }

  async logout() {
    // Look for logout button in navigation
    const logoutButton = this.page.locator('button:has-text("Logout"), button:has-text("Sign out"), [data-testid="logout"]');
    
    if (await logoutButton.isVisible()) {
      await logoutButton.click();
      await this.page.waitForURL('**/login');
    }
  }
}

export default LoginPage;