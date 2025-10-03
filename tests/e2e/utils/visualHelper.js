/**
 * Visual regression testing utilities
 */
class VisualHelper {
  constructor(page) {
    this.page = page;
    this.screenshotOptions = {
      fullPage: true,
      threshold: 0.2,
      maxDiffPixels: 1000,
    };
  }

  /**
   * Take a full page screenshot for comparison
   */
  async takeFullPageScreenshot(name, options = {}) {
    const mergedOptions = { ...this.screenshotOptions, ...options };
    
    // Wait for page to be stable
    await this.waitForPageStable();
    
    // Hide dynamic content that might cause flaky tests
    await this.hideDynamicContent();
    
    return await this.page.screenshot({
      fullPage: mergedOptions.fullPage,
      path: `test-results/screenshots/${name}.png`,
      ...mergedOptions
    });
  }

  /**
   * Compare screenshot with baseline
   */
  async compareScreenshot(name, options = {}) {
    await this.waitForPageStable();
    await this.hideDynamicContent();
    
    const mergedOptions = { ...this.screenshotOptions, ...options };
    
    await expect(this.page).toHaveScreenshot(`${name}.png`, mergedOptions);
  }

  /**
   * Take element screenshot
   */
  async takeElementScreenshot(selector, name, options = {}) {
    const element = this.page.locator(selector);
    await element.waitFor();
    
    // Wait for element to be stable
    await this.waitForElementStable(element);
    
    return await element.screenshot({
      path: `test-results/screenshots/elements/${name}.png`,
      ...options
    });
  }

  /**
   * Compare element screenshot
   */
  async compareElementScreenshot(selector, name, options = {}) {
    const element = this.page.locator(selector);
    await element.waitFor();
    await this.waitForElementStable(element);
    
    const mergedOptions = { ...this.screenshotOptions, ...options };
    
    await expect(element).toHaveScreenshot(`${name}.png`, mergedOptions);
  }

  /**
   * Wait for page to be visually stable
   */
  async waitForPageStable(timeout = 3000) {
    // Wait for network to be idle
    await this.page.waitForLoadState('networkidle');
    
    // Wait for any animations or transitions
    await this.page.waitForTimeout(1000);
    
    // Wait for loading indicators to disappear
    const loadingSelectors = [
      '.v-progress-circular',
      '.v-skeleton-loader',
      '[data-testid="loading"]',
      '.loading',
      '.spinner'
    ];
    
    for (const selector of loadingSelectors) {
      try {
        await this.page.waitForSelector(selector, { state: 'hidden', timeout: 2000 });
      } catch {
        // Selector might not exist, which is fine
      }
    }
    
    // Wait a bit more for any final rendering
    await this.page.waitForTimeout(500);
  }

  /**
   * Wait for element to be visually stable
   */
  async waitForElementStable(element, timeout = 2000) {
    // Wait for element to be visible
    await element.waitFor({ state: 'visible' });
    
    // Wait for any element-specific loading states
    const loadingChild = element.locator('.v-progress-circular, .loading');
    try {
      await loadingChild.waitFor({ state: 'hidden', timeout: 1000 });
    } catch {
      // No loading child found, which is fine
    }
    
    // Wait a bit for stability
    await this.page.waitForTimeout(300);
  }

  /**
   * Hide dynamic content that causes flaky visual tests
   */
  async hideDynamicContent() {
    await this.page.addStyleTag({
      content: `
        /* Hide elements that change frequently */
        [data-testid="timestamp"],
        .timestamp,
        .last-updated,
        .created-at,
        .updated-at,
        .time,
        .date,
        .v-progress-circular,
        .v-skeleton-loader {
          visibility: hidden !important;
        }
        
        /* Disable animations for consistent screenshots */
        *,
        *::before,
        *::after {
          animation-duration: 0s !important;
          animation-delay: 0s !important;
          transition-duration: 0s !important;
          transition-delay: 0s !important;
        }
        
        /* Hide cursor-dependent states */
        *:hover {
          /* Reset hover states that might be inconsistent */
        }
      `
    });
  }

