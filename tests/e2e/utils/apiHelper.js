/**
 * API Helper for backend integration testing
 */
class ApiHelper {
  constructor(page) {
    this.page = page;
    this.baseURL = 'http://localhost:8000/admin';
    this.authenticated = false;
  }

  /**
   * Authenticate with the admin API
   */
  async authenticate(username = null, password = null) {
    if (this.authenticated) return;

    const user = username || process.env.ADMIN_DEFAULT_USERNAME || 'admin';
    const pass = password || process.env.ADMIN_DEFAULT_PASSWORD || 'admin123456789';

    const response = await this.page.request.post(`${this.baseURL}/auth/login`, {
      data: { username: user, password: pass }
    });

    if (!response.ok()) {
      throw new Error(`API Authentication failed: ${response.status()}`);
    }

    this.authenticated = true;
    return response;
  }

  /**
   * Make authenticated API request
   */
  async request(method, endpoint, data = null) {
    await this.authenticate();

    const options = {
      headers: {
        'Content-Type': 'application/json',
      }
    };

    if (data) {
      options.data = data;
    }

    const response = await this.page.request[method.toLowerCase()](`${this.baseURL}${endpoint}`, options);
    
    return {
      status: response.status(),
      ok: response.ok(),
      data: response.ok() ? await response.json().catch(() => ({})) : null,
      response
    };
  }

  // Settings API methods
  async getFollowupSettings() {
    return this.request('GET', '/settings/followup');
  }

  async updateFollowupSettings(settings) {
    return this.request('PUT', '/settings/followup', settings);
  }

  async resetFollowupSettings() {
    return this.request('POST', '/settings/followup/reset');
  }

  // Category API methods
  async getCategories(includeInactive = true) {
    return this.request('GET', `/settings/followup/categories?include_inactive=${includeInactive}`);
  }

  async createCategory(categoryData) {
    return this.request('POST', '/settings/followup/categories', categoryData);
  }

  async updateCategory(categoryId, updates) {
    return this.request('PUT', `/settings/followup/categories/${categoryId}`, updates);
  }

  async deleteCategory(categoryId, strategy = 'delete', targetCategoryId = null) {
    const data = { strategy };
    if (targetCategoryId) {
      data.target_category_id = targetCategoryId;
    }
    return this.request('POST', `/settings/followup/categories/${categoryId}/delete`, data);
  }

  async getCategoryStats(categoryId) {
    return this.request('GET', `/settings/followup/categories/${categoryId}/stats`);
  }

  // Question API methods
  async getQuestions(filters = {}) {
    const params = new URLSearchParams(filters).toString();
    const endpoint = `/settings/followup/questions${params ? '?' + params : ''}`;
    return this.request('GET', endpoint);
  }

  async createQuestion(questionData) {
    return this.request('POST', '/settings/followup/questions', questionData);
  }

  async updateQuestion(questionId, updates) {
    return this.request('PUT', `/settings/followup/questions/${questionId}`, updates);
  }

  async deleteQuestion(questionId) {
    return this.request('DELETE', `/settings/followup/questions/${questionId}`);
  }

  async bulkUpdateQuestions(operations) {
    return this.request('POST', '/settings/followup/questions/bulk', { operations });
  }

  // Health and status methods
  async getHealth() {
    return this.request('GET', '/health');
  }

  async getOverviewStats(days = 7) {
    return this.request('GET', `/stats/overview?days=${days}`);
  }

  // Validation helpers
  async waitForCategoryToExist(categoryName, timeout = 10000) {
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeout) {
      const result = await this.getCategories();
      if (result.ok && result.data) {
        const category = result.data.find(c => c.name === categoryName || c.display_name === categoryName);
        if (category) {
          return category;
        }
      }
      
      await new Promise(resolve => setTimeout(resolve, 500));
    }
    
    throw new Error(`Category "${categoryName}" not found within ${timeout}ms`);
  }

  async waitForQuestionCount(categoryId, expectedCount, timeout = 10000) {
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeout) {
      const result = await this.getQuestions({ category_id: categoryId });
      if (result.ok && result.data && result.data.length === expectedCount) {
        return result.data;
      }
      
      await new Promise(resolve => setTimeout(resolve, 500));
    }
    
    throw new Error(`Expected ${expectedCount} questions, timeout after ${timeout}ms`);
  }

  // Test helpers
  async cleanupTestData() {
    console.log('🧹 API: Cleaning up test data...');
    
    try {
      const categoriesResult = await this.getCategories();
      if (categoriesResult.ok && categoriesResult.data) {
        const testCategories = categoriesResult.data.filter(c => 
          c.name?.match(/^(test_|bulk_|perf_)/) || 
          c.display_name?.includes('Test') ||
          c.display_name?.includes('Bulk') ||
          c.display_name?.includes('Performance')
        );
        
        for (const category of testCategories) {
          await this.deleteCategory(category.id, 'delete');
          console.log(`API: Deleted test category: ${category.display_name}`);
        }
      }
      
      console.log('✅ API: Test data cleanup completed');
    } catch (error) {
      console.warn('⚠️ API: Error during cleanup:', error.message);
    }
  }

  async verifyDatabaseIntegrity() {
    console.log('🔍 API: Verifying database integrity...');
    
    try {
      // Check that categories and questions are properly linked
      const categoriesResult = await this.getCategories();
      const questionsResult = await this.getQuestions();
      
      if (!categoriesResult.ok || !questionsResult.ok) {
        throw new Error('Failed to fetch categories or questions');
      }
      
      const categories = categoriesResult.data || [];
      const questions = questionsResult.data || [];
      
      // Verify all questions have valid category_id
      const categoryIds = new Set(categories.map(c => c.id));
      const orphanedQuestions = questions.filter(q => !categoryIds.has(q.category_id));
      
      if (orphanedQuestions.length > 0) {
        console.warn(`⚠️ Found ${orphanedQuestions.length} orphaned questions`);
      }
      
      // Verify categories have expected structure
      for (const category of categories) {
        if (!category.id || !category.name || !category.display_name) {
          throw new Error(`Invalid category structure: ${JSON.stringify(category)}`);
        }
      }
      
      console.log(`✅ API: Database integrity verified - ${categories.length} categories, ${questions.length} questions`);
      return true;
    } catch (error) {
      console.error('❌ API: Database integrity check failed:', error.message);
      return false;
    }
  }

  // Performance measurement
  async measureApiPerformance(operation, ...args) {
    const startTime = Date.now();
    const result = await this[operation](...args);
    const endTime = Date.now();
    
    return {
      ...result,
      responseTime: endTime - startTime
    };
  }

  // Batch operations for efficiency
  async createBatchCategories(categoriesData) {
    const results = [];
    
    for (const categoryData of categoriesData) {
      try {
        const result = await this.createCategory(categoryData);
        results.push(result);
        
        // Small delay to prevent overwhelming the server
        await new Promise(resolve => setTimeout(resolve, 50));
      } catch (error) {
        results.push({ ok: false, error: error.message });
      }
    }
    
    return results;
  }

  async createBatchQuestions(questionsData) {
    const results = [];
    
    for (const questionData of questionsData) {
      try {
        const result = await this.createQuestion(questionData);
        results.push(result);
        
        // Small delay to prevent overwhelming the server
        await new Promise(resolve => setTimeout(resolve, 25));
      } catch (error) {
        results.push({ ok: false, error: error.message });
      }
    }
    
    return results;
  }
}

export default ApiHelper;