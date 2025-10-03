import adminAPI from '@/services/api'

export class CoreSettingsService {
  async getSettings() {
    return await adminAPI.getCoreSettings()
  }

  async updateSettings(settings) {
    return await adminAPI.updateCoreSettings(settings)
  }
}

export const coreSettingsService = new CoreSettingsService()