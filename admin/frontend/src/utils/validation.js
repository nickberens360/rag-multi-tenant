/**
 * Shared validation rules for form fields
 */

/**
 * Get password validation rules for basic password fields
 * @param {string} requiredMessage - Custom required message
 * @returns {Array} Array of validation functions
 */
export function getBasicPasswordRules(requiredMessage = 'Password is required') {
  return [
    v => Boolean(v) || requiredMessage,
    v => v.length >= 8 || 'Password must be at least 8 characters'
  ]
}

/**
 * Get comprehensive password validation rules for new password fields
 * @param {string} requiredMessage - Custom required message
 * @returns {Array} Array of validation functions
 */
export function getStrongPasswordRules(requiredMessage = 'New password is required') {
  return [
    v => Boolean(v) || requiredMessage,
    v => v.length >= 8 || 'Password must be at least 8 characters',
    v => /[A-Z]/.test(v) || 'Password must contain at least one uppercase letter',
    v => /[a-z]/.test(v) || 'Password must contain at least one lowercase letter',
    v => /[0-9]/.test(v) || 'Password must contain at least one number',
    v => /[^A-Za-z0-9]/.test(v) || 'Password must contain at least one special character'
  ]
}

/**
 * Get display name validation rules
 * @returns {Array} Array of validation functions
 */
export function getDisplayNameRules() {
  return [
    v => Boolean(v) || 'Display name is required',
    v => v.length >= 2 || 'Display name must be at least 2 characters',
    v => v.length <= 50 || 'Display name must be less than 50 characters'
  ]
}

/**
 * Get email validation rules
 * @returns {Array} Array of validation functions
 */
export function getEmailRules() {
  return [
    v => Boolean(v) || 'Email is required',
    v => /.+@.+\..+/.test(v) || 'Email must be valid'
  ]
}

/**
 * Get password confirmation validation rules
 * @param {string} passwordValue - The password to match against
 * @returns {Array} Array of validation functions
 */
export function getPasswordConfirmationRules(passwordValue) {
  return [
    v => Boolean(v) || 'Please confirm your password',
    v => v === passwordValue || 'Passwords do not match'
  ]
}