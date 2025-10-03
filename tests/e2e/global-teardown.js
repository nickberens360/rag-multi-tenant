async function globalTeardown(config) {
  console.log('🧹 Starting global teardown for admin e2e tests...');
  
  try {
    // Clean up any remaining test data
    await cleanupTestData();
    
    // Generate final test reports
    await generateFinalReports();
    
    // Archive test results
    await archiveTestResults();
    
    console.log('✅ Global teardown completed');
  } catch (error) {
    console.error('❌ Error during global teardown:', error.message);
  }
}

async function cleanupTestData() {
  console.log('🧹 Cleaning up remaining test data...');
  
  try {
    // Use fetch directly since we don't have browser context here
    const response = await fetch('http://localhost:8000/admin/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: process.env.ADMIN_DEFAULT_USERNAME || 'admin',
        password: process.env.ADMIN_DEFAULT_PASSWORD || 'admin123456789'
      })
    });

    if (response.ok) {
      // Get session cookie for cleanup requests
      const setCookieHeader = response.headers.get('set-cookie');
      
      // Clean up test categories
      const categoriesResponse = await fetch('http://localhost:8000/admin/settings/followup/categories?include_inactive=true', {
        headers: {
          'Cookie': setCookieHeader || ''
        }
      });

      if (categoriesResponse.ok) {
        const categories = await categoriesResponse.json();
        const testCategories = categories.filter(c => 
          c.name?.match(/^(test_|bulk_|perf_)/) ||
          c.display_name?.includes('Test') ||
          c.display_name?.includes('Bulk') ||
          c.display_name?.includes('Performance')
        );

        for (const category of testCategories) {
          await fetch(`http://localhost:8000/admin/settings/followup/categories/${category.id}/delete`, {
            method: 'POST',
            headers: { 
              'Content-Type': 'application/json',
              'Cookie': setCookieHeader || ''
            },
            body: JSON.stringify({ strategy: 'delete' })
          });
        }

        console.log(`✅ Cleaned up ${testCategories.length} test categories`);
      }
    }
  } catch (error) {
    console.warn('⚠️ Could not complete data cleanup:', error.message);
  }
}

async function generateFinalReports() {
  console.log('📊 Generating final test reports...');
  
  try {
    const fs = await import('fs');
    const path = await import('path');
    
    // Check if results directory exists
    const resultsDir = 'test-results';
    if (!fs.existsSync(resultsDir)) {
      console.log('No test results directory found, skipping report generation');
      return;
    }

    // Compile performance results
    const performanceDir = path.join(resultsDir, 'performance');
    if (fs.existsSync(performanceDir)) {
      const performanceFiles = fs.readdirSync(performanceDir)
        .filter(file => file.endsWith('.json'))
        .map(file => {
          const filePath = path.join(performanceDir, file);
          return JSON.parse(fs.readFileSync(filePath, 'utf8'));
        });

      if (performanceFiles.length > 0) {
        const performanceSummary = {
          timestamp: new Date().toISOString(),
          totalTests: performanceFiles.length,
          averageResponseTime: performanceFiles.reduce((sum, r) => sum + (r.responseTime || r.duration || 0), 0) / performanceFiles.length,
          tests: performanceFiles,
          thresholds: {
            pageLoad: 5000,
            interaction: 2000,
            apiCall: 1000
          }
        };

        // Check for regressions
        performanceSummary.regressions = performanceFiles.filter(test => {
          const responseTime = test.responseTime || test.duration || 0;
          if (test.testName?.includes('page-load')) return responseTime > performanceSummary.thresholds.pageLoad;
          if (test.testName?.includes('interaction')) return responseTime > performanceSummary.thresholds.interaction;
          if (test.testName?.includes('api')) return responseTime > performanceSummary.thresholds.apiCall;
          return false;
        });

        fs.writeFileSync(
          path.join(resultsDir, 'final-performance-report.json'), 
          JSON.stringify(performanceSummary, null, 2)
        );

        console.log(`📈 Performance report: ${performanceFiles.length} tests, ${performanceSummary.regressions.length} regressions`);
      }
    }

    // Compile visual test results
    const visualReportPath = path.join(resultsDir, 'visual-report.json');
    if (fs.existsSync(visualReportPath)) {
      console.log('📷 Visual regression report available');
    }

    // Create test summary
    const summary = {
      timestamp: new Date().toISOString(),
      testRun: {
        environment: process.env.NODE_ENV || 'test',
        baseUrl: 'http://localhost:3000',
        apiUrl: 'http://localhost:8000/admin'
      },
      performance: fs.existsSync(path.join(resultsDir, 'final-performance-report.json')),
      visual: fs.existsSync(visualReportPath),
      screenshots: fs.existsSync(path.join(resultsDir, 'screenshots')),
      traces: fs.existsSync(path.join(resultsDir, 'traces'))
    };

    fs.writeFileSync(path.join(resultsDir, 'test-summary.json'), JSON.stringify(summary, null, 2));
    
    console.log('✅ Final test reports generated');
  } catch (error) {
    console.warn('⚠️ Could not generate final reports:', error.message);
  }
}

async function archiveTestResults() {
  console.log('📦 Archiving test results...');
  
  try {
    const fs = await import('fs');
    const path = await import('path');
    
    const resultsDir = 'test-results';
    if (!fs.existsSync(resultsDir)) {
      return;
    }

    // Only archive if running in CI or if explicitly requested
    if (process.env.CI || process.env.ARCHIVE_RESULTS === 'true') {
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const archiveDir = `test-results-archive-${timestamp}`;
      
      // Create archive directory
      if (!fs.existsSync(archiveDir)) {
        fs.mkdirSync(archiveDir);
      }

      // Copy important files
      const filesToArchive = [
        'test-summary.json',
        'final-performance-report.json',
        'visual-report.json',
        'results.json'
      ];

      for (const file of filesToArchive) {
        const sourcePath = path.join(resultsDir, file);
        const destPath = path.join(archiveDir, file);
        
        if (fs.existsSync(sourcePath)) {
          fs.copyFileSync(sourcePath, destPath);
        }
      }

      // Copy screenshots directory if it exists
      const screenshotsDir = path.join(resultsDir, 'screenshots');
      if (fs.existsSync(screenshotsDir)) {
        const archiveScreenshotsDir = path.join(archiveDir, 'screenshots');
        fs.mkdirSync(archiveScreenshotsDir, { recursive: true });
        
        const screenshots = fs.readdirSync(screenshotsDir);
        for (const screenshot of screenshots) {
          fs.copyFileSync(
            path.join(screenshotsDir, screenshot),
            path.join(archiveScreenshotsDir, screenshot)
          );
        }
      }

      console.log(`✅ Test results archived to ${archiveDir}`);
    } else {
      console.log('📁 Skipping archive (not in CI environment)');
    }
  } catch (error) {
    console.warn('⚠️ Could not archive results:', error.message);
  }
}

export default globalTeardown;