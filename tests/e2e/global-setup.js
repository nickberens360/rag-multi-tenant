import { chromium } from '@playwright/test';

async function globalSetup(config) {
  console.log('🚀 Starting global setup for admin e2e tests...');
  
  // Set test environment variables
  process.env.ENVIRONMENT = 'testing';
  process.env.ALLOW_DB_RESET = 'true';
  process.env.ADMIN_DEFAULT_USERNAME = process.env.ADMIN_DEFAULT_USERNAME || 'admin';
  process.env.ADMIN_DEFAULT_PASSWORD = process.env.ADMIN_DEFAULT_PASSWORD || 'admin123456789';
  
  // Wait for services to be ready
  await waitForServices();
  
  // Initialize test database with seed data
  await setupTestDatabase();
  
  console.log('✅ Global setup completed');
}

async function waitForServices() {
  console.log('⏳ Waiting for backend and frontend services...');
  
  const maxRetries = 30;
  const retryDelay = 2000;
  
  // Wait for backend
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch('http://localhost:8000/health');
      if (response.ok) {
        console.log('✅ Backend service ready');
        break;
      }
    } catch (error) {
      if (i === maxRetries - 1) {
        throw new Error('Backend service failed to start');
      }
      await new Promise(resolve => setTimeout(resolve, retryDelay));
    }
  }
  
  // Wait for frontend
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch('http://localhost:3000');
      if (response.ok) {
        console.log('✅ Frontend service ready');
        break;
      }
    } catch (error) {
      if (i === maxRetries - 1) {
        throw new Error('Frontend service failed to start');
      }
      await new Promise(resolve => setTimeout(resolve, retryDelay));
    }
  }
}

async function setupTestDatabase() {
  console.log('🗄️ Setting up test database with seed data...');
  
  try {
    // First login as admin to get session
    const loginResponse = await fetch('http://localhost:8000/api/admin/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: process.env.ADMIN_DEFAULT_USERNAME || 'admin',
        password: process.env.ADMIN_DEFAULT_PASSWORD || 'admin123456789'
      })
    });
    
    if (loginResponse.ok) {
      const cookies = loginResponse.headers.get('set-cookie');
      
      if (cookies) {
        // Reset database to clean state using authenticated session
        const resetResponse = await fetch('http://localhost:8000/api/admin/test/reset-database', {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Cookie': cookies 
          }
        });
        
        if (resetResponse.ok) {
          console.log('✅ Database reset completed');
        } else {
          console.log('⚠️ Database reset endpoint not available, using default seed');
        }
      }
    } else {
      console.log('⚠️ Could not authenticate for database reset');
    }
  } catch (error) {
    console.log('⚠️ Database reset endpoint not available, using default seed');
  }
}

export default globalSetup;