/**
 * Performance testing utilities for e2e tests
 */
class PerformanceHelper {
  constructor(page) {
    this.page = page;
    this.metrics = {};
  }

  /**
   * Start performance monitoring
   */
  async startMonitoring() {
    // Enable performance monitoring
    await this.page.context().tracing.start({
      screenshots: true,
      snapshots: true,
      sources: true
    });

    // Start collecting metrics
    this.metrics = {
      startTime: Date.now(),
      navigationTiming: null,
      resourceTiming: [],
      customMarks: new Map(),
      memoryUsage: []
    };

    // Collect performance API data
    await this.page.evaluate(() => {
      // Mark the start of test
      performance.mark('test-start');
      
      // Listen for resource loading
      window.performanceObserver = new PerformanceObserver((list) => {
        window.resourceTimings = list.getEntries();
      });
      window.performanceObserver.observe({ entryTypes: ['resource'] });
    });
  }

  /**
   * Stop performance monitoring and collect results
   */
  async stopMonitoring(testName) {
    const endTime = Date.now();
    
    // Collect final performance data
    const performanceData = await this.page.evaluate(() => {
      performance.mark('test-end');
      performance.measure('test-duration', 'test-start', 'test-end');
      
      return {
        navigation: performance.getEntriesByType('navigation')[0],
        resources: performance.getEntriesByType('resource'),
        measures: performance.getEntriesByType('measure'),
        memory: performance.memory ? {
          usedJSHeapSize: performance.memory.usedJSHeapSize,
          totalJSHeapSize: performance.memory.totalJSHeapSize,
          jsHeapSizeLimit: performance.memory.jsHeapSizeLimit
        } : null
      };
    });

    // Stop tracing
    await this.page.context().tracing.stop({
      path: `test-results/traces/trace-${testName}-${Date.now()}.zip`
    });

    // Compile results
    const results = {
      testName,
      duration: endTime - this.metrics.startTime,
      performanceData,
      customMarks: Object.fromEntries(this.metrics.customMarks),
      timestamp: new Date().toISOString()
    };

    this.savePerformanceResults(results);
    return results;
  }

  /**
   * Measure page load time
   */
  async measurePageLoad(url, options = {}) {
    const startTime = Date.now();
    
    // Start measuring
    await this.startMonitoring();
    
    // Navigate to page
    await this.page.goto(url, { 
      waitUntil: options.waitUntil || 'networkidle',
      timeout: options.timeout || 30000
    });

    // Wait for additional loading indicators
    await this.waitForPageComplete();
    
    const loadTime = Date.now() - startTime;
    
    // Get detailed timing
    const navigationTiming = await this.page.evaluate(() => {
      const nav = performance.getEntriesByType('navigation')[0];
      return {
        domContentLoaded: nav.domContentLoadedEventEnd - nav.domContentLoadedEventStart,
        load: nav.loadEventEnd - nav.loadEventStart,
        domInteractive: nav.domInteractive - nav.fetchStart,
        firstPaint: performance.getEntriesByName('first-paint')[0]?.startTime,
        firstContentfulPaint: performance.getEntriesByName('first-contentful-paint')[0]?.startTime
      };
    });

    return {
      totalLoadTime: loadTime,
      navigationTiming,
      url
    };
  }

  /**
   * Measure interaction response time
   */
  async measureInteraction(action, actionName) {
    const startTime = Date.now();
    
    // Mark start of interaction
    await this.page.evaluate((name) => {
      performance.mark(`interaction-${name}-start`);
    }, actionName);

    // Perform the action
    const result = await action();

    // Wait for any loading states to complete
    await this.waitForInteractionComplete();

    const endTime = Date.now();
    
    // Mark end of interaction
    await this.page.evaluate((name) => {
      performance.mark(`interaction-${name}-end`);
      performance.measure(`interaction-${name}`, `interaction-${name}-start`, `interaction-${name}-end`);
    }, actionName);

    const responseTime = endTime - startTime;
    
    // Store metric
    this.metrics.customMarks.set(actionName, responseTime);

    return {
      actionName,
      responseTime,
      result
    };
  }

  /**
   * Measure form submission performance
   */
  async measureFormSubmission(formSelector, submitAction) {
    return await this.measureInteraction(async () => {
      // Fill and submit form
      await submitAction();
      
      // Wait for response
      await this.page.waitForLoadState('networkidle');
      
      // Check for success indicators
      const hasSuccess = await this.page.locator('.v-snackbar--color-success, .success, .v-alert--type-success').isVisible().catch(() => false);
      const hasError = await this.page.locator('.v-snackbar--color-error, .error, .v-alert--type-error').isVisible().catch(() => false);
      
      return { hasSuccess, hasError };
    }, 'form-submission');
  }

  /**
   * Measure data loading performance
   */
  async measureDataLoad(triggerAction, dataSelector) {
    return await this.measureInteraction(async () => {
      // Trigger data loading
      await triggerAction();
      
      // Wait for data to appear
      await this.page.waitForSelector(dataSelector, { state: 'visible', timeout: 10000 });
      
      // Count loaded items
      const count = await this.page.locator(dataSelector).count();
      
      return { itemsLoaded: count };
    }, 'data-load');
  }

