import { defineStore } from 'pinia'
import { adminAPI } from '../services/api.js'

export const useUsersStore = defineStore('users', {
  state: () => ({
    users: [],
    loading: false,
    error: null,
    lastUpdated: null
  }),

  getters: {
    activeUsers: (state) => state.users.filter(user => user.is_active),
    inactiveUsers: (state) => state.users.filter(user => !user.is_active),
    userCount: (state) => state.users.length,
    activeUserCount: (state) => state.users.filter(user => user.is_active).length,
    adminUsers: (state) => state.users.filter(user => user.role === 'admin'),
    viewerUsers: (state) => state.users.filter(user => user.role === 'viewer'),
    
    getUserById: (state) => (id) => state.users.find(user => user.id === id),
    getUserByUsername: (state) => (username) => state.users.find(user => user.username === username),
  },

  actions: {
    async fetchUsers() {
      this.loading = true
      this.error = null
      
      try {
        const response = await adminAPI.getUsers()
        
        if (Array.isArray(response)) {
          this.users = response
        } else {
          console.error('❌ Users Store: Response is not an array:', typeof response)
          throw new Error('Invalid response format - expected array')
        }
        
        this.lastUpdated = new Date()
        
      } catch (error) {
        console.error('❌ Users Store: Error fetching users:', error)
        if (import.meta.env.DEV) {
          console.error('❌ Error details:', error.response?.data)
        }
        
        this.error = {
          message: error.message,
          status: error.response?.status,
          data: error.response?.data,
          timestamp: new Date()
        }
        
        // Don't clear users on error - keep previous data if available
        if (!this.users.length) {
          this.users = []
        }
        
        throw error
      } finally {
        this.loading = false
      }
    },

    async createUser(userData) {
      this.loading = true
      this.error = null
      
      try {
        const response = await adminAPI.createUser(userData)
        
        // Add the new user to the store instead of refetching the entire list
        if (response.user) {
          this.users.push(response.user)
          this.lastUpdated = new Date()
        } else {
          // Fallback to refetching if user data isn't returned for some reason
          await this.fetchUsers()
        }
        
        return response
      } catch (error) {
        console.error('❌ Users Store: Error creating user:', error.message)
        this.error = {
          message: error.message,
          status: error.response?.status,
          data: error.response?.data,
          timestamp: new Date()
        }
        throw error
      } finally {
        this.loading = false
      }
    },

    async deactivateUser(userId) {
      this.loading = true
      this.error = null
      
      try {
        const response = await adminAPI.deactivateUser(userId)
        
        // Update user in store immediately for better UX
        const userIndex = this.users.findIndex(user => user.id === userId)
        if (userIndex !== -1) {
          this.users[userIndex].is_active = false
        }
        
        return response
      } catch (error) {
        console.error('❌ Users Store: Error deactivating user:', error.message)
        this.error = {
          message: error.message,
          status: error.response?.status,
          data: error.response?.data,
          timestamp: new Date()
        }
        throw error
      } finally {
        this.loading = false
      }
    },

    async deleteUser(userId) {
      this.loading = true
      this.error = null
      
      try {
        const response = await adminAPI.deleteUser(userId)
        
        // Remove user from store immediately
        const userIndex = this.users.findIndex(user => user.id === userId)
        if (userIndex !== -1) {
          const deletedUser = this.users[userIndex]
          this.users.splice(userIndex, 1)
        }
        
        return response
      } catch (error) {
        console.error('❌ Users Store: Error deleting user:', error.message)
        this.error = {
          message: error.message,
          status: error.response?.status,
          data: error.response?.data,
          timestamp: new Date()
        }
        throw error
      } finally {
        this.loading = false
      }
    },

    async bulkDeleteUsers(userIds) {
      
      // Validate input
      if (!Array.isArray(userIds) || userIds.length === 0) {
        throw new Error('Invalid user IDs provided')
      }
      
      if (userIds.length > 50) {
        throw new Error('Cannot delete more than 50 users at once')
      }
      
      // Ensure all IDs are valid integers
      const invalidIds = userIds.filter(id => !Number.isInteger(id) || id <= 0)
      if (invalidIds.length > 0) {
        throw new Error(`Invalid user IDs: ${invalidIds.join(', ')}`)
      }
      
      this.loading = true
      this.error = null
      
      try {
        const response = await adminAPI.bulkDeleteUsers(userIds)
        
        // Remove successfully deleted users from store
        if (response.deleted_users) {
          // Remove by username since that's what we get back
          const deletedUsernames = response.deleted_users
          this.users = this.users.filter(user => !deletedUsernames.includes(user.username))
        } else if (response.successful_deletions > 0) {
          // Fallback: remove by user ID if we don't get usernames back
          this.users = this.users.filter(user => !userIds.includes(user.id))
        }
        
        return response
      } catch (error) {
        console.error('❌ Users Store: Error in bulk delete:', error.message)
        this.error = {
          message: error.message,
          status: error.response?.status,
          data: error.response?.data,
          timestamp: new Date()
        }
        throw error
      } finally {
        this.loading = false
      }
    },

    async reactivateUser(userId) {
      this.loading = true
      this.error = null
      
      try {
        const response = await adminAPI.reactivateUser(userId)
        
        // Update the user in the store
        const userIndex = this.users.findIndex(u => u.id === userId)
        if (userIndex !== -1) {
          this.users[userIndex].is_active = true
        }
        
        return response
      } catch (error) {
        console.error('❌ Users Store: Error reactivating user:', error.message)
        this.error = {
          message: error.message,
          status: error.response?.status,
          data: error.response?.data,
          timestamp: new Date()
        }
        throw error
      } finally {
        this.loading = false
      }
    },

    async bulkDeactivateUsers(userIds) {
      
      // Validate input
      if (!Array.isArray(userIds) || userIds.length === 0) {
        throw new Error('Invalid user IDs provided')
      }
      
      if (userIds.length > 50) {
        throw new Error('Cannot deactivate more than 50 users at once')
      }
      
      // Ensure all IDs are valid integers
      const invalidIds = userIds.filter(id => !Number.isInteger(id) || id <= 0)
      if (invalidIds.length > 0) {
        throw new Error(`Invalid user IDs: ${invalidIds.join(', ')}`)
      }
      
      this.loading = true
      this.error = null
      
      try {
        const response = await adminAPI.bulkDeactivateUsers(userIds)
        
        // Update successfully deactivated users in store
        if (response.deactivated_user_ids && response.deactivated_user_ids.length > 0) {
          const deactivatedIdsSet = new Set(response.deactivated_user_ids)
          this.users.forEach(user => {
            if (deactivatedIdsSet.has(user.id)) {
              user.is_active = false
            }
          })
        }
        
        return response
      } catch (error) {
        console.error('❌ Users Store: Error in bulk deactivate:', error.message)
        this.error = {
          message: error.message,
          status: error.response?.status,
          data: error.response?.data,
          timestamp: new Date()
        }
        throw error
      } finally {
        this.loading = false
      }
    },

    // Utility actions
    clearError() {
      this.error = null
    },

    reset() {
      this.users = []
      this.loading = false
      this.error = null
      this.lastUpdated = null
    },

    // Method to clear tenant-specific data (called by reactive watchers in components)
    clearTenantData() {
      console.debug('Users store: clearing tenant-specific data')
      this.reset()
    }
  }
})