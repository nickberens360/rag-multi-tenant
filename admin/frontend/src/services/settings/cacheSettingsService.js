import adminAPI from '@/services/api'

export class CacheSettingsService {
  async invalidateCache() {
    return await adminAPI.invalidateSettingsCache()
  }

  async getCacheStatus() {
    return await adminAPI.getSettingsCacheStatus()
  }
}

export const cacheSettingsService = new CacheSettingsService()