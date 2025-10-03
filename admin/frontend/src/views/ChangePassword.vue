<template>
  <v-container>
    <v-row justify="center">
      <v-col
        cols="12"
        md="6"
      >
        <v-card>
          <v-card-title>
            <v-icon left>
              $lock
            </v-icon>
            Change Password
          </v-card-title>
          
          <v-card-text>
            <v-form ref="form">
              <v-text-field
                v-model="currentPassword"
                :rules="[requiredRule]"
                label="Current Password"
                type="password"
                prepend-icon="$lock-outline"
                required
              />
              
              <v-text-field
                v-model="newPassword"
                :rules="[requiredRule, minLengthRule]"
                label="New Password"
                type="password"
                prepend-icon="$lock"
                required
                hint="At least 8 characters with uppercase, lowercase, digit, and special character"
              />
              
              <v-text-field
                v-model="confirmPassword"
                :rules="[requiredRule, passwordMatchRule]"
                label="Confirm New Password"
                type="password"
                prepend-icon="$lock-check"
                required
              />
              
              <v-alert
                v-if="error"
                type="error"
                dismissible
                class="mt-3"
                @click="error = ''"
              >
                {{ error }}
              </v-alert>
              
              <v-alert
                v-if="success"
                type="success"
                dismissible
                class="mt-3"
                @click="success = ''"
              >
                {{ success }}
              </v-alert>
            </v-form>
          </v-card-text>
          
          <v-card-actions>
            <v-spacer />
            <v-btn
              color="grey"
              text
              @click="resetForm"
            >
              Cancel
            </v-btn>
            <v-btn
              color="primary"
              :disabled="loading"
              :loading="loading"
              @click="changePassword"
            >
              Change Password
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/services/api'

export default {
  name: 'ChangePassword',
  setup() {
    const router = useRouter()
    const form = ref(null)
    
    const loading = ref(false)
    const currentPassword = ref('')
    const newPassword = ref('')
    const confirmPassword = ref('')
    const error = ref('')
    const success = ref('')
    
    const requiredRule = (v) => Boolean(v) || 'Required'
    const minLengthRule = (v) => {
      if (!v) return 'Password is required'
      if (v.length < 8) return 'Password must be at least 8 characters'
      if (!/[A-Z]/.test(v)) return 'Password must contain at least one uppercase letter'
      if (!/[a-z]/.test(v)) return 'Password must contain at least one lowercase letter'
      if (!/\d/.test(v)) return 'Password must contain at least one digit'
      if (!/[!@#$%^&*()_+\-=[\]{}|;:,.<>?]/.test(v)) return 'Password must contain at least one special character'
      return true
    }
    const passwordMatchRule = computed(() => (v) => v === newPassword.value || 'Passwords must match')
    
    const changePassword = async () => {
      const result = await form.value?.validate?.()
      if (!result || result.valid === false) {
        return
      }
      
      loading.value = true
      error.value = ''
      success.value = ''
      
      try {
        const response = await api.changePassword(currentPassword.value, newPassword.value)
        
        if (response.success) {
          success.value = 'Password changed successfully! All sessions have been invalidated. You will be redirected to login.'
          resetForm()
          
          // HTTPOnly cookies will be cleared by the server
          
          // Redirect to login page since sessions are expired
          setTimeout(() => {
            router.push('/login')
          }, 3000)
        }
      } catch (err) {
        if (err.response && err.response.data) {
          error.value = err.response.data.detail || 'Failed to change password'
        } else {
          error.value = 'An error occurred while changing password'
        }
      } finally {
        loading.value = false
      }
    }
    
    const resetForm = () => {
      currentPassword.value = ''
      newPassword.value = ''
      confirmPassword.value = ''
      error.value = ''
      if (form.value) {
        form.value.reset()
      }
    }
    
    return {
      form,
      loading,
      currentPassword,
      newPassword,
      confirmPassword,
      error,
      success,
      requiredRule,
      minLengthRule,
      passwordMatchRule,
      changePassword,
      resetForm
    }
  }
}
</script>

<style scoped>
.v-card {
  margin-top: 20px;
}
</style>