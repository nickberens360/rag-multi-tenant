# Admin Followup Question Management - E2E Tests

This directory contains comprehensive end-to-end tests for the admin followup question management system using Playwright.

## 🏗️ Architecture

### Test Structure
```
tests/e2e/
├── specs/                    # Test specifications
│   ├── auth.spec.js         # Authentication flows
│   ├── categories.spec.js   # Category management
│   ├── questions.spec.js    # Question management
│   ├── settings.spec.js     # System settings
│   ├── bulk-operations.spec.js  # Bulk actions
│   └── performance.spec.js  # Performance testing
├── pages/                   # Page Object Models
│   ├── BasePage.js         # Base page class
│   ├── LoginPage.js        # Login page interactions
│   ├── AdminLayoutPage.js  # Admin dashboard layout
│   └── FollowupSettingsPage.js  # Main settings page
├── utils/                   # Test utilities
│   ├── apiHelper.js        # Backend API integration
│   ├── performanceHelper.js # Performance measurement
│   └── visualHelper.js     # Visual regression testing
├── fixtures/                # Test data and seeding
│   ├── testData.js         # Test data definitions
│   └── databaseSeeder.js   # Database seeding utilities
├── auth.setup.js           # Authentication setup
├── global-setup.js         # Global test setup
└── global-teardown.js      # Global test cleanup
```

## 🚀 Running Tests

### Prerequisites
1. **Backend and Frontend Services** must be running:
   ```bash
   npm run admin:backend  # Port 8000
   npm run admin:frontend # Port 3000
   ```

2. **Environment Variables** (already configured in .env):
   ```bash
   ADMIN_DEFAULT_USERNAME=admin
   ADMIN_DEFAULT_PASSWORD=admin123456789
   ```

### Run All E2E Tests
```bash
# Run all tests
npx playwright test

# Run specific test suite
npx playwright test auth.spec.js
npx playwright test categories.spec.js
npx playwright test questions.spec.js
npx playwright test settings.spec.js
npx playwright test bulk-operations.spec.js
npx playwright test performance.spec.js

# Run tests in headed mode (see browser)
npx playwright test --headed

# Run tests in debug mode
npx playwright test --debug

# Generate test report
npx playwright show-report
```

### Run Performance Tests Only
```bash
npx playwright test performance.spec.js

# View performance results
cat test-results/final-performance-report.json
```

### Run Visual Regression Tests
```bash
# Generate baseline screenshots (first run)
npx playwright test --update-snapshots

# Run visual regression tests
npx playwright test
```

## 📊 Test Coverage

### 1. Authentication Flow (`auth.spec.js`)
- ✅ Successful login with valid credentials
- ✅ Failed login with invalid credentials  
- ✅ Session persistence across page reloads
- ✅ Logout functionality
- ✅ Protected route access control
- ✅ Login with redirect to original destination
- ✅ Visual regression testing
- ✅ Performance measurement

### 2. Category Management (`categories.spec.js`)
- ✅ Create new categories
- ✅ Edit existing categories
- ✅ Delete categories with different strategies:
  - Move questions to another category
  - Delete category and all questions
  - Deactivate category (soft delete)
- ✅ Bulk operations (activate, deactivate, delete)
- ✅ Form validation
- ✅ Visual regression testing
- ✅ Performance measurement
- ✅ Accessibility testing

### 3. Question Management (`questions.spec.js`)
- ✅ Create new questions in categories
- ✅ Edit question text and properties
- ✅ Delete questions with confirmation
- ✅ Reorder questions using arrow buttons
- ✅ Toggle question active/inactive status
- ✅ Bulk question operations
- ✅ Form validation (required fields, length limits)
- ✅ Question search functionality
- ✅ Pagination handling
- ✅ Visual regression testing
- ✅ Performance measurement
- ✅ Error handling (network failures)
- ✅ Concurrent editing scenarios

### 4. System Settings (`settings.spec.js`)
- ✅ Toggle service enable/disable
- ✅ Change service type (static, dynamic, smart)
- ✅ Adjust question limit slider (1-5)
- ✅ Settings persistence across sessions
- ✅ Reset to default settings
- ✅ Metrics display updates
- ✅ Settings validation
- ✅ Concurrent settings changes
- ✅ Settings impact on system behavior
- ✅ Visual regression testing
- ✅ Performance measurement
- ✅ Accessibility testing
- ✅ Error handling

### 5. Bulk Operations (`bulk-operations.spec.js`)
- ✅ Multi-select categories
- ✅ Bulk activate/deactivate categories
- ✅ Bulk delete with confirmation
- ✅ Bulk operations with mixed states
- ✅ Select all/deselect all functionality
- ✅ Bulk question operations
- ✅ Error handling for bulk operations
- ✅ Performance measurement
- ✅ Pagination with bulk operations
- ✅ Undo functionality (if available)
- ✅ Accessibility testing

