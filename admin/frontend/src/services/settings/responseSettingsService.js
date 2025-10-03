import adminAPI from '@/services/api'

export class ResponseSettingsService {
  async getSettings() {
    return await adminAPI.getResponseSettings()
  }

  async updateSettings(settings) {
    return await adminAPI.updateResponseSettings(settings)
  }
}

export const responseSettingsService = new ResponseSettingsService()