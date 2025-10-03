import { testCategories, testSettings, scenarios } from './testData.js';

class DatabaseSeeder {
  constructor(page) {
    this.page = page;
    this.baseURL = 'http://localhost:8000/admin';
  }

  /**
   * Authenticate and get session cookie for API calls
   */
  async authenticate() {
    const username = process.env.ADMIN_DEFAULT_USERNAME || 'admin';
    const password = process.env.ADMIN_DEFAULT_PASSWORD || 'admin123456789';
    
    const response = await this.page.request.post(`${this.baseURL}/auth/login`, {
      data: { username, password }
    });
    
    if (!response.ok()) {
      throw new Error(`Authentication failed: ${response.status()}`);
    }
    
    return response;
  }

  /**
   * Clear all test data from the database
   */
  async clearTestData() {
    console.log('🧹 Clearing existing test data...');
    
    try {
      await this.authenticate();
      
      // Get all categories
      const categoriesResponse = await this.page.request.get(
        `${this.baseURL}/settings/followup/categories?include_inactive=true`
      );
      
      if (categoriesResponse.ok()) {
        const categories = await categoriesResponse.json();
        
        // Delete test categories (those starting with 'test_' or 'bulk_' or 'perf_')
        for (const category of categories) {
          if (category.name?.match(/^(test_|bulk_|perf_)/)) {
            console.log(`Deleting test category: ${category.name}`);
            await this.page.request.post(
              `${this.baseURL}/settings/followup/categories/${category.id}/delete`,
              {
                data: { strategy: 'delete' }
              }
            );
          }
        }
      }
      
      console.log('✅ Test data cleared');
    } catch (error) {
      console.warn('⚠️ Could not clear test data:', error.message);
    }
  }

  /**
   * Seed the database with basic test data
   */
  async seedBasicData() {
    console.log('🌱 Seeding basic test data...');
    
    try {
      await this.authenticate();
      
      // Create test categories with questions
      for (const categoryData of testCategories) {
        const categoryResponse = await this.page.request.post(
          `${this.baseURL}/settings/followup/categories`,
          {
            data: {
              name: categoryData.name,
              display_name: categoryData.displayName,
              description: categoryData.description,
              icon: categoryData.icon,
              sort_order: categoryData.sortOrder
            }
          }
        );
        
        if (categoryResponse.ok()) {
          const category = await categoryResponse.json();
          console.log(`Created category: ${category.display_name}`);
          
          // Add questions to the category
          for (let i = 0; i < categoryData.questions.length; i++) {
            const questionText = categoryData.questions[i];
            await this.page.request.post(
              `${this.baseURL}/settings/followup/questions`,
              {
                data: {
                  category_id: category.id,
                  question_text: questionText,
                  sort_order: i
                }
              }
            );
          }
          
          console.log(`Added ${categoryData.questions.length} questions to ${category.display_name}`);
        }
      }
      
      // Update followup settings
      await this.page.request.put(`${this.baseURL}/settings/followup`, {
        data: testSettings
      });
      
      console.log('✅ Basic test data seeded');
    } catch (error) {
      console.error('❌ Error seeding basic data:', error.message);
      throw error;
    }
  }

  /**
   * Seed data for bulk operations testing
   */
  async seedBulkTestData() {
    console.log('🌱 Seeding bulk test data...');
    
    try {
      await this.authenticate();
      
      for (const categoryData of scenarios.bulkCategories) {
        const response = await this.page.request.post(
          `${this.baseURL}/settings/followup/categories`,
          {
            data: {
              name: categoryData.name,
              display_name: categoryData.displayName,
              description: categoryData.description
            }
          }
        );
        
        if (response.ok()) {
          console.log(`Created bulk test category: ${categoryData.displayName}`);
        }
      }
      
      console.log('✅ Bulk test data seeded');
    } catch (error) {
      console.error('❌ Error seeding bulk data:', error.message);
      throw error;
    }
  }

  /**
   * Seed performance test data
   */
  async seedPerformanceData() {
    console.log('🚀 Seeding performance test data...');
    
    const { performanceData } = require('./testData');
    
    try {
      await this.authenticate();
      
      // Create category with many questions
      const categoryResponse = await this.page.request.post(
        `${this.baseURL}/settings/followup/categories`,
        {
          data: {
            name: performanceData.largeCategory.name,
            display_name: performanceData.largeCategory.displayName,
            description: performanceData.largeCategory.description
          }
        }
      );
      
      if (categoryResponse.ok()) {
        const category = await categoryResponse.json();
        
        // Add many questions
        for (let i = 0; i < performanceData.largeCategory.questions.length; i++) {
          await this.page.request.post(
            `${this.baseURL}/settings/followup/questions`,
            {
              data: {
                category_id: category.id,
                question_text: performanceData.largeCategory.questions[i],
                sort_order: i
              }
            }
          );
          
          // Add small delay to avoid overwhelming the server
          if (i % 10 === 0) {
            await new Promise(resolve => setTimeout(resolve, 100));
          }
        }
        
        console.log(`Created performance category with ${performanceData.largeCategory.questions.length} questions`);
      }
      
      console.log('✅ Performance test data seeded');
    } catch (error) {
      console.error('❌ Error seeding performance data:', error.message);
      throw error;
    }
  }

  /**
   * Reset database to a clean state and seed with fresh data
   */
  async resetAndSeed() {
    await this.clearTestData();
    await this.seedBasicData();
  }

  /**
   * Verify seeded data exists
   */
  async verifySeededData() {
    try {
      await this.authenticate();
      
      const response = await this.page.request.get(
        `${this.baseURL}/settings/followup/categories`
      );
      
      if (response.ok()) {
        const categories = await response.json();
        const testCategoryCount = categories.filter(c => c.name?.startsWith('test_')).length;
        
        console.log(`✅ Verified ${testCategoryCount} test categories exist`);
        return testCategoryCount >= testCategories.length;
      }
      
      return false;
    } catch (error) {
      console.error('❌ Error verifying seeded data:', error.message);
      return false;
    }
  }

  /**
   * Get current database state for assertions
   */
  async getDatabaseState() {
    try {
      await this.authenticate();
      
      const [categoriesResponse, questionsResponse, settingsResponse] = await Promise.all([
        this.page.request.get(`${this.baseURL}/settings/followup/categories?include_inactive=true`),
        this.page.request.get(`${this.baseURL}/settings/followup/questions`),
        this.page.request.get(`${this.baseURL}/settings/followup`)
      ]);
      
      const state = {};
      
      if (categoriesResponse.ok()) {
        state.categories = await categoriesResponse.json();
      }
      
      if (questionsResponse.ok()) {
        state.questions = await questionsResponse.json();
      }
      
      if (settingsResponse.ok()) {
        state.settings = await settingsResponse.json();
      }
      
      return state;
    } catch (error) {
      console.error('❌ Error getting database state:', error.message);
      return {};
    }
  }
}

export default DatabaseSeeder;