import adminAPI from '@/services/api'

export class SearchRetrievalSettingsService {
  async getSettings() {
    return await adminAPI.getSearchRetrievalSettings()
  }

  async updateSettings(settings) {
    return await adminAPI.updateSearchRetrievalSettings(settings)
  }
}

export const searchRetrievalSettingsService = new SearchRetrievalSettingsService()