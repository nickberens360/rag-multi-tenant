import adminAPI from '@/services/api'

export class UXSettingsService {
  async getSettings() {
    return await adminAPI.getUXSettings()
  }

  async updateSettings(settings) {
    return await adminAPI.updateUXSettings(settings)
  }
}

export const uxSettingsService = new UXSettingsService()