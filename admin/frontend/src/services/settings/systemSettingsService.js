import adminAPI from '@/services/api'

export class SystemSettingsService {
  async getSettings() {
    return await adminAPI.getSystemConfigSettings()
  }

  async updateSettings(settings) {
    return await adminAPI.updateSystemConfigSettings(settings)
  }
}

export const systemSettingsService = new SystemSettingsService()