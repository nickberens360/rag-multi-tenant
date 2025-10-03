<template>
  <div class="settings-page">
    <div class="settings-layout">
      <!-- Pure Navigation -->
      <SettingsNavigation />
      
      <!-- Content Area -->
      <main class="settings-content">
        <!-- Page Header -->
        <SettingsHeader />
        
        <!-- Just route content, no data orchestration -->
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import SettingsNavigation from '@/components/settings/SettingsNavigation.vue'
import SettingsHeader from '@/components/settings/SettingsHeader.vue'

// Minimal parent - only layout and navigation
// No data loading, no prop drilling, no event bubbling
</script>

<style scoped>
.settings-page {
  max-width: 100%;
  margin: 0 auto;
}

.settings-layout {
  display: flex;
  gap: 24px;
  align-items: flex-start;
}

.settings-content {
  flex: 1;
  min-width: 0;
}

/* Responsive Design */
@media (max-width: 1024px) {
  .settings-layout {
    flex-direction: column;
    gap: 16px;
  }
}

@media (max-width: 768px) {
  .settings-page {
    padding: 0 16px;
  }
}
</style>
