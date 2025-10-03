import BasePage from './BasePage.js';

class AdminLayoutPage extends BasePage {
  constructor(page) {
    super(page);
    
    // Navigation elements - be more specific to avoid pagination nav
    this.navigationDrawer = page.locator('.v-navigation-drawer, nav:has-text("MAIN MENU"), [data-testid="admin-nav"]').first();
    this.settingsLink = page.locator('a:has-text("Settings"), [href*="settings"]');
    this.followupSettingsLink = page.locator('a:has-text("Follow-up"), [href*="followup"]');
    this.dashboardLink = page.locator('a:has-text("Dashboard"), [href*="dashboard"]');
    this.logoutButton = page.locator('button:has-text("Logout"), [data-testid="logout"]');
    
    // Header elements
    this.pageTitle = page.locator('h1, .v-toolbar-title, [data-testid="page-title"]');
    this.userInfo = page.locator('[data-testid="user-info"], .user-menu');
    
    // Loading states
    this.loadingOverlay = page.locator('.v-overlay--active .v-progress-circular');
    this.pageLoading = page.locator('[data-testid="page-loading"]');
  }

  async navigateToSettings() {
    await this.settingsLink.click();
    await this.waitForLoading();
    await this.page.waitForURL('**/settings**');
  }

  async navigateToFollowupSettings() {
    // First go to settings, then to followup
    if (!this.page.url().includes('/settings')) {
      await this.navigateToSettings();
    }
    
    await this.followupSettingsLink.click();
    await this.waitForLoading();
    await this.page.waitForURL('**/settings/followup');
  }

  async navigateToDashboard() {
    await this.dashboardLink.click();
    await this.waitForLoading();
    await this.page.waitForURL(/.*(?:dashboard|\/)/);
  }

  async getCurrentPageTitle() {
    try {
      return await this.pageTitle.textContent();
    } catch {
      return document.title;
    }
  }

  async isNavigationVisible() {
    return await this.navigationDrawer.isVisible();
  }

  async waitForPageLoad() {
    // Wait for navigation and content to load
    await this.waitForLoading();
    
    // Wait for any page-specific loading indicators
    await this.loadingOverlay.waitFor({ state: 'hidden' }).catch(() => {});
    await this.pageLoading.waitFor({ state: 'hidden' }).catch(() => {});
  }

  async logout() {
    // Click on the user profile section to open menu
    const userProfileSection = this.page.locator('.user-profile-section');
    await userProfileSection.click();
    
    // Wait for dropdown menu to be visible
    await this.page.waitForTimeout(500);
    
    // Click the logout option in the dropdown
    const logoutItem = this.page.getByText('Logout');
    await logoutItem.click();
    
    // Wait for redirect to login page
    await this.page.waitForURL('**/login', { timeout: 5000 });
  }

  async getCurrentUser() {
    try {
      const userText = await this.userInfo.textContent();
      return userText?.trim();
    } catch {
      return null;
    }
  }

  // Mobile navigation helpers
  async openMobileMenu() {
    const menuButton = this.page.locator('.v-app-bar__nav-icon, [data-testid="menu-toggle"]');
    if (await menuButton.isVisible()) {
      await menuButton.click();
      await this.navigationDrawer.waitFor({ state: 'visible' });
    }
  }

  async closeMobileMenu() {
    const overlay = this.page.locator('.v-overlay--active');
    if (await overlay.isVisible()) {
      await overlay.click();
      await this.navigationDrawer.waitFor({ state: 'hidden' });
    }
  }

  async isAuthenticated() {
    // Check if we're on an authenticated page by looking for admin elements
    const hasAdminNavigation = await this.navigationDrawer.isVisible();
    const isOnLoginPage = this.page.url().includes('/login');
    
    return hasAdminNavigation && !isOnLoginPage;
  }

  async waitForLoad() {
    // Alias for waitForPageLoad for compatibility
    await this.waitForPageLoad();
  }
}

export default AdminLayoutPage;