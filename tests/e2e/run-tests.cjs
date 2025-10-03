#!/usr/bin/env node

// Simple test runner for e2e tests
const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

console.log('🚀 Starting E2E Test Suite for Admin Followup Management');

// Check if services are running
async function checkServices() {
  console.log('🔍 Checking if services are running...');
  
  try {
    const response = await fetch('http://localhost:8000/health');
    if (!response.ok) throw new Error('Backend not ready');
    console.log('✅ Backend service (port 8000) is ready');
  } catch (error) {
    console.error('❌ Backend service not available on port 8000');
    console.log('Please start the backend: npm run admin:backend');
    process.exit(1);
  }
  
  try {
    const response = await fetch('http://localhost:3000');
    if (!response.ok) throw new Error('Frontend not ready');
    console.log('✅ Frontend service (port 3000) is ready');
  } catch (error) {
    console.error('❌ Frontend service not available on port 3000');
    console.log('Please start the frontend: npm run admin:frontend');
    process.exit(1);
  }
}

// Run a basic authentication test
async function runBasicAuthTest() {
  console.log('🔐 Running basic authentication test...');
  
  try {
    // Test admin login endpoint
    const loginResponse = await fetch('http://localhost:8000/api/admin/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: process.env.ADMIN_DEFAULT_USERNAME || 'admin',
        password: process.env.ADMIN_DEFAULT_PASSWORD || 'admin123456789'
      })
    });
    
    if (loginResponse.ok) {
      console.log('✅ Admin authentication working');
      return true;
    } else {
      console.error('❌ Admin authentication failed:', loginResponse.status);
      return false;
    }
  } catch (error) {
    console.error('❌ Authentication test failed:', error.message);
    return false;
  }
}

// Test API endpoints
async function runAPITests() {
  console.log('📡 Testing API endpoints...');
  
  // Login first to get session
  const loginResponse = await fetch('http://localhost:8000/api/admin/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username: process.env.ADMIN_DEFAULT_USERNAME || 'admin',
      password: process.env.ADMIN_DEFAULT_PASSWORD || 'admin123456789'
    })
  });
  
  if (!loginResponse.ok) {
    console.error('❌ Could not authenticate for API tests');
    return false;
  }
  
  const setCookieHeader = loginResponse.headers.get('set-cookie');
  
  // Test categories endpoint
  try {
    const categoriesResponse = await fetch('http://localhost:8000/api/admin/settings/followup/categories', {
      headers: { 'Cookie': setCookieHeader || '' }
    });
    
    if (categoriesResponse.ok) {
      const categories = await categoriesResponse.json();
      console.log(`✅ Categories API working (${categories.length || 0} categories found)`);
    } else {
      console.error('❌ Categories API failed:', categoriesResponse.status);
      return false;
    }
  } catch (error) {
    console.error('❌ Categories API test failed:', error.message);
    return false;
  }
  
  // Test settings endpoint
  try {
    const settingsResponse = await fetch('http://localhost:8000/api/admin/settings/followup', {
      headers: { 'Cookie': setCookieHeader || '' }
    });
    
    if (settingsResponse.ok) {
      const settings = await settingsResponse.json();
      console.log(`✅ Settings API working (enabled: ${settings.enabled})`);
    } else {
      console.error('❌ Settings API failed:', settingsResponse.status);
      return false;
    }
  } catch (error) {
    console.error('❌ Settings API test failed:', error.message);
    return false;
  }
  
  return true;
}

// Main test runner
async function runTests() {
  try {
    console.log('📋 E2E Test Suite - Admin Followup Management\n');
    
    // Pre-flight checks
    await checkServices();
    
    const authResult = await runBasicAuthTest();
    if (!authResult) {
      console.error('\n❌ Authentication tests failed - stopping test suite');
      process.exit(1);
    }
    
    const apiResult = await runAPITests();
    if (!apiResult) {
      console.error('\n❌ API tests failed - stopping test suite');
      process.exit(1);
    }
    
    console.log('\n🎉 All basic tests passed!');
    console.log('\n📊 Test Summary:');
    console.log('✅ Service availability: PASS');
    console.log('✅ Authentication flow: PASS');
    console.log('✅ API endpoints: PASS');
    console.log('\n🔧 To run full Playwright tests:');
    console.log('   cd tests/e2e');
    console.log('   npx playwright test --headed');
    console.log('\n📖 For more options, see: tests/e2e/README.md');
    
  } catch (error) {
    console.error('\n❌ Test suite failed:', error.message);
    process.exit(1);
  }
}

// Run the tests
runTests();