import { test as setup, expect } from '@playwright/test';

setup('authenticate via API', async ({ request, context }) => {
  // Authenticate via API instead of UI
  const response = await request.post('http://localhost:8000/api/admin/auth/login', {
    data: {
      username: 'admin',
      password: 'admin123456789'
    }
  });
  
  expect(response.ok()).toBeTruthy();
  
  // Extract cookies from response
  const cookies = response.headers()['set-cookie'];
  
  if (cookies) {
    // Parse and set cookies in context
    const sessionCookie = cookies.split(';')[0];
    await context.addCookies([{
      name: sessionCookie.split('=')[0],
      value: sessionCookie.split('=')[1],
      domain: 'localhost',
      path: '/'
    }]);
  }
  
  // Save the authentication state
  await context.storageState({ path: 'test-results/.auth/admin.json' });
});