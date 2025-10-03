<template>
  <div
    class="org-switcher"
    v-bind="$attrs"
  >
    <v-menu>
      <template #activator="{ props }">
        <v-btn
          v-bind="props"
          variant="outlined"
        >
          <v-icon start>
            $account-group
          </v-icon>
          {{ currentTenant?.name || 'Select Organization' }}
          <v-icon end>
            $chevron-down
          </v-icon>
        </v-btn>
      </template>
      <v-list>
        <v-list-item
          v-for="tenant in userTenants"
          :key="tenant.id"
          :active="tenant.id === currentTenant?.id"
          @click="switchToTenant(tenant)"
        >
          <v-list-item-title>{{ tenant.name }}</v-list-item-title>
          <v-list-item-subtitle>{{ tenant.role }}</v-list-item-subtitle>
        </v-list-item>
        <v-divider />
        <v-list-item @click="openCreateDialog">
          <v-list-item-title>
            <v-icon start>
              $plus
            </v-icon>
            Create Organization
          </v-list-item-title>
        </v-list-item>
      </v-list>
    </v-menu>
    <!-- Create Organization Dialog -->
    <v-dialog
      v-model="showCreateDialog"
      max-width="480"
    >
      <v-card>
        <v-card-title>Create Organization</v-card-title>
        <v-card-text>
          <v-text-field
            v-model="newTenantName"
            label="Organization Name"
            variant="outlined"
            :disabled="creating"
            required
          />
          <v-text-field
            v-model="newTenantSlug"
            label="Slug"
            variant="outlined"
            :disabled="creating"
            hint="Lowercase letters, numbers and hyphens"
            persistent-hint
            required
          />
          <v-alert
            v-if="errorMessage"
            type="error"
            variant="tonal"
            class="mt-2"
          >
            {{ errorMessage }}
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            :disabled="creating"
            @click="closeCreateDialog"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            :loading="creating"
            :disabled="!isValid"
            @click="createTenant"
          >
            Create
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch, computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useTenantStore } from '@/stores/tenant'
import { adminAPI } from '@/services/api'

const tenantStore = useTenantStore()
const { currentTenant, userTenants } = storeToRefs(tenantStore)

onMounted(() => {
  // Tenant store is initialized by AdminLayout, no need to fetch again
  console.log('OrgSwitcher mounted, current tenant:', currentTenant.value)
  console.log('OrgSwitcher mounted, user tenants:', userTenants.value)
})

async function switchToTenant(tenant) {
  const result = await tenantStore.switchTenant(tenant)
  if (!result.success) {
    console.error('Failed to switch tenant:', result.error)
  }
}

// Create organization dialog logic
const showCreateDialog = ref(false)
const creating = ref(false)
const newTenantName = ref('')
const newTenantSlug = ref('')
const errorMessage = ref('')

const isValid = computed(() => newTenantName.value.trim().length > 1 && newTenantSlug.value.trim().length > 1)

function openCreateDialog() {
  errorMessage.value = ''
  newTenantName.value = ''
  newTenantSlug.value = ''
  showCreateDialog.value = true
}

function closeCreateDialog() {
  if (!creating.value) showCreateDialog.value = false
}

function slugify(input: string): string {
  return input
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9-\s]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 80)
}

watch(newTenantName, (val) => {
  if (!newTenantSlug.value || newTenantSlug.value === slugify(newTenantSlug.value)) {
    newTenantSlug.value = slugify(val || '')
  }
})

async function createTenant() {
  if (!isValid.value) return
  creating.value = true
  errorMessage.value = ''
  try {
    const payload = { slug: newTenantSlug.value, name: newTenantName.value }
    const created = await adminAPI.createTenant(payload)
    // Refresh list, then switch to the new tenant
    await tenantStore.fetchUserTenants()
    const matched = userTenants.value.find(t => t.slug === created.slug) || created
    await tenantStore.switchTenant(matched)
    showCreateDialog.value = false
  } catch (err: any) {
    errorMessage.value = adminAPI.formatError?.(err) || (err?.message || 'Failed to create organization')
  } finally {
    creating.value = false
  }
}
</script>
