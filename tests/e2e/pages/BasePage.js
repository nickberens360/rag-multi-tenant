class BasePage {
  constructor(page) {
    this.page = page;
  }

  // Common wait methods
  async waitForLoading() {
    await this.page.waitForLoadState('networkidle');
    // Wait for any loading spinners to disappear
    await this.page.waitForSelector('.v-progress-circular', { state: 'hidden', timeout: 5000 }).catch(() => {});
    await this.page.waitForSelector('[data-testid="loading"]', { state: 'hidden', timeout: 5000 }).catch(() => {});
  }

  async waitForToast() {
    // Wait for success/error toast messages
    const toast = this.page.locator('.v-snackbar, .v-alert, .toast');
    try {
      await toast.waitFor({ timeout: 3000 });
      const message = await toast.textContent();
      return message;
    } catch {
      return null;
    }
  }

  async dismissToast() {
    const closeButton = this.page.locator('.v-snackbar button, .v-alert button, .toast .close');
    if (await closeButton.isVisible()) {
      await closeButton.click();
    }
  }

  // Navigation helpers
  async navigateTo(path) {
    await this.page.goto(path);
    await this.waitForLoading();
  }

  async clickAndWait(selector, options = {}) {
    await this.page.click(selector, options);
    await this.waitForLoading();
  }

  // Form helpers
  async fillForm(fields) {
    for (const [selector, value] of Object.entries(fields)) {
      await this.page.fill(selector, value);
    }
  }

  async submitForm(submitSelector = 'button[type="submit"]') {
    await this.page.click(submitSelector);
    await this.waitForLoading();
  }

  // Dialog helpers
  async waitForDialog() {
    return this.page.locator('.v-dialog, [role="dialog"]').waitFor();
  }

  async closeDialog() {
    const closeButton = this.page.locator('.v-dialog .v-btn:has-text("Cancel"), .v-dialog .v-btn:has-text("Close")');
    if (await closeButton.isVisible()) {
      await closeButton.click();
    }
    await this.page.waitForSelector('.v-dialog', { state: 'hidden' });
  }

  // Table/List helpers
  async getTableRowCount(tableSelector = 'table, .v-data-table') {
    const rows = this.page.locator(`${tableSelector} tbody tr`);
    return await rows.count();
  }

  async getListItemCount(listSelector = '.v-list') {
    const items = this.page.locator(`${listSelector} .v-list-item`);
    return await items.count();
  }

  // Error handling
  async checkForErrors() {
    const errorElements = this.page.locator('.v-alert--type-error, .error, [class*="error"]');
    const errorCount = await errorElements.count();
    
    if (errorCount > 0) {
      const errorText = await errorElements.first().textContent();
      throw new Error(`Page error detected: ${errorText}`);
    }
  }

  // Screenshot helpers
  async takeScreenshot(name) {
    await this.page.screenshot({ path: `test-results/${name}-${Date.now()}.png` });
  }

  // Performance helpers
  async measurePageLoad() {
    const startTime = Date.now();
    await this.waitForLoading();
    return Date.now() - startTime;
  }
}

export default BasePage;