import adminAPI from '@/services/api'

export class FollowupSettingsService {
  async getSettings() {
    return await adminAPI.getFollowupSettings()
  }

  async updateSettings(settings) {
    return await adminAPI.updateFollowupSettings(settings)
  }

  async getCategories(includeInactive = true) {
    return await adminAPI.getFollowupCategories(includeInactive)
  }

  async createCategory(categoryData) {
    return await adminAPI.createFollowupCategory(categoryData)
  }

  async updateCategory(categoryId, categoryData) {
    return await adminAPI.updateFollowupCategory(categoryId, categoryData)
  }

  async deleteCategory(deleteRequest) {
    return await adminAPI.deleteFollowupCategoryWithStrategy(deleteRequest)
  }

  async getCategoryStats(categoryId) {
    return await adminAPI.getFollowupCategoryStats(categoryId)
  }

  async bulkUpdateCategories(operations) {
    return await Promise.all(operations.map(op => 
      this.updateCategory(op.id, op.data)
    ))
  }

  async resetSettings() {
    return await adminAPI.resetFollowupSettings()
  }

  async reorderCategories(categories) {
    return await adminAPI.reorderFollowupCategories(categories)
  }
}

export const followupSettingsService = new FollowupSettingsService()