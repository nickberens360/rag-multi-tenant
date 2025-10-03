<template>
  <div class="profile-settings">
    <!-- Display Name Section -->
    <v-card
      class="mb-6"
      rounded="lg"
      elevation="1"
    >
      <v-card-title class="d-flex align-center">
        <v-icon start>
          $account
        </v-icon>
        Display Name
      </v-card-title>
      <v-card-text>
        <v-form
          ref="displayNameForm"
          @submit.prevent="handleDisplayNameChange"
        >
          <v-text-field
            v-model="displayName"
            label="Display Name"
            placeholder="Enter your display name"
            variant="outlined"
            density="comfortable"
            :rules="displayNameRules"
            class="mb-4"
          />
          <div class="d-flex justify-end">
            <v-btn
              type="submit"
              color="primary"
              variant="flat"
              :loading="displayNameLoading"
              :disabled="!displayNameChanged"
            >
              Update Display Name
            </v-btn>
          </div>
        </v-form>
      </v-card-text>
    </v-card>

    <!-- Email Section -->
    <v-card
      class="mb-6"
      rounded="lg"
      elevation="1"
    >
      <v-card-title class="d-flex align-center">
        <v-icon start>
          $email
        </v-icon>
        Email Address
      </v-card-title>
      <v-card-text>
        <v-form
          ref="emailForm"
          @submit.prevent="handleEmailChange"
        >
          <v-text-field
            v-model="email"
            label="Email Address"
            placeholder="Enter your email address"
            type="email"
            variant="outlined"
            density="comfortable"
            :rules="emailRules"
            class="mb-4"
          />
          <v-text-field
            v-model="emailPassword"
            label="Confirm with Password"
            placeholder="Enter your password to confirm"
            type="password"
            variant="outlined"
            density="comfortable"
            :rules="passwordRules"
            hint="For security, please enter your current password to change your email"
            persistent-hint
            class="mb-4"
          />
          <div class="d-flex justify-end">
            <v-btn
              type="submit"
              color="primary"
              variant="flat"
              :loading="emailLoading"
              :disabled="!emailChanged || !emailPassword"
            >
              Update Email
            </v-btn>
          </div>
        </v-form>
      </v-card-text>
    </v-card>

    <!-- Password Section -->
    <v-card
      rounded="lg"
      elevation="1"
    >
      <v-card-title class="d-flex align-center">
        <v-icon start>
          $lock
        </v-icon>
        Change Password
      </v-card-title>
      <v-card-text>
        <v-form
          ref="passwordForm"
          @submit.prevent="handlePasswordChange"
        >
          <v-text-field
            v-model="currentPassword"
            label="Current Password"
            placeholder="Enter your current password"
            :type="showCurrentPassword ? 'text' : 'password'"
            variant="outlined"
            density="comfortable"
            :rules="passwordRules"
            :append-inner-icon="showCurrentPassword ? '$eye-off' : '$eye'"
            class="mb-4"
            @click:append-inner="showCurrentPassword = !showCurrentPassword"
          />
          <v-text-field
            v-model="newPassword"
            label="New Password"
            placeholder="Enter your new password"
            :type="showNewPassword ? 'text' : 'password'"
            variant="outlined"
            density="comfortable"
            :rules="newPasswordRules"
            :append-inner-icon="showNewPassword ? '$eye-off' : '$eye'"
            class="mb-4"
            @click:append-inner="showNewPassword = !showNewPassword"
          />
          <v-text-field
            v-model="confirmPassword"
            label="Confirm New Password"
            placeholder="Confirm your new password"
            :type="showConfirmPassword ? 'text' : 'password'"
            variant="outlined"
            density="comfortable"
            :rules="confirmPasswordRules"
            :append-inner-icon="showConfirmPassword ? '$eye-off' : '$eye'"
            :error-messages="passwordMatchError"
            class="mb-4"
            @click:append-inner="showConfirmPassword = !showConfirmPassword"
          />
          
          <!-- Password Requirements -->
          <v-alert
            type="info"
            variant="tonal"
            density="compact"
            class="mb-4"
          >
            <div class="text-caption">
              Password Requirements:
              <ul class="mt-1 ml-4">
                <li>At least 8 characters long</li>
                <li>Contains at least one uppercase letter</li>
                <li>Contains at least one lowercase letter</li>
                <li>Contains at least one number</li>
                <li>Contains at least one special character</li>
              </ul>
            </div>
          </v-alert>

          <div class="d-flex justify-end">
            <v-btn
              type="submit"
              color="primary"
              variant="flat"
              :loading="passwordLoading"
              :disabled="!currentPassword || !newPassword || !confirmPassword || passwordMatchError !== ''"
            >
              Change Password
            </v-btn>
          </div>
        </v-form>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAdminStore } from '@/stores/admin'
