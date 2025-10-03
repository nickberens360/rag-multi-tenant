<template>
  <div v-if="error" class="tenant-error-boundary">
    <div class="error-icon">⚠️</div>
    <h2 class="error-title">Tenant Error</h2>
    <p class="error-message">{{ error.message }}</p>
    <div class="error-actions">
      <button @click="retry" class="retry-button">
        Retry
      </button>
      <button @click="goHome" class="home-button">
        Go Home
      </button>
    </div>
    <details v-if="isDev" class="error-details">
      <summary>Error Details (Dev Only)</summary>
      <pre>{{ error.stack }}</pre>
    </details>
  </div>
  <slot v-else />
</template>

<script setup lang="ts">
import { ref, onErrorCaptured } from 'vue';

const error = ref<Error | null>(null);
const isDev = import.meta.env.DEV;

/**
 * Capture errors that occur in child components
 * Only captures tenant-related errors to avoid interfering with other error handling
 */
onErrorCaptured((err: Error) => {
  // Only capture tenant-related errors
  const isTenantError =
    err.message.toLowerCase().includes('tenant') ||
    err.message.toLowerCase().includes('organization');

  if (isTenantError) {
    error.value = err;
    console.error('Tenant error captured:', err);
    return false; // Prevent error propagation
  }

  return true; // Let other errors bubble up
});

function retry() {
  error.value = null;
  // Trigger re-render of child components
  window.location.reload();
}

function goHome() {
  const defaultSlug = import.meta.env.PUBLIC_TENANT_DEFAULT_SLUG || '';
  window.location.href = defaultSlug ? `/${defaultSlug}` : '/';
}
</script>

<style scoped>
.tenant-error-boundary {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  margin: 2rem auto;
  max-width: 600px;
  border: 2px solid #ff6b6b;
  border-radius: 0.5rem;
  background: linear-gradient(to bottom, #ffe0e0, #fff5f5);
  text-align: center;
}

.error-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
  animation: shake 0.5s ease-in-out;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-10px); }
  75% { transform: translateX(10px); }
}

.error-title {
  font-size: 1.5rem;
  color: #d32f2f;
  margin: 0 0 0.5rem 0;
}

.error-message {
  color: #666;
  margin: 0 0 1.5rem 0;
  font-size: 1rem;
}

.error-actions {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.retry-button,
.home-button {
  padding: 0.5rem 1.25rem;
  border: none;
  border-radius: 0.375rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.875rem;
}

.retry-button {
  background: #0066cc;
  color: white;
}

.retry-button:hover {
  background: #0052a3;
  transform: translateY(-1px);
}

.home-button {
  background: #e0e0e0;
  color: #333;
}

.home-button:hover {
  background: #d0d0d0;
  transform: translateY(-1px);
}

.error-details {
  margin-top: 1rem;
  width: 100%;
  text-align: left;
  font-size: 0.75rem;
}

.error-details summary {
  cursor: pointer;
  color: #666;
  margin-bottom: 0.5rem;
}

.error-details pre {
  background: #f5f5f5;
  padding: 0.75rem;
  border-radius: 0.25rem;
  overflow-x: auto;
  font-size: 0.75rem;
  color: #d32f2f;
}
</style>