### 6. Performance Testing (`performance.spec.js`)
- ✅ Page load times (empty state, with data, large datasets)
- ✅ Interaction response times
- ✅ Form submission performance
- ✅ Data loading performance
- ✅ Bulk operations performance
- ✅ Memory usage monitoring
- ✅ API response times
- ✅ Progressive loading performance
- ✅ Concurrent operations performance
- ✅ Performance regression detection

## 🛠️ Test Infrastructure

### Page Object Model
Tests use the Page Object Model pattern for maintainable, reusable code:

```javascript
// Example usage
const followupPage = new FollowupSettingsPage(page);
await followupPage.goto();
await followupPage.createFirstCategory();
await followupPage.fillCategoryForm(testData);
const toast = await followupPage.saveCategoryForm();
```

### Database Seeding
Automated test data management:

```javascript
// Clean slate for each test
await dbSeeder.clearTestData();

// Seed with basic test data
await dbSeeder.seedBasicData();

// Seed with bulk test data
await dbSeeder.seedBulkTestData();

// Seed with performance test data
await dbSeeder.seedPerformanceData();
```

### API Integration
Backend verification for all UI operations:

```javascript
// Verify UI changes via API
const category = await apiHelper.waitForCategoryToExist(categoryName);
expect(category.display_name).toBe(expectedName);

// Direct API operations for setup
await apiHelper.createCategory(testData);
await apiHelper.updateFollowupSettings(newSettings);
```

### Performance Measurement
Built-in performance monitoring:

```javascript
// Measure page load
const loadMetrics = await performanceHelper.measurePageLoad('/settings/followup');
expect(loadMetrics.totalLoadTime).toBeLessThan(5000);

// Measure interactions
const interactionMetrics = await performanceHelper.measureInteraction(async () => {
  await followupPage.toggleService();
}, 'settings-toggle');
```

### Visual Regression Testing
Automated visual comparison:

```javascript
// Compare full page
await visualHelper.compareScreenshot('settings-page');

// Compare specific elements
await visualHelper.compareElementScreenshot('.metric-card', 'metrics-card');

// Capture different states
await visualHelper.captureFollowupSettingsState('with-data');
```

## 📈 Performance Thresholds

The tests enforce these performance standards:

- **Page Load**: < 5 seconds (with data), < 3 seconds (empty)
- **Interactions**: < 2 seconds (forms), < 1 second (toggles)
- **API Calls**: < 1 second per request
- **Bulk Operations**: < 500ms per item
- **Memory Usage**: < 50MB increase per major operation

## 🔧 Configuration

### Playwright Config (`playwright.config.js`)
- **Workers**: 1 (sequential execution for database consistency)
- **Timeout**: 30 seconds per test
- **Retries**: 2 in CI, 0 locally
- **Storage State**: Shared authentication
- **Projects**: Desktop Chrome, Mobile Safari, Performance testing

### Environment Variables
```bash
# Authentication
ADMIN_DEFAULT_USERNAME=admin
ADMIN_DEFAULT_PASSWORD=admin123456789

# Service URLs
VITE_API_BASE_URL=http://localhost:8000/admin

# Test Configuration
NODE_ENV=test
CI=false                    # Set to true in CI environments
ARCHIVE_RESULTS=false      # Set to true to archive results
```

## 📊 Test Reports

### HTML Report
```bash
npx playwright show-report
```

### Performance Report
```bash
cat test-results/final-performance-report.json
```

### Visual Regression Report
```bash
cat test-results/visual-report.json
```

### Test Summary
```bash
cat test-results/test-summary.json
```

## 🐛 Debugging

### Debug Mode
```bash
# Run single test in debug mode
npx playwright test auth.spec.js --debug

# Run with browser visible
npx playwright test --headed --slowMo=1000
```

### Screenshots and Videos
- **Screenshots**: Captured on failure
- **Videos**: Recorded on failure
- **Traces**: Generated on retry

### Common Issues

1. **Services Not Running**
   ```bash
   # Start services first
   npm run admin:backend
   npm run admin:frontend
   ```

2. **Authentication Failures**
   ```bash
   # Verify credentials in .env
   ADMIN_DEFAULT_USERNAME=admin
   ADMIN_DEFAULT_PASSWORD=admin123456789
   ```

3. **Database State Issues**
   ```bash
   # Clear test data manually if needed
   npx playwright test auth.setup.js
   ```

4. **Port Conflicts**
   ```bash
   # Verify ports 3000 and 8000 are available
   lsof -i :3000
   lsof -i :8000
   ```

## 🚀 CI/CD Integration

### GitHub Actions
```yaml
- name: Run E2E Tests
  run: |
    npm run admin:backend &
    npm run admin:frontend &
    sleep 10
    npx playwright test
    
- name: Upload Test Results
  uses: actions/upload-artifact@v3
  with:
    name: test-results
    path: test-results/
```

### Docker Support
```bash
# Run in Docker
docker run --rm -v $(pwd):/work -w /work mcr.microsoft.com/playwright:latest npx playwright test
```

This comprehensive e2e test suite ensures the admin followup question management system is thoroughly tested across all user workflows, performance scenarios, and edge cases.