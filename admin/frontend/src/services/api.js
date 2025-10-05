import axios from 'axios'

class AdminAPI {
  constructor() {
    // Store current tenant for URL construction
    this.currentTenant = null

    // Resolve base URL from env, falling back to same-origin admin API
    const DEFAULT_BASE_URL = '/api/admin'
    // Prefer explicit VITE_API_BASE_URL if provided (even in dev) to bypass proxy issues
    // Otherwise, use same-origin '/api/admin' which works with Vite dev proxy
    this.baseURL = import.meta.env.VITE_API_BASE_URL || DEFAULT_BASE_URL

    this.client = axios.create({
      // baseURL will be set dynamically
      timeout: 15000,
      headers: { 'Content-Type': 'application/json' },
      withCredentials: true  // Enable cookies for session management
    })

    // Authentication is now handled via HTTPOnly cookies
    // No longer storing tokens in localStorage for security

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        // Build base origin
        let originBase = ''
        if (import.meta.env.DEV) {
          // In dev, always call backend directly to avoid Vite proxy mismatches with tenant prefixes
          originBase = 'http://localhost:8001'
        } else if (import.meta.env.VITE_API_BASE_URL) {
          // In prod, accept absolute or relative; strip trailing /api/admin if present
          const base = String(import.meta.env.VITE_API_BASE_URL)
          const abs = /^https?:\/\//i.test(base)
          originBase = abs ? base : ''
          originBase = originBase
            .replace(/\/api\/admin\/?$/, '')
            .replace(/\/$/, '')
        } else {
          originBase = ''
        }

        // Compute tenant-aware admin base path
        const adminPath = '/api/admin'
        // Prioritize explicit tenant context over URL path to handle tenant switches
        // The URL path may be stale during navigation, but this.currentTenant is always current
        let pathTenant = null
        try {
          if (typeof window !== 'undefined' && window.location && window.location.pathname) {
            const m = window.location.pathname.match(/^\/([^/]+)/)
            const seg = m && m[1]
            if (seg && !['api', 'admin', 'login'].includes(seg)) {
              pathTenant = seg
            }
          }
        } catch (_) { /* noop */ }
        // IMPORTANT: Use currentTenant first, then fall back to pathTenant
        const tenantSlug = this.currentTenant || pathTenant || ''
        const urlPath = String(config.url || '')
        // Routers that are NOT mounted under `/{tenant}/api/admin` must avoid tenant prefix
        // NOTE: /auth endpoints SHOULD include tenant prefix for tenant-scoped operations (e.g., user creation)
        const noTenantPrefix = urlPath.startsWith('/tenants') || urlPath.startsWith('/invitations')
        const tenantPrefix = !noTenantPrefix && tenantSlug ? `/${tenantSlug}` : ''
        config.baseURL = `${originBase}${tenantPrefix}${adminPath}`

        // Enhanced logging for debugging
        console.debug(`API ${config.method?.toUpperCase()}: ${config.baseURL}${config.url}`)

        // Session-based authentication - HTTPOnly cookies are automatically sent with withCredentials: true
        return config
      },
      (error) => {
        if (import.meta.env.DEV) {
          console.error('Request error:', error)
        }
        return Promise.reject(error)
      }
    )

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => {
        return response.data
      },
      (error) => {
        // Don't log expected 401 errors for auth endpoints (like /auth/me checks)
        const isAuthEndpoint = error.config?.url?.includes('/auth/')
        const is401 = error.response?.status === 401
        
        if (import.meta.env.DEV && !(isAuthEndpoint && is401)) {
          console.error('API Error:', error.response?.data || error.message)
        }
        
        // Handle common error cases
        if (error.response?.status === 401) {
          // SECURITY FIX: Better authentication state management
          if (import.meta.env.DEV && !isAuthEndpoint) {
            console.debug('Unauthorized access - authentication required')
          }
          
          // Only trigger logout and redirect for non-auth endpoint 401s
          if (!isAuthEndpoint) {
            this.handleAuthenticationError()
          }
        } else if (error.response?.status === 404) {
          if (import.meta.env.DEV) {
            console.error('API endpoint not found')
          }
        } else if (error.response?.status >= 500) {
          console.error('Server error')
        }
        
        return Promise.reject(error)
      }
    )
  }

  // Stats endpoints
  async getStats(days = 7) {
    const params = new URLSearchParams({ days: days.toString() })

    return await this.client.get(`/stats/overview?${params.toString()}`)
  }

  async getSystemHealth() {
    return await this.client.get('/health')
  }

  // Query endpoints
  async getQueries(params = {}) {
    const searchParams = new URLSearchParams()

    // Convert page to offset
    if (params.page && params.limit) {
      const offset = (params.page - 1) * params.limit
      searchParams.append('offset', offset)
    }
    if (params.limit) searchParams.append('limit', params.limit)
    if (params.search) searchParams.append('search', params.search)
    if (params.startDate) searchParams.append('start_date', params.startDate)
    if (params.endDate) searchParams.append('end_date', params.endDate)
    if (params.errorOnly) searchParams.append('errors_only', params.errorOnly)
    if (params.minRelevance) searchParams.append('min_relevance', params.minRelevance)
    if (params.sortBy) searchParams.append('sort_by', params.sortBy)
    if (params.sortOrder) searchParams.append('sort_order', params.sortOrder)

    // Note: Tenant filtering is handled via URL path prefix (/{tenant}/api/admin/queries)
    // not via query parameter, so we don't add it here

    return await this.client.get(`/queries?${searchParams.toString()}`)
  }

  async getQuery(id) {
    return await this.client.get(`/queries/${id}`)
  }

  async updateQueryFeedback(id, feedback) {
    return await this.client.post(`/queries/${id}/feedback`, { feedback })
  }

  async getQueryInsights() {
    return await this.client.get('/queries/insights')
  }

  // Performance endpoints
  async getPerformanceMetrics(timeRange = '24h') {
    return await this.client.get(`/performance/metrics?time_range=${timeRange}`)
  }

  async getPerformanceTimeline(days = 7, interval = 'hour') {
    return await this.client.get(`/performance/timeline?days=${days}&interval=${interval}`)
  }

  async getResponseTimePercentiles(timeRange = '24h') {
    return await this.client.get(`/performance/percentiles?time_range=${timeRange}`)
  }

  // Content endpoints
  async getContentGaps(params = {}) {
    const { resolved = false, limit = 50 } = params
    return await this.client.get(`/content/gaps?resolved=${resolved}&limit=${limit}`)
  }

  async updateContentGap(gapId, data) {
    const params = new URLSearchParams()
    if (data.resolved !== undefined) params.append('resolved', data.resolved)
    if (data.notes !== undefined) params.append('notes', data.notes)
    return await this.client.patch(`/content/gaps/${gapId}?${params}`)
  }

  async getPopularTopics(timeRange = '7d') {
    return await this.client.get(`/content/popular-topics?time_range=${timeRange}`)
  }

  async getSourceUsage() {
    return await this.client.get('/content/sources')
  }

  // Legacy method for backward compatibility
  async markGapResolved(gapId) {
    return this.updateContentGap(gapId, { resolved: true })
  }

  // Session endpoints
  async getSessions(params = {}) {
    const searchParams = new URLSearchParams()
    
    if (params.page) searchParams.append('page', params.page)
    if (params.limit) searchParams.append('limit', params.limit)
    if (params.active) searchParams.append('active', params.active)
    if (params.startDate) searchParams.append('start_date', params.startDate)
    if (params.endDate) searchParams.append('end_date', params.endDate)

    return await this.client.get(`/sessions?${searchParams.toString()}`)
  }

  async getSessionDetails(sessionId) {
    return await this.client.get(`/sessions/${sessionId}`)
  }

  async getSessionAnalytics() {
    return await this.client.get('/sessions/analytics')
  }

  // Export endpoints
  async exportQueries(params = {}) {
    const searchParams = new URLSearchParams()
    
    if (params.format) searchParams.append('format', params.format)
    if (params.startDate) searchParams.append('start_date', params.startDate)
    if (params.endDate) searchParams.append('end_date', params.endDate)
    if (params.includeResponses) searchParams.append('include_responses', params.includeResponses)

    const response = await this.client.get(`/export/queries?${searchParams.toString()}`, {
      responseType: 'blob'
    })
    
    return response
  }

  async exportPerformanceReport(timeRange = '7d') {
    const response = await this.client.get(`/export/performance?time_range=${timeRange}`, {
      responseType: 'blob'
    })
    
    return response
  }

  // Knowledge base endpoints (available on both public and admin APIs)
  async getKnowledgeStats() {
    return await this.client.get('/knowledge/stats')
  }

  async getKnowledgeDocuments(limit = 100, offset = 0) {
    return await this.client.get(`/knowledge/documents?limit=${limit}&offset=${offset}`)
  }

  async getKnowledgeSources() {
    return await this.client.get('/knowledge/sources')
  }

  async getDocumentContent(documentId) {
    return await this.client.get(`/knowledge/documents/${documentId}`)
  }

  async getKnowledgeFileContent(filename) {
    return await this.client.get(`/knowledge/files/${encodeURIComponent(filename)}/content`)
  }

  async uploadKnowledgeFiles(formData, options = {}) {
    // Supports new tenant-scoped upload endpoint with optional immediate indexing
    const { indexNow = true } = options || {}
    try {
      // Avoid duplicating field if already present
      if (!(formData instanceof FormData) || !formData.has) {
        // In unusual cases (tests), formData may be a plain object
      } else if (!formData.has('index_now')) {
        formData.append('index_now', indexNow ? 'true' : 'false')
      }
    } catch (_) {
      // Non-fatal; proceed without index_now
    }
    return await this.client.post('/knowledge/uploads', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  }

  async getUploadStatus({ limit = 50, offset = 0, status = null } = {}) {
    const params = new URLSearchParams()
    params.append('limit', String(limit))
    params.append('offset', String(offset))
    if (status) params.append('status', status)
    return await this.client.get(`/knowledge/uploads/status?${params.toString()}`)
  }

  async deleteUpload(fileId) {
    return await this.client.delete(`/knowledge/uploads/${encodeURIComponent(fileId)}`)
  }

  async getKnowledgeFiles() {
    return await this.client.get('/knowledge/files')
  }

  async deleteKnowledgeFile(filename) {
    return await this.client.delete(`/knowledge/files/${encodeURIComponent(filename)}`)
  }

  // Knowledge consistency (admin)
  async getKnowledgeConsistency(sample = 50) {
    return await this.client.get(`/knowledge/consistency?sample=${sample}`)
  }

  async reconcileKnowledge(options = {}) {
    const payload = {
      dry_run: options.dryRun !== undefined ? options.dryRun : true,
      allow_deletes: Boolean(options.allowDeletes),
      limit: options.limit,
      paths: options.paths,
    }
    return await this.client.post('/knowledge/reconcile', payload, { timeout: 120000 })
  }

  async getKnowledgeFilesStatus(params = {}) {
    const searchParams = new URLSearchParams()
    if (params.status) searchParams.append('status', params.status)
    // Backend validation caps limit at 1000; clamp client value to avoid 422
    const limit = Math.min(params.limit ?? 200, 1000)
    searchParams.append('limit', limit)
    if (params.offset) searchParams.append('offset', params.offset)
    const qs = searchParams.toString()
    return await this.client.get(`/knowledge/files/status${qs ? `?${qs}` : ''}`)
  }

  async reindexKnowledgeFile(path) {
    return await this.client.post('/knowledge/reindex-file', { path })
  }

  // Knowledge settings
  async getKnowledgeSettings() {
    return await this.client.get('/settings/knowledge')
  }

  async updateKnowledgeSettings(data) {
    return await this.client.put('/settings/knowledge', data)
  }

  async getKnowledgeConsistencyList(kind, { offset = 0, limit = 50 } = {}) {
    const searchParams = new URLSearchParams()
    searchParams.append('kind', kind)
    searchParams.append('offset', offset)
    searchParams.append('limit', limit)
    return await this.client.get(`/knowledge/consistency/list?${searchParams.toString()}`)
  }

  async getKnowledgeHealth() {
    return await this.client.get('/knowledge/health')
  }

  async refreshKnowledgeBase(forceReindex = true) {
    return await this.client.post('/refresh', {
      force_reindex: forceReindex
    })
  }

  async getRefreshStatus() {
    return await this.client.get('/refresh/status')
  }


  async updateKnowledgeFileContent(filename, content) {
    return await this.client.put(`/knowledge/files/${encodeURIComponent(filename)}/content`, {
      content: content
    }, {
      timeout: 30000  // 30 second timeout for file saves with re-indexing
    })
  }

  async updateKnowledgeSource(sourcePath, updateData) {
    return await this.client.put(`/knowledge/sources/${encodeURIComponent(sourcePath)}`, updateData)
  }

  async deleteKnowledgeSource(sourcePath) {
    return await this.client.delete(`/knowledge/sources/${encodeURIComponent(sourcePath)}`)
  }

  // Authentication endpoints
  async login(username, password) {
    try {
      const response = await this.client.post('/auth/login', {
        username,
        password
      })
      
      // Session is now managed via HTTPOnly cookies
      // No need to store session_id manually
      
      return response
    } catch (error) {
      console.error('Login failed:', error)
      throw error
    }
  }

  async logout() {
    try {
      const response = await this.client.post('/auth/logout')
      // HTTPOnly cookie will be cleared by the server
      return response
    } catch (error) {
      console.error('Logout failed:', error)
      // Cookie should still be cleared by server even if logout fails
      throw error
    }
  }

  // SECURITY FIX: Handle authentication errors properly
  handleAuthenticationError() {
    if (import.meta.env.DEV) {
      console.debug('Handling authentication error - clearing auth state')
    }
    
    // Instead of redirecting immediately, let the router handle navigation
    // This prevents redirect loops
    if (typeof window !== 'undefined' && window.location) {
      // Only redirect if we're not already on login page
      if (!window.location.pathname.includes('/login')) {
        // Use a more controlled redirect to login
        window.location.href = '/login'
      }
    }
  }

  async getCurrentUser() {
    try {
      return await this.client.get('/auth/me')
    } catch (error) {
      // Don't log 401 errors as they're expected when not authenticated
      if (error.response?.status !== 401 && import.meta.env.DEV) {
        console.error('Failed to get current user:', error)
      }
      throw error
    }
  }

  async createUser(userData) {
    try {
      return await this.client.post('/auth/create-user', userData)
    } catch (error) {
      console.error('Failed to create user:', error)
      throw error
    }
  }

  async changePassword(currentPassword, newPassword) {
    try {
      return await this.client.post('/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword
      })
    } catch (error) {
      console.error('Failed to change password:', error)
      throw error
    }
  }

  // Settings API methods
  async getFollowupSettings() {
    try {
      const response = await this.client.get('/settings/followup')
      return response
    } catch (error) {
      console.error('Failed to get follow-up settings:', error)
      throw error
    }
  }

  async updateFollowupSettings(settings) {
    try {
      const response = await this.client.put('/settings/followup', settings)
      return response
    } catch (error) {
      console.error('Failed to update follow-up settings:', error)
      throw error
    }
  }

  async resetFollowupSettings() {
    try {
      const response = await this.client.post('/settings/followup/reset')
      return response
    } catch (error) {
      console.error('Failed to reset follow-up settings:', error)
      throw error
    }
  }

  // New settings API methods for the hybrid configuration system
  async getResponseSettings() {
    try {
      const response = await this.client.get('/settings/response')
      return response
    } catch (error) {
      console.error('Failed to get response settings:', error)
      throw error
    }
  }

  async updateResponseSettings(settings) {
    try {
      const response = await this.client.put('/settings/response', settings)
      return response
    } catch (error) {
      console.error('Failed to update response settings:', error)
      throw error
    }
  }

  async getRoutingSettings() {
    try {
      const response = await this.client.get('/settings/routing')
      return response
    } catch (error) {
      console.error('Failed to get routing settings:', error)
      throw error
    }
  }

  async updateRoutingSettings(settings) {
    try {
      const response = await this.client.put('/settings/routing', settings)
      return response
    } catch (error) {
      console.error('Failed to update routing settings:', error)
      throw error
    }
  }

  async getFeatureFlags() {
    try {
      const response = await this.client.get('/settings/features')
      return response
    } catch (error) {
      console.error('Failed to get feature flags:', error)
      throw error
    }
  }

  async updateFeatureFlags(settings) {
    try {
      const response = await this.client.put('/settings/features', settings)
      return response
    } catch (error) {
      console.error('Failed to update feature flags:', error)
      throw error
    }
  }

  async getSettingsCacheStatus() {
    try {
      const response = await this.client.get('/settings/cache/status')
      return response
    } catch (error) {
      console.error('Failed to get settings cache status:', error)
      throw error
    }
  }

  async invalidateSettingsCache() {
    try {
      const response = await this.client.post('/settings/cache/invalidate')
      return response
    } catch (error) {
      console.error('Failed to invalidate settings cache:', error)
      throw error
    }
  }

  // Diagnostics endpoints
  async getDiagnosticsConfigStatus() {
    return await this.client.get('/diagnostics/config-status')
  }

  async getDiagnosticsValidation() {
    return await this.client.get('/diagnostics/config-validation')
  }

  async getDiagnosticsCriticalCheck() {
    // Returns { status: 'healthy'|'warning'|'critical', critical_missing: [], ... }
    return await this.client.get('/diagnostics/critical-settings-check')
  }


  async resetFollowupQuestions() {
    try {
      const response = await this.client.post('/settings/followup/questions/reset')
      return response
    } catch (error) {
      console.error('Failed to reset follow-up questions:', error)
      throw error
    }
  }


  async reorderFollowupCategories(categories) {
    try {
      const response = await this.client.post('/settings/followup/categories/reorder', { categories })
      return response
    } catch (error) {
      console.error('Failed to reorder follow-up categories:', error)
      throw error
    }
  }

  // Enhanced category management with stats
  async getCategoriesWithStats(includeInactive = false) {
    try {
      const response = await this.client.get(`/settings/followup/categories/with-stats?include_inactive=${includeInactive}`)
      return response
    } catch (error) {
      console.error('Failed to get categories with stats:', error)
      throw error
    }
  }

  async validateCategoryDeletion(categoryId) {
    try {
      const response = await this.client.get(`/settings/followup/categories/${categoryId}/validate-deletion`)
      return response
    } catch (error) {
      console.error('Failed to validate category deletion:', error)
      throw error
    }
  }

  async deleteCategoryWithStrategy(categoryId, strategy, targetCategoryId = null) {
    try {
      const response = await this.client.post(`/settings/followup/categories/${categoryId}/delete`, {
        strategy,
        target_category_id: targetCategoryId
      })
      return response
    } catch (error) {
      console.error('Failed to delete category with strategy:', error)
      throw error
    }
  }

  // New normalized question management
  async getFollowupQuestions(params = {}) {
    try {
      const searchParams = new URLSearchParams()
      if (params.category_id) searchParams.append('category_id', params.category_id)
      if (params.active_only !== undefined) searchParams.append('active_only', params.active_only)
      if (params.search) searchParams.append('search', params.search)
      if (params.limit) searchParams.append('limit', params.limit)
      if (params.offset) searchParams.append('offset', params.offset)

      const response = await this.client.get(`/settings/followup/questions?${searchParams}`)
      return response
    } catch (error) {
      console.error('Failed to get followup questions:', error)
      throw error
    }
  }

  async getFollowupQuestion(questionId) {
    try {
      const response = await this.client.get(`/settings/followup/questions/${questionId}`)
      return response
    } catch (error) {
      console.error('Failed to get followup question:', error)
      throw error
    }
  }

  async createFollowupQuestion(questionData) {
    try {
      const response = await this.client.post('/settings/followup/questions', questionData)
      return response
    } catch (error) {
      console.error('Failed to create followup question:', error)
      throw error
    }
  }

  async updateFollowupQuestion(questionId, questionData) {
    try {
      const response = await this.client.put(`/settings/followup/questions/${questionId}`, questionData)
      return response
    } catch (error) {
      console.error('Failed to update followup question:', error)
      throw error
    }
  }

  async deleteFollowupQuestion(questionId) {
    try {
      const response = await this.client.delete(`/settings/followup/questions/${questionId}`)
      return response
    } catch (error) {
      console.error('Failed to delete followup question:', error)
      throw error
    }
  }

  async bulkUpdateQuestions(operations) {
    try {
      const response = await this.client.post('/settings/followup/questions/bulk', { operations })
      return response
    } catch (error) {
      console.error('Failed to bulk update questions:', error)
      throw error
    }
  }

  async searchFollowupQuestions(query, categoryId = null, limit = 20) {
    try {
      const searchParams = new URLSearchParams()
      searchParams.append('query', query)
      if (categoryId) searchParams.append('category_id', categoryId)
      searchParams.append('limit', limit)

      const response = await this.client.get(`/settings/followup/questions/search?${searchParams}`)
      return response
    } catch (error) {
      console.error('Failed to search followup questions:', error)
      throw error
    }
  }

  // Additional normalized API methods for the unified interface
  async getFollowupCategories(includeInactive = true) {
    try {
      const response = await this.client.get(`/settings/followup/categories?include_inactive=${includeInactive}`)
      return response
    } catch (error) {
      console.error('Failed to get followup categories normalized:', error)
      throw error
    }
  }

  async createFollowupCategory(categoryData) {
    try {
      const response = await this.client.post('/settings/followup/categories', categoryData)
      return response
    } catch (error) {
      console.error('Failed to create followup category normalized:', error)
      throw error
    }
  }

  async updateFollowupCategory(categoryId, categoryData) {
    try {
      const response = await this.client.put(`/settings/followup/categories/${categoryId}`, categoryData)
      return response
    } catch (error) {
      console.error('Failed to update followup category normalized:', error)
      throw error
    }
  }

  async deleteFollowupCategoryWithStrategy(deleteRequest) {
    try {
      const response = await this.client.post(`/settings/followup/categories/${deleteRequest.categoryId}/delete`, {
        strategy: deleteRequest.strategy,
        target_category_id: deleteRequest.targetCategoryId
      })
      return response
    } catch (error) {
      console.error('Failed to delete followup category with strategy:', error)
      throw error
    }
  }

  // Backward-compatible alias used by some views
  async deleteFollowupCategoryWithStrategyNormalized(deleteRequest) {
    return this.deleteFollowupCategoryWithStrategy(deleteRequest)
  }

  async getFollowupCategoryStats(categoryId) {
    try {
      const response = await this.client.get(`/settings/followup/categories/${categoryId}/stats`)
      return response
    } catch (error) {
      console.error('Failed to get followup category stats:', error)
      // Return default stats instead of throwing to prevent UI breaking
      return { question_count: 0, active_questions: 0 }
    }
  }

  async getFollowupCategoryStatsNormalized(categoryId) {
    try {
      const response = await this.client.get(`/settings/followup/categories/${categoryId}/stats`)
      return response
    } catch (error) {
      console.error('Failed to get followup category stats normalized:', error)
      // Return default stats instead of throwing to prevent UI breaking
      return { question_count: 0, active_questions: 0 }
    }
  }

  // Utility methods
  async testConnection() {
    try {
      await this.client.get('/health')
      return true
    } catch (error) {
      return false
    }
  }

  // Welcome Questions API methods
  async getWelcomeQuestions(activeOnly = false) {
    try {
      const response = await this.client.get(`/settings/welcome/questions?active_only=${activeOnly}`)
      return response
    } catch (error) {
      console.error('Failed to get welcome questions:', error)
      throw error
    }
  }

  async createWelcomeQuestion(questionData) {
    try {
      const response = await this.client.post('/settings/welcome/questions', questionData)
      return response
    } catch (error) {
      console.error('Failed to create welcome question:', error)
      throw error
    }
  }

  async updateWelcomeQuestion(questionId, questionData) {
    try {
      const response = await this.client.put(`/settings/welcome/questions/${questionId}`, questionData)
      return response
    } catch (error) {
      console.error('Failed to update welcome question:', error)
      throw error
    }
  }

  async deleteWelcomeQuestion(questionId) {
    try {
      const response = await this.client.delete(`/settings/welcome/questions/${questionId}`)
      return response
    } catch (error) {
      console.error('Failed to delete welcome question:', error)
      throw error
    }
  }

  // Tenant context management
  setCurrentTenant(tenantSlug) {
    this.currentTenant = tenantSlug
    console.debug(`API tenant context set to: ${tenantSlug || 'none'}`)
  }

  getCurrentTenant() {
    return this.currentTenant
  }

  formatError(error) {
    if (error.response?.data?.detail) {
      return error.response.data.detail
    } else if (error.response?.data?.message) {
      return error.response.data.message
    } else if (error.message) {
      return error.message
    } else {
      return 'An unknown error occurred'
    }
  }

  // API Key Management endpoints
  async getApiKeys(includeInactive = false) {
    return await this.client.get(`/settings/api-keys?include_inactive=${includeInactive}`)
  }

  async createApiKey(keyData) {
    return await this.client.post('/settings/api-keys', keyData)
  }

  async updateApiKey(keyName, keyData) {
    return await this.client.put(`/settings/api-keys/${keyName}`, keyData)
  }

  async toggleApiKey(keyName, isActive) {
    return await this.client.post(`/settings/api-keys/${keyName}/toggle`, { is_active: isActive })
  }

  async deleteApiKey(keyName) {
    return await this.client.delete(`/settings/api-keys/${keyName}`)
  }

  async validateApiKey(keyName) {
    return await this.client.post(`/settings/api-keys/${keyName}/validate`)
  }

  async migrateApiKeysFromEnv() {
    return await this.client.post('/settings/api-keys/migrate-from-env')
  }

  // System Configuration Settings endpoints
  async getSystemConfigSettings() {
    try {
      const response = await this.client.get('/settings/system-config')
      return response
    } catch (error) {
      console.error('Failed to get system config settings:', error)
      throw error
    }
  }

  async updateSystemConfigSettings(settingsData) {
    try {
      const response = await this.client.put('/settings/system-config', settingsData)
      return response
    } catch (error) {
      console.error('Failed to update system config settings:', error)
      throw error
    }
  }

  // Security Settings endpoints
  async getSecuritySettings() {
    try {
      const response = await this.client.get('/settings/security')
      return response
    } catch (error) {
      console.error('Failed to get security settings:', error)
      throw error
    }
  }

  async updateSecuritySettings(settingsData) {
    try {
      const response = await this.client.put('/settings/security', settingsData)
      return response
    } catch (error) {
      console.error('Failed to update security settings:', error)
      throw error
    }
  }

  // Core Settings endpoints
  async getCoreSettings() {
    try {
      const response = await this.client.get('/settings/core')
      return response
    } catch (error) {
      console.error('Failed to get core settings:', error)
      throw error
    }
  }

  async updateCoreSettings(settingsData) {
    try {
      const response = await this.client.put('/settings/core', settingsData)
      return response
    } catch (error) {
      console.error('Failed to update core settings:', error)
      throw error
    }
  }

  // UX Settings endpoints
  async getUXSettings() {
    try {
      const response = await this.client.get('/settings/ux')
      return response
    } catch (error) {
      console.error('Failed to get UX settings:', error)
      throw error
    }
  }

  async updateUXSettings(settingsData) {
    try {
      const response = await this.client.put('/settings/ux', settingsData)
      return response
    } catch (error) {
      console.error('Failed to update UX settings:', error)
      throw error
    }
  }

  // Search Retrieval Settings endpoints
  async getSearchRetrievalSettings() {
    try {
      const response = await this.client.get('/settings/search-retrieval')
      return response
    } catch (error) {
      console.error('Failed to get search retrieval settings:', error)
      throw error
    }
  }

  async updateSearchRetrievalSettings(settingsData) {
    try {
      const response = await this.client.put('/settings/search-retrieval', settingsData)
      return response
    } catch (error) {
      console.error('Failed to update search retrieval settings:', error)
      throw error
    }
  }

  // Taxonomy Settings endpoints
  async getTaxonomySettings() {
    try {
      const response = await this.client.get('/settings/taxonomy')
      return response
    } catch (error) {
      console.error('Failed to get taxonomy settings:', error)
      throw error
    }
  }

  async updateTaxonomySettings(settingsData) {
    try {
      const response = await this.client.put('/settings/taxonomy', settingsData)
      return response
    } catch (error) {
      console.error('Failed to update taxonomy settings:', error)
      throw error
    }
  }

  async getTaxonomyFallback() {
    try {
      const response = await this.client.get('/settings/taxonomy/fallback')
      return response
    } catch (error) {
      console.error('Failed to get taxonomy fallback:', error)
      throw error
    }
  }

  async uploadTaxonomyFallback(file) {
    try {
      const form = new FormData()
      form.append('file', file)
      const response = await this.client.post('/settings/taxonomy/fallback-file', form)
      return response
    } catch (error) {
      console.error('Failed to upload taxonomy fallback file:', error)
      throw error
    }
  }

  async autoGenerateTaxonomy(options = {}) {
    try {
      const response = await this.client.post('/settings/taxonomy/auto-generate', options)
      return response
    } catch (error) {
      console.error('Failed to auto-generate taxonomy:', error)
      throw error
    }
  }

  async listTaxonomyVersions(limit = 20, offset = 0) {
    try {
      const response = await this.client.get(`/settings/taxonomy/versions?limit=${limit}&offset=${offset}`)
      return response
    } catch (error) {
      console.error('Failed to list taxonomy versions:', error)
      throw error
    }
  }

  async getTaxonomyVersion(versionId) {
    try {
      const response = await this.client.get(`/settings/taxonomy/versions/${versionId}`)
      return response
    } catch (error) {
      console.error('Failed to get taxonomy version:', error)
      throw error
    }
  }

  async restoreTaxonomyVersion(versionId, note) {
    try {
      const response = await this.client.post(`/settings/taxonomy/versions/${versionId}/restore`, note ? { note } : {})
      return response
    } catch (error) {
      console.error('Failed to restore taxonomy version:', error)
      throw error
    }
  }

  async createTaxonomyVersion(settings, note) {
    try {
      const body = { settings, note }
      const response = await this.client.post('/settings/taxonomy/versions', body)
      return response
    } catch (error) {
      console.error('Failed to create taxonomy snapshot:', error)
      throw error
    }
  }

  // User Management endpoints
  async getUsers() {
    return await this.client.get('/users')
  }

  async deactivateUser(userId) {
    return await this.client.put(`/users/${userId}/deactivate`)
  }

  async deleteUser(userId) {
    return await this.client.delete(`/users/${userId}`)
  }

  async bulkDeleteUsers(userIds) {
    return await this.client.delete('/users/bulk', {
      data: { user_ids: userIds }
    })
  }

  async bulkDeactivateUsers(userIds) {
    return await this.client.post('/users/bulk/deactivate', { user_ids: userIds })
  }

  async reactivateUser(userId) {
    return await this.client.post(`/users/${userId}/reactivate`)
  }

  // User profile management
  async updateDisplayName(displayName) {
    return await this.client.put('/user/display-name', { display_name: displayName })
  }

  async updateEmail(email, password) {
    return await this.client.put('/user/email', { email, password })
  }

  // Tenant Management endpoints
  async getMyTenants() {
    try {
      const response = await this.client.get('/tenants/mine')
      return response
    } catch (error) {
      console.error('Failed to get user tenants:', error)
      throw error
    }
  }

  async createTenant(tenantData) {
    try {
      const response = await this.client.post('/tenants', tenantData)
      return response
    } catch (error) {
      console.error('Failed to create tenant:', error)
      throw error
    }
  }

  async createInvitation(invitationData) {
    try {
      const response = await this.client.post('/invitations', invitationData)
      return response
    } catch (error) {
      console.error('Failed to create invitation:', error)
      throw error
    }
  }

  async acceptInvitation(token) {
    try {
      const response = await this.client.post('/invitations/accept', { token })
      return response
    } catch (error) {
      console.error('Failed to accept invitation:', error)
      throw error
    }
  }

  // Authentication token methods removed - now using HTTPOnly cookies exclusively
  // These methods are kept for backward compatibility but do nothing
  setAuthToken(token) {
    console.warn('setAuthToken deprecated - using HTTPOnly cookies')
  }

  clearAuthToken() {
    console.warn('clearAuthToken deprecated - using HTTPOnly cookies')
  }
}

// Create and export singleton instance
export const adminAPI = new AdminAPI()
export default adminAPI