  /**
   * Wait for page to be completely loaded
   */
  async waitForPageComplete() {
    // Wait for network idle
    await this.page.waitForLoadState('networkidle');
    
    // Wait for common loading indicators to disappear
    const loadingSelectors = [
      '.v-progress-circular',
      '.v-skeleton-loader',
      '[data-testid="loading"]',
      '.loading-spinner'
    ];
    
    for (const selector of loadingSelectors) {
      try {
        await this.page.waitForSelector(selector, { state: 'hidden', timeout: 2000 });
      } catch {
        // Selector might not exist
      }
    }
    
    // Wait a bit more for any final rendering
    await this.page.waitForTimeout(1000);
  }

  /**
   * Wait for interaction to complete
   */
  async waitForInteractionComplete() {
    // Wait for any network requests triggered by interaction
    await this.page.waitForLoadState('networkidle');
    
    // Wait for loading states
    await this.waitForPageComplete();
  }

  /**
   * Measure API response times
   */
  async measureApiCalls(action, actionName) {
    const apiCalls = [];
    
    // Listen for API calls
    this.page.on('response', (response) => {
      if (response.url().includes('/admin/') || response.url().includes('/api/')) {
        apiCalls.push({
          url: response.url(),
          method: response.request().method(),
          status: response.status(),
          timing: response.timing()
        });
      }
    });
    
    // Perform action
    const result = await action();
    
    // Stop listening
    this.page.removeAllListeners('response');
    
    return {
      actionName,
      apiCalls,
      totalCalls: apiCalls.length,
      result
    };
  }

  /**
   * Measure memory usage during test
   */
  async measureMemoryUsage() {
    const memoryInfo = await this.page.evaluate(() => {
      if (performance.memory) {
        return {
          used: Math.round(performance.memory.usedJSHeapSize / 1024 / 1024),
          total: Math.round(performance.memory.totalJSHeapSize / 1024 / 1024),
          limit: Math.round(performance.memory.jsHeapSizeLimit / 1024 / 1024),
          timestamp: Date.now()
        };
      }
      return null;
    });
    
    if (memoryInfo) {
      this.metrics.memoryUsage.push(memoryInfo);
    }
    
    return memoryInfo;
  }

  /**
   * Measure bulk operations performance
   */
  async measureBulkOperation(operation, itemCount, actionName) {
    const startTime = Date.now();
    
    // Measure memory before
    const memoryBefore = await this.measureMemoryUsage();
    
    // Perform bulk operation
    const result = await this.measureInteraction(operation, actionName);
    
    // Measure memory after
    const memoryAfter = await this.measureMemoryUsage();
    
    const totalTime = Date.now() - startTime;
    
    return {
      actionName,
      itemCount,
      totalTime,
      timePerItem: totalTime / itemCount,
      memoryBefore,
      memoryAfter,
      memoryDelta: memoryAfter && memoryBefore ? memoryAfter.used - memoryBefore.used : null,
      result
    };
  }

  /**
   * Save performance results to file
   */
  savePerformanceResults(results) {
    const fs = require('fs');
    const path = require('path');
    
    const resultsDir = path.join('test-results', 'performance');
    if (!fs.existsSync(resultsDir)) {
      fs.mkdirSync(resultsDir, { recursive: true });
    }
    
    const filename = `${results.testName}-${Date.now()}.json`;
    const filepath = path.join(resultsDir, filename);
    
    fs.writeFileSync(filepath, JSON.stringify(results, null, 2));
    
    console.log(`📊 Performance results saved to ${filepath}`);
  }

  /**
   * Generate performance report
   */
  generatePerformanceReport(allResults) {
    const report = {
      timestamp: new Date().toISOString(),
      summary: {
        totalTests: allResults.length,
        averageResponseTime: allResults.reduce((sum, r) => sum + (r.responseTime || 0), 0) / allResults.length,
        slowestTest: allResults.reduce((slowest, current) => 
          (current.responseTime || 0) > (slowest.responseTime || 0) ? current : slowest
        ),
        fastestTest: allResults.reduce((fastest, current) => 
          (current.responseTime || 0) < (fastest.responseTime || 0) ? current : fastest
        )
      },
      tests: allResults,
      thresholds: {
        pageLoad: 3000, // 3 seconds
        interaction: 1000, // 1 second
        apiCall: 500 // 500ms
      }
    };
    
    // Check for performance regressions
    report.regressions = allResults.filter(test => {
      if (test.actionName?.includes('page-load')) return test.responseTime > report.thresholds.pageLoad;
      if (test.actionName?.includes('interaction')) return test.responseTime > report.thresholds.interaction;
      if (test.actionName?.includes('api')) return test.responseTime > report.thresholds.apiCall;
      return false;
    });
    
    const fs = require('fs');
    const reportPath = 'test-results/performance-report.json';
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
    
    console.log(`📊 Performance report generated: ${reportPath}`);
    console.log(`🏃 Average response time: ${Math.round(report.summary.averageResponseTime)}ms`);
    console.log(`⚠️ Performance regressions: ${report.regressions.length}`);
    
    return report;
  }
}

export default PerformanceHelper;