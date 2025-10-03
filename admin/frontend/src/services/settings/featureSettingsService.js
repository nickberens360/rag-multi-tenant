import adminAPI from '@/services/api'

export class FeatureSettingsService {
  async getFeatureFlags() {
    return await adminAPI.getFeatureFlags()
  }

  async updateFeatureFlags(flags) {
    return await adminAPI.updateFeatureFlags(flags)
  }
}

export const featureSettingsService = new FeatureSettingsService()