import { adminAPI } from '@/services/api'
import { useNotifications } from '@/composables/useNotifications'
import { 
  getBasicPasswordRules, 
  getStrongPasswordRules, 
  getDisplayNameRules, 
  getEmailRules, 
  getPasswordConfirmationRules 
} from '@/utils/validation'

// Global notifications
const { showSuccess, showError } = useNotifications()

// Store
const adminStore = useAdminStore()

// Form refs
const displayNameForm = ref()
const emailForm = ref()
const passwordForm = ref()

// Display Name fields
const displayName = ref('')
const originalDisplayName = ref('')
const displayNameLoading = ref(false)

// Email fields
const email = ref('')
const originalEmail = ref('')
const emailPassword = ref('')
const emailLoading = ref(false)

// Password fields
const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const showCurrentPassword = ref(false)
const showNewPassword = ref(false)
const showConfirmPassword = ref(false)
const passwordLoading = ref(false)

// Computed properties
const displayNameChanged = computed(() => displayName.value !== originalDisplayName.value)
const emailChanged = computed(() => email.value !== originalEmail.value)

const passwordMatchError = computed(() => {
  if (!confirmPassword.value || !newPassword.value) return ''
  return newPassword.value !== confirmPassword.value ? 'Passwords do not match' : ''
})

// Validation rules using shared utility functions
const displayNameRules = getDisplayNameRules()
const emailRules = getEmailRules()
const passwordRules = getBasicPasswordRules()
const newPasswordRules = getStrongPasswordRules()
const confirmPasswordRules = computed(() => getPasswordConfirmationRules(newPassword.value))

// Methods
const loadUserData = async () => {
  try {
    // Get current user data from the store first
    await adminStore.checkAuth()
    const userData = adminStore.user
    if (userData) {
      displayName.value = userData.display_name || userData.username || 'Admin User'
      originalDisplayName.value = displayName.value
      email.value = userData.email || ''
      originalEmail.value = email.value
    }
  } catch (error) {
    console.error('Error loading user data:', error)
    showError('Failed to load user data')
  }
}

const handleDisplayNameChange = async () => {
  const valid = await displayNameForm.value.validate()
  if (!valid.valid) return

  displayNameLoading.value = true
  try {
    const response = await adminAPI.updateDisplayName(displayName.value)
    
    if (response.success) {
      originalDisplayName.value = displayName.value
      // Update the store with the new display name
      await adminStore.checkAuth()
      showSuccess('Display name updated successfully')
    } else {
      throw new Error(response.message || 'Failed to update display name')
    }
  } catch (error) {
    showError(error.response?.data?.detail || 'Failed to update display name. Please try again.')
    console.error('Display name update error:', error)
  } finally {
    displayNameLoading.value = false
  }
}

const handleEmailChange = async () => {
  const valid = await emailForm.value.validate()
  if (!valid.valid) return

  emailLoading.value = true
  try {
    const response = await adminAPI.updateEmail(email.value, emailPassword.value)
    
    if (response.success) {
      originalEmail.value = email.value
      emailPassword.value = ''
      // Update the store with the new email
      await adminStore.checkAuth()
      showSuccess('Email address updated successfully')
    } else {
      throw new Error(response.message || 'Failed to update email address')
    }
  } catch (error) {
    showError(error.response?.data?.detail || 'Failed to update email address. Please check your password and try again.')
    console.error('Email update error:', error)
  } finally {
    emailLoading.value = false
  }
}

const handlePasswordChange = async () => {
  const valid = await passwordForm.value.validate()
  if (!valid.valid) return

  if (newPassword.value !== confirmPassword.value) {
    showError('Passwords do not match')
    return
  }

  passwordLoading.value = true
  try {
    const response = await adminAPI.changePassword(currentPassword.value, newPassword.value)
    
    if (response.success) {
      // Clear password fields on success
      currentPassword.value = ''
      newPassword.value = ''
      confirmPassword.value = ''
      showCurrentPassword.value = false
      showNewPassword.value = false
      showConfirmPassword.value = false
      
      showSuccess('Password changed successfully')
    } else {
      throw new Error(response.message || 'Failed to change password')
    }
  } catch (error) {
    showError(error.response?.data?.detail || 'Failed to change password. Please check your current password and try again.')
    console.error('Password change error:', error)
  } finally {
    passwordLoading.value = false
  }
}

// Lifecycle
onMounted(() => {
  loadUserData()
})
</script>

<style scoped>
.profile-settings {
  max-width: 800px;
}

/* Ensure form fields have consistent spacing */
.v-form {
  width: 100%;
}

/* Improve readability of password requirements */
.v-alert ul {
  margin: 0;
  padding: 0;
}

.v-alert li {
  margin: 2px 0;
}
</style>
