<template>
  <div class="users-view">
    <v-container fluid>
      <!-- Page Header -->
      <v-row>
        <v-col cols="12">
          <div class="d-flex align-center justify-space-between mb-6">
            <div>
              <h1 class="text-h4 font-weight-bold">
                User Management
              </h1>
              <p class="text-subtitle-1 text-medium-emphasis mt-1">
                Manage admin users and their access permissions
              </p>
            </div>
            <v-btn
              color="primary"
              prepend-icon="$account-plus"
              :loading="storeLoading"
              @click="showCreateDialog = true"
            >
              Add User
            </v-btn>
          </div>
        </v-col>
      </v-row>

      <!-- Users Table -->
      <v-row>
        <v-col cols="12">
          <v-card>
            <v-card-title class="d-flex align-center pa-6">
              <v-icon class="me-3">
                $users
              </v-icon>
              Admin Users
              <v-spacer />
              <v-chip
                :color="(users?.length || 0) > 0 ? 'success' : 'warning'"
                variant="flat"
                size="small"
              >
                {{ users?.length || 0 }} {{ (users?.length || 0) === 1 ? 'user' : 'users' }}
              </v-chip>
            </v-card-title>

            <v-divider />

            <!-- Bulk Actions Banner -->
            <v-expand-transition>
              <v-card
                v-if="selectedUsers.length > 0"
                class="bulk-actions-card ma-4 mb-0"
                color="primary"
                variant="tonal"
              >
                <v-card-text class="pa-3">
                  <div class="d-flex align-center justify-space-between">
                    <div class="d-flex align-center">
                      <v-icon class="mr-2">
                        $checkbox-marked
                      </v-icon>
                      <span class="font-weight-medium">
                        {{ selectedUsers.length }} {{ selectedUsers.length === 1 ? 'user' : 'users' }} selected
                      </span>
                    </div>
                    <v-btn-group
                      variant="outlined"
                      density="compact"
                    >
                      <v-btn
                        :loading="false"
                        class="mr-3"
                        @click="clearSelection"
                      >
                        Clear Selection
                      </v-btn>
                      <v-btn
                        prepend-icon="$account-off"
                        :disabled="!canBulkDeactivate"
                        :loading="bulkDeactivating"
                        class="mr-3"
                        @click="showBulkDeactivateDialog = true"
                      >
                        Deactivate
                      </v-btn>
                      <v-btn
                        color="error"
                        prepend-icon="$delete"
                        :disabled="!canBulkDelete"
                        :loading="bulkDeleting"
                        @click="showBulkDeleteDialog = true"
                      >
                        Delete
                      </v-btn>
                    </v-btn-group>
                  </div>
                </v-card-text>
              </v-card>
            </v-expand-transition>

            <v-card-text class="pa-0">
              <v-data-table
                v-model="selectedUsers"
                :headers="headers"
                :items="users"
                :loading="storeLoading"
                show-select
                item-value="id"
                item-key="id"
                class="elevation-0"
                :items-per-page="25"
              >
                <!-- Username Column -->
                <template #[`item.username`]="{ item }">
                  <div class="d-flex align-center">
                    <v-avatar
                      size="32"
                      class="me-3"
                      color="primary"
                    >
                      <span class="text-white text-caption font-weight-bold">
                        {{ item.username.charAt(0).toUpperCase() }}
                      </span>
                    </v-avatar>
                    <div>
                      <div class="font-weight-medium">
                        {{ item.username }}
                      </div>
                      <div
                        v-if="item.email"
                        class="text-caption text-medium-emphasis"
                      >
                        {{ item.email }}
                      </div>
                    </div>
                  </div>
                </template>

                <!-- Role Column -->
                <template #[`item.role`]="{ item }">
                  <v-chip
                    :color="getRoleColor(item.role)"
                    variant="flat"
                    size="small"
                    class="font-weight-medium"
                  >
                    {{ item.role }}
                  </v-chip>
                </template>

                <!-- Status Column -->
                <template #[`item.is_active`]="{ item }">
                  <v-chip
                    :color="item.is_active ? 'success' : 'error'"
                    variant="flat"
                    size="small"
                    :prepend-icon="item.is_active ? '$check-circle' : '$close-circle'"
                  >
                    {{ item.is_active ? 'Active' : 'Inactive' }}
                  </v-chip>
                </template>

                <!-- Created Date Column -->
                <template #[`item.created_at`]="{ item }">
                  <div class="text-body-2">
                    {{ formatDate(item.created_at) }}
                  </div>
                </template>

                <!-- Last Login Column -->
                <template #[`item.last_login_at`]="{ item }">
                  <div class="text-body-2">
                    {{ item.last_login_at ? formatDate(item.last_login_at) : 'Never' }}
                  </div>
                </template>

                <!-- Actions Column -->
                <template #[`item.actions`]="{ item }">
                  <v-menu>
                    <template #activator="{ props }">
                      <v-btn
                        icon="$dots-vertical"
                        variant="text"
                        size="small"
                        v-bind="props"
                      />
                    </template>
                    <v-list>
                      <!-- View Details - Always available -->
                      <v-list-item
                        prepend-icon="$account-details"
                        @click="viewUserDetails(item)"
                      >
                        View Details
                      </v-list-item>
                      
                      <v-divider v-if="!isCurrentUser(item)" />
                      
                      <!-- Deactivate User - Only for active non-current users -->
                      <v-list-item
                        v-if="item.is_active && !isCurrentUser(item)"
                        prepend-icon="$account-off"
                        class="text-warning"
                        @click="confirmDeactivateUser(item)"
                      >
                        Deactivate User
                      </v-list-item>

                      <!-- Reactivate User - Only for inactive users -->
                      <v-list-item
                        v-if="!item.is_active"
                        prepend-icon="$account-check"
                        class="text-success"
                        @click="confirmReactivateUser(item)"
                      >
                        Reactivate User
                      </v-list-item>
                      
                      <!-- Delete User - Only for non-current users -->
                      <v-list-item
                        v-if="!isCurrentUser(item)"
                        prepend-icon="$delete-forever"
                        class="text-error"
                        @click="confirmDeleteUser(item)"
                      >
                        Delete User
                      </v-list-item>
                      
                      <!-- Current User Indicator -->
                      <v-list-item
                        v-if="isCurrentUser(item)"
                        disabled
                        prepend-icon="$account-check"
                      >
                        Current User
                      </v-list-item>
                    </v-list>
                  </v-menu>
                </template>

                <!-- Empty State -->
                <template #no-data>
                  <div class="text-center py-12">
                    <v-icon
                      size="64"
                      class="mb-4 text-medium-emphasis"
                    >
                      $account-group
                    </v-icon>
                    <h3 class="text-h6 mb-2">
                      No users found
                    </h3>
                    <p class="text-body-1 text-medium-emphasis mb-4">
                      Get started by creating your first admin user.
                    </p>
                    <v-btn
                      color="primary"
                      @click="showCreateDialog = true"
                    >
                      Add First User
                    </v-btn>
                  </div>
                </template>

                <!-- Loading State -->
                <template #loading>
                  <div class="text-center py-12">
                    <v-progress-circular
                      indeterminate
                      color="primary"
                    />
                    <p class="mt-4 text-body-1">
                      Loading users...
                    </p>
                  </div>
                </template>
              </v-data-table>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-container>

    <!-- Create User Dialog -->
    <v-dialog
      v-model="showCreateDialog"
      max-width="600px"
      persistent
    >
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon class="me-3">
            $account-plus
          </v-icon>
          Create New User
        </v-card-title>

        <v-divider />

        <v-form
          ref="createForm"
          v-model="createFormValid"
          @submit.prevent="createUserAction"
        >
          <v-card-text class="pb-0">
            <v-row>
              <!-- Username -->
              <v-col cols="12">
                <v-text-field
                  v-model="newUser.username"
                  label="Username"
                  :rules="usernameRules"
                  required
                  prepend-inner-icon="$account"
                  variant="outlined"
                  density="comfortable"
                  hint="Must be unique and contain only letters, numbers, and underscores"
                  persistent-hint
                />
              </v-col>

              <!-- Email -->
              <v-col cols="12">
                <v-text-field
                  v-model="newUser.email"
                  label="Email (Optional)"
                  :rules="emailRules"
                  prepend-inner-icon="$email"
                  variant="outlined"
                  density="comfortable"
                  type="email"
                />
              </v-col>

              <!-- Password -->
              <v-col cols="12">
                <v-text-field
                  v-model="newUser.password"
                  label="Password"
                  :rules="passwordRules"
                  required
                  prepend-inner-icon="$lock"
                  :append-inner-icon="showPassword ? '$eye-off' : '$eye'"
                  :type="showPassword ? 'text' : 'password'"
                  variant="outlined"
                  density="comfortable"
                  hint="Minimum 12 characters with uppercase, lowercase, numbers, and special characters"
                  persistent-hint
                  @click:append-inner="showPassword = !showPassword"
                />
              </v-col>

              <!-- Role -->
              <v-col cols="12">
                <v-select
                  v-model="newUser.role"
                  label="Role"
                  :items="roleOptions"
                  :rules="roleRules"
                  required
                  prepend-inner-icon="$shield-account"
                  variant="outlined"
                  density="comfortable"
                />
              </v-col>
            </v-row>

            <!-- Security Notice -->
            <v-alert
              type="info"
              variant="tonal"
              class="mt-4"
              icon="$information"
            >
              <div class="text-body-2">
                <strong>Security Notice:</strong>
                <ul class="mt-1 ml-4">
                  <li>Passwords are securely hashed using bcrypt</li>
                  <li>User creation is logged for audit purposes</li>
                  <li>Admin users can create other users and manage settings</li>
                  <li>Viewer users have read-only access to most features</li>
                </ul>
              </div>
            </v-alert>
          </v-card-text>

          <v-card-actions class="pa-6">
            <v-spacer />
            <v-btn
              variant="text"
              :disabled="creating"
              @click="cancelCreateUser"
            >
              Cancel
            </v-btn>
            <v-btn
              color="primary"
              type="submit"
              :loading="creating"
              :disabled="!createFormValid"
            >
              Create User
            </v-btn>
          </v-card-actions>
        </v-form>
      </v-card>
    </v-dialog>

    <!-- Reactivate Confirmation Dialog -->
    <v-dialog
      v-model="showReactivateDialog"
      max-width="500px"
    >
      <v-card>
        <v-card-title class="d-flex align-center text-success">
          <v-icon class="me-3">
            $account-check
          </v-icon>
          Reactivate User
        </v-card-title>

        <v-divider />

        <v-card-text v-if="userToReactivate">
          <p class="mb-4">
            Are you sure you want to reactivate user <strong>{{ userToReactivate.username }}</strong>?
          </p>

          <v-alert
            type="info"
            variant="tonal"
            class="mb-3"
          >
            <strong>This will:</strong>
            <ul class="mt-2">
              <li>Allow the user to log in again</li>
              <li>Restore access to all admin features based on their role</li>
            </ul>
          </v-alert>
        </v-card-text>

        <v-divider />

        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            :disabled="reactivating"
            @click="showReactivateDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="success"
            variant="flat"
            :loading="reactivating"
            @click="reactivateUserAction"
          >
            Reactivate User
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Deactivate Confirmation Dialog -->
    <v-dialog
      v-model="showDeactivateDialog"
      max-width="500px"
    >
      <v-card>
        <v-card-title class="d-flex align-center text-error">
          <v-icon class="me-3">
            $alert-circle
          </v-icon>
          Deactivate User
        </v-card-title>

        <v-divider />

        <v-card-text v-if="userToDeactivate">
          <p class="mb-4">
            Are you sure you want to deactivate user <strong>{{ userToDeactivate.username }}</strong>?
          </p>

          <v-alert
            type="warning"
            variant="tonal"
            class="mb-4"
          >
            <div class="text-body-2">
              <strong>This action will:</strong>
              <ul class="mt-2 ml-4">
                <li>Prevent the user from logging in</li>
                <li>Terminate all active sessions immediately</li>
                <li>Require admin intervention to reactivate</li>
              </ul>
            </div>
          </v-alert>

          <p class="text-body-2 text-medium-emphasis">
            This action can be reversed by reactivating the user account.
          </p>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            :disabled="deactivating"
            @click="showDeactivateDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="error"
            :loading="deactivating"
            @click="deactivateUserAction"
          >
            Deactivate User
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete User Confirmation Dialog -->
    <v-dialog
      v-model="showDeleteDialog"
      max-width="600px"
      persistent
    >
      <v-card v-if="userToDelete">
        <v-card-title class="d-flex align-center text-error">
          <v-icon
            class="me-3"
            color="error"
          >
            $delete-forever
          </v-icon>
          Permanently Delete User
        </v-card-title>

        <v-divider />

        <v-card-text class="pa-6">
          <v-alert
            type="error"
            variant="tonal"
            class="mb-6"
            icon="$alert-octagon"
          >
            <div class="text-body-1">
              <strong>⚠️ DANGER - This action cannot be undone!</strong>
            </div>
            <div class="text-body-2 mt-2">
              This will permanently delete the user <strong>{{ userToDelete.username }}</strong> 
              and all associated data including sessions and settings.
            </div>
          </v-alert>

          <div class="text-body-1 mb-4">
            This action will:
          </div>
          <ul class="text-body-2 mb-6 ml-4">
            <li>Permanently remove the user account</li>
            <li>Delete all user sessions immediately</li>
            <li>Remove all user-specific settings</li>
            <li>Cannot be reversed or undone</li>
          </ul>

          <v-divider class="my-4" />

          <div class="text-body-1 mb-3">
            <strong>Type "DELETE" to confirm:</strong>
          </div>
          <v-text-field
            v-model="deleteConfirmText"
            placeholder="Type DELETE to confirm"
            variant="outlined"
            density="comfortable"
            :color="deleteConfirmText === 'DELETE' ? 'success' : 'error'"
            hint="This confirmation is required for security"
            persistent-hint
          >
            <template #prepend-inner>
              <v-icon 
                :color="deleteConfirmText === 'DELETE' ? 'success' : 'error'"
              >
                {{ deleteConfirmText === 'DELETE' ? '$check-circle' : '$alert-circle' }}
              </v-icon>
            </template>
          </v-text-field>

          <v-alert
            v-if="deleteConfirmText && deleteConfirmText !== 'DELETE'"
            type="warning"
            variant="tonal"
            class="mt-4"
            density="compact"
          >
            Please type "DELETE" exactly as shown to confirm
          </v-alert>
        </v-card-text>

        <v-card-actions class="pa-6">
          <v-spacer />
          <v-btn
            variant="text"
            :disabled="deleting"
            @click="showDeleteDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="error"
            :loading="deleting"
            :disabled="deleteConfirmText !== 'DELETE'"
            @click="deleteUserAction"
          >
            <v-icon start>
              $delete-forever
            </v-icon>
            Delete Forever
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Bulk Delete Dialog -->
    <v-dialog
      v-model="showBulkDeleteDialog"
      max-width="600px"
      persistent
    >
      <v-card>
        <v-card-title class="text-h5 error--text">
          <v-icon
            start
            color="error"
          >
            $alert
          </v-icon>
          Bulk Delete Users
        </v-card-title>

        <v-card-text>
          <v-alert
            color="error"
            variant="tonal"
            class="mb-4"
          >
            <strong>WARNING:</strong> You are about to permanently delete {{ selectedUsers.length }} user{{ selectedUsers.length === 1 ? '' : 's' }}. This action cannot be undone.
          </v-alert>

          <div class="mb-4">
            <div class="text-subtitle-2 mb-2">
              Users to be deleted:
            </div>
            <v-list
              dense
              class="pa-0"
            >
              <v-list-item
                v-for="userId in selectedUsers.slice(0, 5)"
                :key="userId"
                density="compact"
              >
                <template #prepend>
                  <v-icon
                    size="small"
                    color="error"
                  >
                    $account-remove
                  </v-icon>
                </template>
                <v-list-item-title>
                  {{ getUserById(userId)?.username || 'Unknown User' }}
                </v-list-item-title>
                <v-list-item-subtitle v-if="getUserById(userId)?.email">
                  {{ getUserById(userId).email }}
                </v-list-item-subtitle>
              </v-list-item>
              <v-list-item
                v-if="selectedUsers.length > 5"
                density="compact"
              >
                <v-list-item-title class="text-medium-emphasis">
                  ... and {{ selectedUsers.length - 5 }} more
                </v-list-item-title>
              </v-list-item>
            </v-list>
          </div>

          <v-text-field
            v-model="bulkDeleteConfirmText"
            label="Type 'DELETE ALL' to confirm"
            placeholder="DELETE ALL"
            variant="outlined"
            density="compact"
            :rules="[v => v === 'DELETE ALL' || 'You must type DELETE ALL to confirm']"
            class="mt-4"
          />
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn
            color="grey"
            variant="text"
            :disabled="bulkDeleting"
            @click="cancelBulkDelete"
          >
            Cancel
          </v-btn>
          <v-btn
            color="error"
            variant="flat"
            :loading="bulkDeleting"
            :disabled="bulkDeleteConfirmText !== 'DELETE ALL'"
            @click="bulkDeleteUsers"
          >
            <v-icon start>
              $delete-forever
            </v-icon>
            Delete {{ selectedUsers.length }} User{{ selectedUsers.length === 1 ? '' : 's' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Bulk Deactivate Dialog -->
    <v-dialog
      v-model="showBulkDeactivateDialog"
      max-width="500px"
    >
      <v-card>
        <v-card-title class="text-h5">
          <v-icon
            start
            color="warning"
          >
            $account-off
          </v-icon>
          Deactivate Users
        </v-card-title>

        <v-card-text>
          <p>Are you sure you want to deactivate {{ selectedUsers.length }} user{{ selectedUsers.length === 1 ? '' : 's' }}?</p>
          
          <div class="mt-4">
            <div class="text-subtitle-2 mb-2">
              Users to be deactivated:
            </div>
            <v-list
              dense
              class="pa-0"
            >
              <v-list-item
                v-for="userId in selectedUsers.slice(0, 5)"
                :key="userId"
                density="compact"
              >
                <template #prepend>
                  <v-icon
                    size="small"
                    color="warning"
                  >
                    $account-off
                  </v-icon>
                </template>
                <v-list-item-title>
                  {{ getUserById(userId)?.username || 'Unknown User' }}
                </v-list-item-title>
              </v-list-item>
              <v-list-item
                v-if="selectedUsers.length > 5"
                density="compact"
              >
                <v-list-item-title class="text-medium-emphasis">
                  ... and {{ selectedUsers.length - 5 }} more
                </v-list-item-title>
              </v-list-item>
            </v-list>
          </div>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn
            color="grey"
            variant="text"
            :disabled="bulkDeactivating"
            @click="showBulkDeactivateDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="warning"
            variant="flat"
            :loading="bulkDeactivating"
            @click="bulkDeactivateUsers"
          >
            <v-icon start>
              $account-off
            </v-icon>
            Deactivate {{ selectedUsers.length }} User{{ selectedUsers.length === 1 ? '' : 's' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- User Details Dialog -->
    <v-dialog
      v-model="showDetailsDialog"
      max-width="700px"
    >
      <v-card v-if="userToView">
        <v-card-title class="d-flex align-center">
          <v-icon class="me-3">
            $account-details
          </v-icon>
          User Details: {{ userToView.username }}
        </v-card-title>

        <v-divider />

        <v-card-text class="pa-6">
          <v-row>
            <!-- Basic Information Section -->
            <v-col cols="12">
              <h3 class="text-h6 mb-4 d-flex align-center">
                <v-icon class="me-2">
                  $account
                </v-icon>
                Basic Information
              </h3>
              <v-row>
                <v-col
                  cols="12"
                  md="6"
                >
                  <v-text-field
                    label="Username"
                    :model-value="userToView.username"
                    readonly
                    variant="outlined"
                    density="comfortable"
                  />
                </v-col>
                <v-col
                  cols="12"
                  md="6"
                >
                  <v-text-field
                    label="Email"
                    :model-value="userToView.email || 'Not provided'"
                    readonly
                    variant="outlined"
                    density="comfortable"
                  />
                </v-col>
                <v-col
                  cols="12"
                  md="6"
                >
                  <v-text-field
                    label="Role"
                    :model-value="userToView.role"
                    readonly
                    variant="outlined"
                    density="comfortable"
                  >
                    <template #prepend-inner>
                      <v-chip
                        :color="getRoleColor(userToView.role)"
                        size="small"
                        variant="flat"
                      >
                        {{ userToView.role }}
                      </v-chip>
                    </template>
                  </v-text-field>
                </v-col>
                <v-col
                  cols="12"
                  md="6"
                >
                  <v-text-field
                    label="Status"
                    :model-value="userToView.is_active ? 'Active' : 'Inactive'"
                    readonly
                    variant="outlined"
                    density="comfortable"
                  >
                    <template #prepend-inner>
                      <v-chip
                        :color="userToView.is_active ? 'success' : 'error'"
                        size="small"
                        variant="flat"
                        :prepend-icon="userToView.is_active ? '$check-circle' : '$close-circle'"
                      >
                        {{ userToView.is_active ? 'Active' : 'Inactive' }}
                      </v-chip>
                    </template>
                  </v-text-field>
                </v-col>
              </v-row>
            </v-col>

            <!-- Account Activity Section -->
            <v-col cols="12">
              <v-divider class="my-4" />
              <h3 class="text-h6 mb-4 d-flex align-center">
                <v-icon class="me-2">
                  $clock-outline
                </v-icon>
                Account Activity
              </h3>
              <v-row>
                <v-col
                  cols="12"
                  md="6"
                >
                  <v-text-field
                    label="Account Created"
                    :model-value="formatDate(userToView.created_at)"
                    readonly
                    variant="outlined"
                    density="comfortable"
                  />
                </v-col>
                <v-col
                  cols="12"
                  md="6"
                >
                  <v-text-field
                    label="Last Login"
                    :model-value="userToView.last_login_at ? formatDate(userToView.last_login_at) : 'Never'"
                    readonly
                    variant="outlined"
                    density="comfortable"
                  />
                </v-col>
                <v-col
                  cols="12"
                  md="6"
                >
                  <v-text-field
                    label="User ID"
                    :model-value="userToView.id"
                    readonly
                    variant="outlined"
                    density="comfortable"
                  />
                </v-col>
                <v-col
                  cols="12"
                  md="6"
                >
                  <v-text-field
                    label="Account Age"
                    :model-value="getAccountAge(userToView.created_at)"
                    readonly
                    variant="outlined"
                    density="comfortable"
                  />
                </v-col>
              </v-row>
            </v-col>

            <!-- Security Information Section -->
            <v-col cols="12">
              <v-divider class="my-4" />
              <h3 class="text-h6 mb-4 d-flex align-center">
                <v-icon class="me-2">
                  $shield-check
                </v-icon>
                Security Information
              </h3>
              <v-row>
                <v-col cols="12">
                  <v-alert
                    :type="userToView.is_active ? 'success' : 'warning'"
                    variant="tonal"
                    class="mb-4"
                  >
                    <div class="d-flex align-center">
                      <v-icon class="me-2">
                        {{ userToView.is_active ? '$shield-check' : '$alert-circle' }}
                      </v-icon>
                      <div>
                        <strong>Account Status:</strong>
                        {{ userToView.is_active ? 'Active and accessible' : 'Deactivated - User cannot log in' }}
                      </div>
                    </div>
                  </v-alert>
                </v-col>
                <v-col cols="12">
                  <v-text-field
                    label="Password Security"
                    model-value="Encrypted with bcrypt"
                    readonly
                    variant="outlined"
                    density="comfortable"
                    prepend-inner-icon="$lock-check"
                  />
                </v-col>
              </v-row>
            </v-col>
          </v-row>
        </v-card-text>

        <v-card-actions class="pa-6">
          <v-spacer />
          <v-btn
            variant="text"
            @click="showDetailsDialog = false"
          >
            Close
          </v-btn>
          <v-btn
            color="primary"
            @click="showDetailsDialog = false"
          >
            Done
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useNotifications } from '../composables/useNotifications.js'
import { format } from 'date-fns'
import { useUsersStore } from '../stores/users.js'
import { useAdminStore } from '../stores/admin.js'
import { useTenantStore } from '../stores/tenant.js'
import { getEmailRules, getStrongPasswordRules } from '../utils/validation.js'

const { showSuccess, showError } = useNotifications()
const usersStore = useUsersStore()
const adminStore = useAdminStore()
const tenantStore = useTenantStore()
const { currentTenant } = storeToRefs(tenantStore)

// Local reactive state
const loading = ref(false)
const creating = ref(false)
const deactivating = ref(false)
const reactivating = ref(false)
const deleting = ref(false)
const showCreateDialog = ref(false)
const showDeactivateDialog = ref(false)
const showReactivateDialog = ref(false)
const showDeleteDialog = ref(false)
const showDetailsDialog = ref(false)
const showPassword = ref(false)
const createFormValid = ref(false)
const userToDeactivate = ref(null)
const userToReactivate = ref(null)
const userToDelete = ref(null)
const userToView = ref(null)
const createForm = ref(null)
const deleteConfirmText = ref('')

// Bulk operations state
const selectedUsers = ref([])
const showBulkDeleteDialog = ref(false)
const showBulkDeactivateDialog = ref(false)
const bulkDeleteConfirmText = ref('')
const bulkDeleting = ref(false)
const bulkDeactivating = ref(false)

const newUser = ref({
  username: '',
  email: '',
  password: '',
  role: 'viewer'
})

const headers = [
  { title: 'User', key: 'username', sortable: true },
  { title: 'Role', key: 'role', sortable: true },
  { title: 'Status', key: 'is_active', sortable: true },
  { title: 'Created', key: 'created_at', sortable: true },
  { title: 'Last Login', key: 'last_login_at', sortable: true },
  { title: 'Actions', key: 'actions', sortable: false, width: '100px' }
]

const roleOptions = [
  { title: 'Admin - Full access to all features', value: 'admin' },
  { title: 'Viewer - Read-only access', value: 'viewer' }
]

const usernameRules = [
  v => Boolean(v) || 'Username is required',
  v => (v && v.length >= 3) || 'Username must be at least 3 characters',
  v => (v && v.length <= 50) || 'Username must be less than 50 characters',
  v => /^[a-zA-Z0-9_]+$/.test(v) || 'Username can only contain letters, numbers, and underscores'
]

// Use shared validation utility functions for consistency
const emailRules = [
  v => !v || /.+@.+\..+/.test(v) || 'Email must be valid'
]

const passwordRules = getStrongPasswordRules()

const roleRules = [
  v => Boolean(v) || 'Role is required'
]

// Computed properties
const users = computed(() => {
  return usersStore.users
})

const storeLoading = computed(() => usersStore.loading)
const error = computed(() => usersStore.error)
const lastUpdated = computed(() => usersStore.lastUpdated)

// Bulk operation computed properties
const canBulkDelete = computed(() => {
  // Check if any selected user is the current user
  const currentUserId = adminStore.user?.id
  return selectedUsers.value.length > 0 && currentUserId && !selectedUsers.value.includes(currentUserId)
})

const canBulkDeactivate = computed(() => {
  // Check if any selected user is the current user or already inactive
  const currentUserId = adminStore.user?.id
  const hasCurrentUser = currentUserId && selectedUsers.value.includes(currentUserId)
  const allAlreadyInactive = selectedUsers.value.every(id => {
    const user = getUserById(id)
    return user && !user.is_active
  })
  return selectedUsers.value.length > 0 && !hasCurrentUser && !allAlreadyInactive
})

const getUserById = (id) => {
  return users.value.find(u => u.id === id)
}

// Methods
const loadUsers = async () => {
  await usersStore.fetchUsers()
}

const refreshUsers = async () => {
  console.log('🔄 [UsersView] Refreshing users, currentTenant:', currentTenant.value)
  await usersStore.fetchUsers()
}

const createUserAction = async () => {
  if (!createForm.value?.validate()) {
    return
  }

  creating.value = true
  try {
    const result = await usersStore.createUser({
      username: newUser.value.username,
      email: newUser.value.email || null,
      password: newUser.value.password,
      role: newUser.value.role
    })

    showSuccess(result?.message || 'User created successfully')
    showCreateDialog.value = false
    resetCreateForm()
  } catch (error) {
    const message = error.response?.data?.detail || 'Failed to create user'
    showError(message)
  } finally {
    creating.value = false
  }
}

const confirmDeactivateUser = (user) => {
  userToDeactivate.value = user
  showDeactivateDialog.value = true
}

const confirmReactivateUser = (user) => {
  userToReactivate.value = user
  showReactivateDialog.value = true
}

const viewUserDetails = (user) => {
  userToView.value = user
  showDetailsDialog.value = true
}

const confirmDeleteUser = (user) => {
  userToDelete.value = user
  deleteConfirmText.value = ''
  showDeleteDialog.value = true
}

const deactivateUserAction = async () => {
  if (!userToDeactivate.value) return

  deactivating.value = true
  try {
    const result = await usersStore.deactivateUser(userToDeactivate.value.id)
    showSuccess(result?.message || 'User deactivated successfully')
    showDeactivateDialog.value = false
    userToDeactivate.value = null
  } catch (error) {
    const message = error.response?.data?.detail || 'Failed to deactivate user'
    showError(message)
  } finally {
    deactivating.value = false
  }
}

const reactivateUserAction = async () => {
  if (!userToReactivate.value) return

  reactivating.value = true
  try {
    const result = await usersStore.reactivateUser(userToReactivate.value.id)
    showSuccess(result?.message || 'User reactivated successfully')
    showReactivateDialog.value = false
    userToReactivate.value = null
  } catch (error) {
    const message = error.response?.data?.detail || 'Failed to reactivate user'
    showError(message)
  } finally {
    reactivating.value = false
  }
}

const deleteUserAction = async () => {
  if (!userToDelete.value) return

  deleting.value = true
  try {
    const result = await usersStore.deleteUser(userToDelete.value.id)
    showSuccess(result?.message || 'User permanently deleted')
    showDeleteDialog.value = false
    userToDelete.value = null
    deleteConfirmText.value = ''
  } catch (error) {
    const message = error.response?.data?.detail || 'Failed to delete user'
    showError(message)
  } finally {
    deleting.value = false
  }
}

// Bulk operation methods
const clearSelection = () => {
  selectedUsers.value = []
}

const bulkDeleteUsers = async () => {
  if (bulkDeleteConfirmText.value !== 'DELETE ALL') return
  
  // Validate selected users before attempting bulk delete
  if (!selectedUsers.value || selectedUsers.value.length === 0) {
    showError('No users selected for deletion')
    return
  }
  
  if (selectedUsers.value.length > 50) {
    showError('Cannot delete more than 50 users at once')
    return
  }
  
  // Ensure all selected values are valid integers (accept both string and number IDs)
  const validUserIds = selectedUsers.value.filter(id => Number.isInteger(Number(id)) && Number(id) > 0)
  if (validUserIds.length !== selectedUsers.value.length) {
    showError('Invalid user selection. Please refresh and try again.')
    return
  }
  
  bulkDeleting.value = true
  
  try {
    const response = await usersStore.bulkDeleteUsers(validUserIds)
    
    // Handle response messaging
    if (response.success) {
      showSuccess(response.message || `Successfully deleted ${response.successful_deletions} user${response.successful_deletions === 1 ? '' : 's'}`)
    } else if (response.successful_deletions > 0) {
      // Partial success
      showSuccess(`${response.message} - ${response.successful_deletions} users deleted successfully`)
      
      // Show failure details if any
      if (response.failures && response.failures.length > 0) {
        const errorDetails = response.failures.map(f => 
          f.username ? `${f.username}: ${f.error}` : `User ${f.user_id}: ${f.error}`
        ).join('\n')
        showError(`Some deletions failed:\n${errorDetails}`)
      }
    } else {
      // Complete failure
      showError(response.message || 'Failed to delete any users')
      
      if (response.failures && response.failures.length > 0) {
        const errorDetails = response.failures.map(f => 
          f.username ? `${f.username}: ${f.error}` : `User ${f.user_id}: ${f.error}`
        ).join('\n')
        showError(`Deletion failures:\n${errorDetails}`)
      }
    }
    
    // Clear selection and close dialog
    clearSelection()
    showBulkDeleteDialog.value = false
    bulkDeleteConfirmText.value = ''
    
  } catch (error) {
    const message = error.response?.data?.detail || error.message || 'An unexpected error occurred during bulk delete'
    showError(message)
  } finally {
    bulkDeleting.value = false
  }
}

const cancelBulkDelete = () => {
  showBulkDeleteDialog.value = false
  bulkDeleteConfirmText.value = ''
}

const bulkDeactivateUsers = async () => {
  bulkDeactivating.value = true
  
  try {
    // Ensure all selected values are valid integers (accept both string and number IDs)
    const validUserIds = selectedUsers.value.filter(id => Number.isInteger(Number(id)) && Number(id) > 0)
    
    if (validUserIds.length === 0) {
      showError('No valid users selected for deactivation')
      return
    }

    // Use the bulk deactivate endpoint
    const response = await usersStore.bulkDeactivateUsers(validUserIds)
    
    // Handle response
    if (response.successful_deactivations > 0) {
      showSuccess(`Successfully deactivated ${response.successful_deactivations} user${response.successful_deactivations === 1 ? '' : 's'}`)
    }
    
    if (response.failed_deactivations > 0 && response.failed_user_ids) {
      const errorMsg = response.failed_user_ids.map(userId => {
        const user = getUserById(userId)
        return `${user?.username || `User ${userId}`}: Failed to deactivate`
      }).join('\n')
      showError(`Failed to deactivate ${response.failed_deactivations} user${response.failed_deactivations === 1 ? '' : 's'}:\n${errorMsg}`)
    }
    
    // Clear selection and close dialog
    clearSelection()
    showBulkDeactivateDialog.value = false
    
  } catch (error) {
    const errorMessage = error.response?.data?.detail || error.message || 'An unexpected error occurred during bulk deactivation'
    showError(errorMessage)
  } finally {
    bulkDeactivating.value = false
  }
}

const cancelCreateUser = () => {
  showCreateDialog.value = false
  resetCreateForm()
}

const resetCreateForm = () => {
  newUser.value = {
    username: '',
    email: '',
    password: '',
    role: 'viewer'
  }
  showPassword.value = false
  if (createForm.value) {
    createForm.value.resetValidation()
  }
}

const getRoleColor = (role) => {
  switch (role) {
    case 'admin': return 'primary'
    case 'viewer': return 'info'
    default: return 'grey'
  }
}

const formatDate = (dateString) => {
  if (!dateString) return 'Never'
  try {
    // If the date string doesn't include timezone info, append 'Z' to treat it as UTC
    const dateStr = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}/.test(dateString)
      ? `${dateString.replace(' ', 'T')  }Z`
      : dateString
    
    return format(new Date(dateStr), 'MMM d, yyyy h:mm a')
  } catch (error) {
    return 'Invalid date'
  }
}

const getAccountAge = (createdDate) => {
  if (!createdDate) return 'Unknown'
  try {
    // If the date string doesn't include timezone info, append 'Z' to treat it as UTC
    const dateStr = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}/.test(createdDate)
      ? `${createdDate.replace(' ', 'T')  }Z`
      : createdDate
    
    const created = new Date(dateStr)
    const now = new Date()
    const diffInMs = now - created
    const diffInDays = Math.floor(diffInMs / (1000 * 60 * 60 * 24))
    
    // Handle negative values (shouldn't happen with proper UTC parsing)
    if (diffInDays < 0) return 'Created today'
    if (diffInDays === 0) return 'Created today'
    if (diffInDays === 1) return '1 day old'
    if (diffInDays < 30) return `${diffInDays} days old`
    if (diffInDays < 365) {
      const months = Math.floor(diffInDays / 30)
      return months === 1 ? '1 month old' : `${months} months old`
    }
    const years = Math.floor(diffInDays / 365)
    return years === 1 ? '1 year old' : `${years} years old`
  } catch (error) {
    return 'Unknown'
  }
}

const isCurrentUser = (user) => {
  // Check if the user ID matches the authenticated user's ID
  return adminStore.user?.id === user.id
}

// Lifecycle
onMounted(async () => {
  console.log('✅ [UsersView] Component mounted, currentTenant:', currentTenant.value)
  await refreshUsers()
})

// Watch for tenant changes
watch(() => currentTenant.value?.slug, (newSlug, oldSlug) => {
  console.log('👀 [UsersView] Tenant slug watcher fired:', { oldSlug, newSlug, currentTenant: currentTenant.value })
  if (newSlug && newSlug !== oldSlug) {
    console.log('🔄 [UsersView] Tenant slug changed, refreshing users')
    refreshUsers()
  }
})
</script>

<style scoped>
.users-view {
  min-height: 100vh;
  background-color: rgb(var(--v-theme-background));
}

.v-data-table :deep(.v-data-table__td) {
  padding: 16px 12px;
}

.v-data-table :deep(.v-data-table__th) {
  font-weight: 600;
}
</style>