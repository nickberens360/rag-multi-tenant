import adminAPI from '@/services/api'

export class RoutingSettingsService {
  async getSettings() {
    return await adminAPI.getRoutingSettings()
  }

  async updateSettings(settings) {
    return await adminAPI.updateRoutingSettings(settings)
  }
}

export const routingSettingsService = new RoutingSettingsService()