  /**
   * Prepare page for visual testing
   */
  async preparePage() {
    // Set consistent viewport
    await this.page.setViewportSize({ width: 1280, height: 720 });
    
    // Disable animations
    await this.page.addInitScript(() => {
      // Disable CSS animations and transitions
      const style = document.createElement('style');
      style.textContent = `
        *, *::before, *::after {
          animation-duration: 0s !important;
          animation-delay: 0s !important;
          transition-duration: 0s !important;
          transition-delay: 0s !important;
        }
      `;
      document.head.appendChild(style);
      
      // Mock Date for consistent timestamps
      const mockDate = new Date('2024-01-15T12:00:00.000Z');
      const OriginalDate = Date;
      global.Date = class extends OriginalDate {
        constructor(...args) {
          super(...args);
          if (args.length === 0) {
            // Set the time to our mock date
            this.setTime(mockDate.getTime());
          }
        }
        static now() {
          return mockDate.getTime();
        }
      };
    });
  }

  /**
   * Capture visual state of the followup settings page
   */
  async captureFollowupSettingsState(name) {
    // Wait for metrics to load
    await this.page.waitForSelector('.metric-card', { state: 'visible' });
    
    // Hide dynamic metric values for consistent comparison
    await this.page.addStyleTag({
      content: `
        .metric-value,
        .metric-trend,
        .timestamp {
          color: transparent !important;
        }
      `
    });
    
    await this.compareScreenshot(`followup-settings-${name}`);
  }

  /**
   * Capture category accordion state
   */
  async captureCategoryAccordionState(name, expandedCategories = []) {
    const accordion = this.page.locator('.v-expansion-panels');
    await accordion.waitFor();
    
    // Expand specified categories
    for (const categoryName of expandedCategories) {
      const categoryPanel = accordion.locator(`:has-text("${categoryName}")`);
      const header = categoryPanel.locator('.v-expansion-panel-title');
      if (await header.isVisible()) {
        await header.click();
        await this.waitForPageStable();
      }
    }
    
    await this.compareElementScreenshot('.v-expansion-panels', `category-accordion-${name}`);
  }

  /**
   * Capture dialog state
   */
  async captureDialogState(name) {
    const dialog = this.page.locator('.v-dialog:visible');
    await dialog.waitFor();
    
    // Wait for dialog animations
    await this.page.waitForTimeout(500);
    
    await this.compareElementScreenshot('.v-dialog:visible', `dialog-${name}`);
  }

  /**
   * Capture mobile layout
   */
  async captureMobileLayout(name) {
    // Set mobile viewport
    await this.page.setViewportSize({ width: 375, height: 667 });
    
    await this.waitForPageStable();
    
    // Open mobile menu if it exists
    const menuToggle = this.page.locator('.v-app-bar__nav-icon, [data-testid="menu-toggle"]');
    if (await menuToggle.isVisible()) {
      await menuToggle.click();
      await this.page.waitForTimeout(500);
    }
    
    await this.compareScreenshot(`mobile-${name}`);
  }

  /**
   * Generate visual test report
   */
  async generateVisualReport(testResults) {
    const report = {
      timestamp: new Date().toISOString(),
      browser: await this.page.context().browser().browserType().name(),
      viewport: await this.page.viewportSize(),
      results: testResults,
      summary: {
        total: testResults.length,
        passed: testResults.filter(r => r.status === 'passed').length,
        failed: testResults.filter(r => r.status === 'failed').length,
        diff_pixels: testResults.reduce((sum, r) => sum + (r.diff_pixels || 0), 0)
      }
    };
    
    // Save report
    const fs = require('fs');
    const path = require('path');
    
    const reportPath = path.join('test-results', 'visual-report.json');
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
    
    console.log(`📊 Visual test report saved to ${reportPath}`);
    return report;
  }

  /**
   * Mask dynamic elements for consistent comparison
   */
  async maskDynamicElements() {
    await this.page.addStyleTag({
      content: `
        /* Mask elements with dynamic content */
        [data-mask="dynamic"],
        .metric-value,
        .timestamp,
        .last-updated,
        .session-id,
        .request-id {
          background-color: #f0f0f0 !important;
          color: #f0f0f0 !important;
        }
        
        /* Hide elements that shouldn't be compared */
        [data-visual-ignore="true"] {
          display: none !important;
        }
      `
    });
  }
}

export default VisualHelper;