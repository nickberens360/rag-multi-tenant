<template>
  <div class="taxonomy-settings">
    <v-card elevation="2">
      <v-card-title class="d-flex align-center justify-space-between pa-6">
        <div class="text-h6 font-weight-bold">
          Search & Taxonomy
        </div>
        <div
          class="d-flex align-center"
          style="gap: 8px;"
        >
          <!-- Actions Menu -->
          <v-menu>
            <template #activator="{ props }">
              <v-btn 
                v-bind="props"
                variant="text"
                icon="$dots-vertical"
                density="comfortable"
              />
            </template>
            <v-list density="compact">
              <v-list-item @click="reloadFromServer">
                <template #prepend>
                  <v-icon>$undo</v-icon>
                </template>
                <v-list-item-title>Reload from Server</v-list-item-title>
              </v-list-item>
              <v-list-item @click="validateJson">
                <template #prepend>
                  <v-icon>$check</v-icon>
                </template>
                <v-list-item-title>Validate JSON</v-list-item-title>
              </v-list-item>
              <v-list-item @click="formatJson">
                <template #prepend>
                  <v-icon>$format-text</v-icon>
                </template>
                <v-list-item-title>Format JSON</v-list-item-title>
              </v-list-item>
              <v-list-item @click="openVersionHistory">
                <template #prepend>
                  <v-icon>$clock-outline</v-icon>
                </template>
                <v-list-item-title>Version History</v-list-item-title>
              </v-list-item>
              <v-list-item
                :disabled="!hasUnsavedChanges"
                @click="discardChanges"
              >
                <template #prepend>
                  <v-icon>$undo</v-icon>
                </template>
                <v-list-item-title>Discard Changes</v-list-item-title>
              </v-list-item>
              <v-list-item @click="openAutoGenerate">
                <template #prepend>
                  <v-icon>$auto-generate</v-icon>
                </template>
                <v-list-item-title>Auto-Generate Taxonomy</v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>

          <!-- Unsaved changes indicator -->
          <v-chip
            v-if="hasUnsavedChanges"
            color="warning"
            size="small"
            variant="tonal"
          >
            Unsaved changes
          </v-chip>

          <!-- Primary Action -->
          <v-btn
            variant="elevated"
            color="primary"
            prepend-icon="$save"
            class="ml-3"
            @click="publish"
          >
            Publish
          </v-btn>
          <v-btn
            variant="text"
            color="secondary"
            @click="saveSnapshot"
          >
            Save Snapshot
          </v-btn>
        </div>
      </v-card-title>

      <v-card-text class="pa-6">
        <v-alert
          v-if="error"
          type="error"
          variant="tonal"
          class="mb-4"
        >
          {{ error }}
        </v-alert>
        <!-- Validation success is shown via a toast -->

        <!-- Fallback File Upload Section -->
        <v-card
          variant="flat"
          class="mb-6"
        >
          <v-card-title class="text-subtitle-1 font-weight-bold pa-4 d-flex align-center">
            <v-icon
              color="primary"
              class="mr-2"
            >
              $upload
            </v-icon>
            Fallback Taxonomy File
            <v-chip
              :color="fallbackStatus.exists ? 'success' : 'warning'"
              size="small"
              variant="tonal"
              style="margin-left: 8px;"
            >
              {{ fallbackStatus.exists ? 'Present' : 'Not Found' }}
            </v-chip>
            <v-spacer />
          </v-card-title>
          <div class="px-4 pb-1 text-medium-emphasis">
            The fallback JSON is used only when no taxonomy is saved in Admin Settings. Uploading here writes
            a file on the server (backend/core/topic_taxonomy.json), replacing any existing fallback and
            refreshing the app to use it if needed.
          </div>
          <v-card-text
            class="pa-4 d-flex align-center"
            style="gap: 8px;"
          >
            <v-file-input
              v-model="fallbackFile"
              label="Upload JSON file"
              accept=".json,application/json"
              variant="outlined"
              density="comfortable"
              show-size
              prepend-icon="$file"
              hide-details
            />
            <!-- Fallback Actions Dropdown -->
            <v-menu>
              <template #activator="{ props }">
                <v-btn
                  v-bind="props"
                  variant="text"
                  icon="$dots-vertical"
                  density="comfortable"
                />
              </template>
              <v-list density="compact">
                <v-list-item @click="refreshFallbackStatus">
                  <template #prepend>
                    <v-icon>$refresh</v-icon>
                  </template>
                  <v-list-item-title>Refresh Status</v-list-item-title>
                </v-list-item>
                <v-list-item
                  :disabled="!fallbackStatus.exists"
                  @click="downloadFallback"
                >
                  <template #prepend>
                    <v-icon>$download</v-icon>
                  </template>
                  <v-list-item-title>Download Fallback</v-list-item-title>
                </v-list-item>
                <v-list-item @click="downloadFallbackTemplate">
                  <template #prepend>
                    <v-icon>$file</v-icon>
                  </template>
                  <v-list-item-title>Download Template</v-list-item-title>
                </v-list-item>
              </v-list>
            </v-menu>
            <v-btn
              color="primary"
              variant="elevated"
              :disabled="!fallbackFile"
              prepend-icon="$upload"
              @click="uploadFallback"
            >
              Upload
            </v-btn>
          </v-card-text>
        </v-card>

        

        <!-- Live Preview Section -->
        <v-card
          variant="flat"
          class="mb-6"
        >
          <v-card-title class="text-subtitle-1 font-weight-bold pa-4 d-flex align-center">
            <div class="d-flex align-center">
              <v-icon
                color="primary"
                class="mr-2"
              >
                $preview
              </v-icon>
              Live Preview
            </div>
            <v-spacer />
            <v-btn
              color="primary"
              variant="text"
              prepend-icon="$plus"
              @click="openAddCategory"
            >
              Add Category
            </v-btn>
          </v-card-title>
          <v-card-text class="pa-4">
            <div
              v-if="categoryList.length"
              class="preview-list"
            >
              <template
                v-for="(c, idx) in categoryList"
                :key="c.name"
              >
                <div class="preview-item">
                  <div class="item-title d-flex align-center">
                    <v-icon
                      size="18"
                      color="primary"
                      class="mr-1"
                    >
                      $tag
                    </v-icon>
                    {{ c.name }}
                    <v-spacer />
                    <v-btn
                      size="small"
                      variant="text"
                      icon="$pencil"
                      :title="`Edit ${c.name}`"
                      @click="openEditCategory(c)"
                    />
                    <v-btn
                      size="small"
                      variant="text"
                      color="error"
                      icon="$delete"
                      :title="`Delete ${c.name}`"
                      @click="deleteCategoryFromList(c.name)"
                    />
                  </div>
                  <div class="item-line">
                    <span class="label">Synonyms:</span>
                    <template v-if="(c.synonyms || []).length">
                      <span class="chips">
                        <v-chip
                          v-for="s in c.synonyms"
                          :key="`syn-${c.name}-${s}`"
                          size="small"
                          variant="tonal"
                          class="mr-1 mb-1"
                        >{{ s }}</v-chip>
                      </span>
                    </template>
                    <span v-else>—</span>
                  </div>
                  <div class="item-line">
                    <span class="label">Regex:</span>
                    {{ (c.regex || []).join(' | ') || '—' }}
                  </div>
                </div>
                <v-divider
                  v-if="idx < categoryList.length - 1"
                  class="mt-3 mb-0"
                />
              </template>
            </div>
            <div
              v-else
              class="text-medium-emphasis"
            >
              No categories parsed yet.
            </div>
          </v-card-text>
        </v-card>

        <!-- Taxonomy JSON Editor Section -->
        <v-card
          variant="flat"
          class="mb-6"
        >
          <v-card-title class="text-subtitle-1 font-weight-bold pa-4 d-flex align-center">
            <v-icon
              color="primary"
              class="mr-2"
            >
              $code
            </v-icon>
            Taxonomy JSON Editor
          </v-card-title>
          <v-card-text class="pa-4">
            <!-- Switch Rows -->
            <div class="setting-row">
              <div class="setting-content">
                <div class="setting-left">
                  <v-icon
                    color="primary"
                    class="setting-icon"
                  >
                    $save
                  </v-icon>
                  <div class="setting-info">
                    <div class="setting-title text-high-emphasis">
                      Auto-publish Deletes
                    </div>
                    <div class="setting-description text-medium-emphasis">
                      Immediately publish taxonomy changes after deleting a category. Turn off to stage deletes and publish later.
                    </div>
                  </div>
                </div>
                <div class="setting-right">
                  <v-switch
                    v-model="autoPublishDeletes"
                    color="primary"
                    inset
                    hide-details
                  />
                  <div class="setting-status text-medium-emphasis">
                    {{ autoPublishDeletes ? 'Enabled' : 'Disabled' }}
                  </div>
                </div>
              </div>
            </div>

            <v-divider class="my-1" />

            <div class="setting-row">
              <div class="setting-content">
                <div class="setting-left">
                  <v-icon
                    color="primary"
                    class="setting-icon"
                  >
                    $code
                  </v-icon>
                  <div class="setting-info">
                    <div class="setting-title text-high-emphasis">
                      Advanced JSON Editor
                    </div>
                    <div class="setting-description text-medium-emphasis">
                      Show the raw JSON editor for power users. The UI above covers common edits without dealing with JSON.
                    </div>
                  </div>
                </div>
                <div class="setting-right">
                  <v-switch
                    v-model="showAdvancedJsonEditor"
                    color="primary"
                    inset
                    hide-details
                  />
                  <div class="setting-status text-medium-emphasis">
                    {{ showAdvancedJsonEditor ? 'Shown' : 'Hidden' }}
                  </div>
                </div>
              </div>
            </div>

            <v-divider class="my-4" />

            <!-- Monaco Editor Container -->
            <v-card
              v-if="showAdvancedJsonEditor"
              variant="outlined"
              class="editor-container rounded-lg overflow-hidden mb-4"
            >
              <div
                ref="editorContainer"
                style="height: 450px; width: 100%;"
              />
            </v-card>

            <!-- Editor tools & actions toolbar -->
            <div
              class="mt-2 d-flex align-center"
              style="gap: 8px; flex-wrap: wrap;"
            >
              <v-btn
                variant="text"
                @click="openSnapshotDialog"
              >
                Save Snapshot
              </v-btn>
              <v-btn
                variant="text"
                @click="openAutoGenerate"
              >
                <v-icon
                  size="18"
                  class="mr-1"
                >
                  $auto-generate
                </v-icon>
                Auto-Generate
              </v-btn>
              <v-btn
                variant="text"
                :disabled="!!taxonomyJson"
                @click="insertTemplate"
              >
                Insert Template
              </v-btn>
              <v-btn
                variant="text"
                @click="openImportDialog"
              >
                Import JSON
              </v-btn>
              <v-btn
                variant="text"
                @click="exportJson"
              >
                Export JSON
              </v-btn>
              <v-btn
                variant="text"
                @click="validateJson"
              >
                Validate
              </v-btn>
              <v-btn
                variant="text"
                @click="formatJson"
              >
                Format
              </v-btn>
            </div>

            <div
              class="mt-4 d-flex align-center"
              style="gap: 8px;"
            >
              <v-text-field
                v-model="testQuery"
                label="Test Query"
                variant="outlined"
                density="comfortable"
                prepend-inner-icon="$search"
                class="flex-1"
                hide-details
              />
              <v-btn
                color="primary"
                variant="elevated"
                class="ml-6"
                @click="runTest"
              >
                Test Detection
              </v-btn>
            </div>

            <div
              v-if="testResult"
              class="mt-3 text-medium-emphasis"
            >
              Detected categories: <strong>{{ testResult.join(', ') || 'None' }}</strong>
            </div>
          </v-card-text>
        </v-card>

        <!-- Edit/Add Category Dialog -->
        <v-dialog
          v-model="categoryDialog.open"
          max-width="720"
        >
          <v-card>
            <v-card-title class="d-flex align-center">
              <v-icon
                color="primary"
                class="mr-2"
              >
                $tag
              </v-icon>
              {{
                categoryDialog.isNew ? 'Add Category' : `Edit Category: ${categoryDialog.originalName}`
              }}
            </v-card-title>
            <v-card-text>
              <div
                class="d-flex flex-column"
                style="gap: 16px;"
              >
                <v-text-field
                  v-model="categoryDialog.form.name"
                  label="Category Name"
                  variant="outlined"
                  density="comfortable"
                  :rules="[v => !!(v && v.trim()) || 'Name is required']"
                />

                <v-combobox
                  v-model="categoryDialog.form.synonyms"
                  label="Synonyms"
                  multiple
                  chips
                  clearable
                  variant="outlined"
                  density="comfortable"
                  :hide-no-data="true"
                  :delimiters="[',']"
                  hint="Press Enter or comma to add"
                  persistent-hint
                />

                <v-expansion-panels variant="accordion">
                  <v-expansion-panel>
                    <v-expansion-panel-title>
                      Advanced: Custom Regex (optional)
                    </v-expansion-panel-title>
                    <v-expansion-panel-text>
                      <v-combobox
                        v-model="categoryDialog.form.regex"
                        label="Regex Patterns"
                        multiple
                        chips
                        clearable
                        variant="outlined"
                        density="comfortable"
                        :hide-no-data="true"
                        :delimiters="[',']"
                        hint="For complex cases only; synonyms are auto-matched with word boundaries"
                        persistent-hint
                      />
                      <v-alert
                        type="info"
                        variant="tonal"
                        class="mt-3"
                      >
                        Synonyms are used to auto-generate safe, word-boundary
                        regex. Add custom regex only for
                        advanced matching (e.g., abbreviations, hyphenation).
                      </v-alert>
                    </v-expansion-panel-text>
                  </v-expansion-panel>
                </v-expansion-panels>

                <v-switch
                  v-model="categoryDialog.form.metadata.is_illustration_data"
                  color="primary"
                  inset
                  hide-details
                  label="Illustration/Creative Data"
                />
              </div>
            </v-card-text>
            <v-card-actions class="justify-end">
              <v-btn
                v-if="!categoryDialog.isNew"
                variant="text"
                color="error"
                class="mr-auto"
                @click="deleteCategory"
              >
                Delete
              </v-btn>
              <v-btn
                variant="text"
                @click="closeCategoryDialog"
              >
                Cancel
              </v-btn>
              <v-btn
                color="primary"
                variant="elevated"
                @click="saveCategory"
              >
                Save
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-dialog>
      </v-card-text>
    </v-card>
  </div>

  <!-- Undo deletion snackbar -->
  <v-snackbar
    v-model="undoSnack.open"
    timeout="6000"
    :scrim="false"
    :contained="true"
    :retain-focus="false"
    :close-on-back="false"
    location="bottom right"
  >
    Deleted '{{ undoSnack.name }}'.
    <template #actions>
      <v-btn
        variant="text"
        color="primary"
        @click="undoDelete"
      >
        Undo
      </v-btn>
    </template>
  </v-snackbar>

  <!-- Typed delete confirmation dialog -->
  <v-dialog
    v-model="deleteConfirm.open"
    max-width="520"
  >
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon
          color="error"
          class="mr-2"
        >
          $delete
        </v-icon>
        Confirm Delete
      </v-card-title>
      <v-card-text>
        <div class="mb-3">
          You are about to delete category
          <strong>{{ deleteConfirm.name }}</strong>.
        </div>
        <v-alert
          type="warning"
          variant="tonal"
          class="mb-4"
        >
          This will remove the category from the taxonomy and auto-publish the change.
        </v-alert>
        <v-text-field
          v-model="deleteConfirm.match"
          label="Type the category name to confirm"
          :placeholder="deleteConfirm.name"
          variant="outlined"
          density="comfortable"
          hide-details
          autofocus
        />
      </v-card-text>
      <v-card-actions class="justify-end">
        <v-btn
          variant="text"
          @click="deleteConfirm.open = false"
        >
          Cancel
        </v-btn>
        <v-btn
          color="error"
          variant="elevated"
          :disabled="deleteConfirm.match !== deleteConfirm.name"
          @click="confirmDeleteAction"
        >
          Delete
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <!-- Snapshot Dialog -->
  <v-dialog
    v-model="snapshot.open"
    max-width="520"
  >
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon
          color="primary"
          class="mr-2"
        >
          $save
        </v-icon>
        Save Snapshot
      </v-card-title>
      <v-card-text>
        <div class="mb-3">
          Add an optional note to this version.
        </div>
        <v-text-field
          v-model="snapshot.note"
          label="Note (optional)"
          variant="outlined"
          density="comfortable"
        />
      </v-card-text>
      <v-card-actions class="justify-end">
        <v-btn
          variant="text"
          @click="snapshot.open = false"
        >
          Cancel
        </v-btn>
        <v-btn
          color="primary"
          variant="elevated"
          @click="confirmSnapshot"
        >
          Save
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <!-- Discard Changes Dialog -->
  <v-dialog
    v-model="discard.open"
    max-width="520"
  >
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon
          color="error"
          class="mr-2"
        >
          $undo
        </v-icon>
        Discard Changes
      </v-card-title>
      <v-card-text>Revert the editor to the last loaded/published version?</v-card-text>
      <v-card-actions class="justify-end">
        <v-btn
          variant="text"
          @click="discard.open = false"
        >
          Cancel
        </v-btn>
        <v-btn
          color="error"
          variant="elevated"
          @click="confirmDiscard"
        >
          Discard
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <!-- Import JSON Dialog -->
  <v-dialog
    v-model="importJson.open"
    max-width="720"
  >
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon
          color="primary"
          class="mr-2"
        >
          $import
        </v-icon>
        Import Taxonomy JSON
      </v-card-title>
      <v-card-text>
        <div class="text-medium-emphasis mb-3">
          Paste a valid taxonomy JSON. This replaces the current draft.
        </div>
        <v-textarea
          v-model="importJson.text"
          rows="12"
          auto-grow
          variant="outlined"
          density="comfortable"
        />
      </v-card-text>
      <v-card-actions class="justify-end">
        <v-btn
          variant="text"
          @click="importJson.open = false"
        >
          Cancel
        </v-btn>
        <v-btn
          color="primary"
          variant="elevated"
          @click="confirmImportJson"
        >
          Import
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <!-- View Fallback Dialog -->
  <v-dialog
    v-model="fallbackView.open"
    max-width="860"
  >
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon
          color="primary"
          class="mr-2"
        >
          $view
        </v-icon>
        Fallback JSON
      </v-card-title>
      <v-card-text style="max-height: 60vh; overflow:auto;">
        <pre style="white-space: pre-wrap; word-break: break-word;">{{ fallbackView.text }}</pre>
      </v-card-text>
      <v-card-actions class="justify-end">
        <v-btn
          variant="text"
          @click="fallbackView.open = false"
        >
          Close
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <!-- Version History Dialog -->
  <v-dialog
    v-model="versions.open"
    max-width="860"
  >
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon
          color="primary"
          class="mr-2"
        >
          $clock-outline
        </v-icon>
        Taxonomy Versions
      </v-card-title>
      <v-card-text>
        <v-alert
          v-if="versions.error"
          type="error"
          variant="tonal"
          class="mb-3"
        >
          {{ versions.error }}
        </v-alert>
        <v-table density="comfortable">
          <thead>
            <tr>
              <th class="text-left">
                ID
              </th>
              <th class="text-left">
                Categories
              </th>
              <th class="text-left">
                Note
              </th>
              <th class="text-left">
                Saved At
              </th>
              <th class="text-left">
                User
              </th>
              <th class="text-left">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="v in versions.items"
              :key="v.id"
            >
              <td>{{ v.id }}</td>
              <td>{{ v.category_count }}</td>
              <td>{{ v.note || '—' }}</td>
              <td>{{ formatTs(v.created_at) }}</td>
              <td>{{ v.updated_by ?? '—' }}</td>
              <td>
                <v-btn
                  size="small"
                  variant="text"
                  @click="previewVersion(v.id)"
                >
                  Preview
                </v-btn>
                <v-btn
                  size="small"
                  variant="text"
                  @click="downloadVersion(v.id)"
                >
                  Download
                </v-btn>
                <v-btn
                  size="small"
                  variant="text"
                  @click="openDiffDialog(v.id)"
                >
                  Diff
                </v-btn>
                <v-btn
                  size="small"
                  color="primary"
                  variant="text"
                  @click="openRestoreDialog(v.id)"
                >
                  Restore
                </v-btn>
              </td>
            </tr>
            <tr v-if="!versions.items.length">
              <td
                colspan="6"
                class="text-medium-emphasis"
              >
                No versions yet.
              </td>
            </tr>
          </tbody>
        </v-table>
      </v-card-text>
      <v-card-actions class="justify-end">
        <v-btn
          variant="text"
          @click="versions.open = false"
        >
          Close
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <!-- Diff Dialog -->
  <v-dialog
    v-model="diff.open"
    max-width="960"
  >
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon
          color="primary"
          class="mr-2"
        >
          $code
        </v-icon>
        Differences vs Current Draft
      </v-card-title>
      <v-card-text>
        <div class="mb-3">
          Comparing current draft with version <strong>{{ diff.versionId }}</strong>
        </div>
        <div
          class="d-flex"
          style="gap: 24px; align-items: flex-start;"
        >
          <div style="flex:1;">
            <div class="text-subtitle-2 mb-1">
              Added
            </div>
            <div
              v-if="!diff.data.added.length"
              class="text-medium-emphasis"
            >
              —
            </div>
            <ul v-else>
              <li
                v-for="k in diff.data.added"
                :key="k"
              >
                {{ k }}
              </li>
            </ul>
          </div>
          <div style="flex:1;">
            <div class="text-subtitle-2 mb-1">
              Removed
            </div>
            <div
              v-if="!diff.data.removed.length"
              class="text-medium-emphasis"
            >
              —
            </div>
            <ul v-else>
              <li
                v-for="k in diff.data.removed"
                :key="k"
              >
                {{ k }}
              </li>
            </ul>
          </div>
          <div style="flex:1;">
            <div class="text-subtitle-2 mb-1">
              Changed
            </div>
            <div
              v-if="!diff.data.changed.length"
              class="text-medium-emphasis"
            >
              —
            </div>
            <ul v-else>
              <li
                v-for="k in diff.data.changed"
                :key="k"
              >
                {{ k }}
              </li>
            </ul>
          </div>
        </div>
        <v-divider class="my-4" />
        <v-switch
          v-model="diff.showJson"
          color="primary"
          inset
          hide-details
          label="Show JSON"
        />
        <div
          v-if="diff.showJson"
          class="d-flex mt-2"
          style="gap: 16px;"
        >
          <v-card
            variant="outlined"
            style="flex:1;"
          >
            <v-card-title class="text-subtitle-2">
              Current Draft
            </v-card-title>
            <v-card-text style="max-height: 300px; overflow:auto;">
              <pre style="white-space: pre-wrap; word-break: break-word;">{{ diff.left }}</pre>
            </v-card-text>
          </v-card>
          <v-card
            variant="outlined"
            style="flex:1;"
          >
            <v-card-title class="text-subtitle-2">
              Version {{ diff.versionId }}
            </v-card-title>
            <v-card-text style="max-height: 300px; overflow:auto;">
              <pre style="white-space: pre-wrap; word-break: break-word;">{{ diff.right }}</pre>
            </v-card-text>
          </v-card>
        </div>
      </v-card-text>
      <v-card-actions class="justify-end">
        <v-btn
          variant="text"
          @click="diff.open = false"
        >
          Close
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <!-- Restore Dialog with Note -->
  <v-dialog
    v-model="restore.open"
    max-width="520"
  >
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon
          color="primary"
          class="mr-2"
        >
          $undo
        </v-icon>
        Restore Version {{ restore.versionId }}
      </v-card-title>
      <v-card-text>
        <div class="mb-3">
          Optionally add a note for audit logs.
        </div>
        <v-text-field
          v-model="restore.note"
          label="Note (optional)"
          variant="outlined"
          density="comfortable"
        />
      </v-card-text>
      <v-card-actions class="justify-end">
        <v-btn
          variant="text"
          @click="restore.open = false"
        >
          Cancel
        </v-btn>
        <v-btn
          color="primary"
          variant="elevated"
          @click="confirmRestore"
        >
          Restore
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <!-- Auto-Generate Taxonomy Dialog -->
  <v-dialog
    v-model="autoGen.open"
    max-width="560"
  >
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon
          color="primary"
          class="mr-2"
        >
          $auto-generate
        </v-icon>
        Auto-Generate Taxonomy
      </v-card-title>
      <v-card-text>
        <div class="text-medium-emphasis mb-4">
          Proposes categories and synonyms from indexed content. Review and edit before publishing.
        </div>
        <div
          class="d-flex"
          style="gap: 16px;"
        >
          <v-text-field
            v-model.number="autoGen.options.max_categories"
            type="number"
            label="Max categories"
            min="3"
            max="20"
            variant="outlined"
            density="comfortable"
          />
          <v-text-field
            v-model.number="autoGen.options.max_synonyms"
            type="number"
            label="Max synonyms"
            min="3"
            max="30"
            variant="outlined"
            density="comfortable"
          />
        </div>
        <v-switch
          v-model="autoGen.options.include_filenames"
          color="primary"
          inset
          hide-details
          label="Include filename hints"
        />
      </v-card-text>
      <v-card-actions class="justify-end">
        <v-btn
          variant="text"
          @click="autoGen.open = false"
        >
          Cancel
        </v-btn>
        <v-btn
          color="primary"
          variant="elevated"
          @click="runAutoGenerate"
        >
          Generate
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import {
  ref,
  reactive,
  computed,
  onMounted,
  onUnmounted,
  watch,
  nextTick
} from 'vue';
import { useNotifications } from '@/composables/useNotifications';
import { useTheme } from 'vuetify';
import { storeToRefs } from 'pinia';
import { useTenantStore } from '@/stores/tenant';
import * as monaco from 'monaco-editor';
import { adminAPI } from '@/services/api';

const { showSuccess, showError } = useNotifications();
const theme = useTheme();
const tenantStore = useTenantStore();
const { currentTenant } = storeToRefs(tenantStore);

const error = ref('');
// Success validation messages are shown via global toasts
const taxonomyJson = ref('');
const testQuery = ref('');
const testResult = ref(null);
const editorContainer = ref(null);
const loading = ref(false);
const baselineJson = ref('');
const autoPublishDeletes = ref(true);
const showAdvancedJsonEditor = ref(false);
// Undo deletion state
const undoSnack = reactive({ open: false, name: '', data: null });
// Delete confirmation state
const deleteConfirm = reactive({ open: false, name: '', match: '', options: { closeDialog: false } });
// Fallback upload state
const fallbackFile = ref(null);
const fallbackStatus = reactive({ exists: false, invalid: false });
// Auto-generate state
const autoGen = reactive({
  open: false,
  options: { max_categories: 10, max_synonyms: 12, include_filenames: true }
});
// Versions state
const versions = reactive({ open: false, items: [], error: '' });
const diff = reactive({ open: false, versionId: null, data: { added: [], removed: [], changed: [] }, showJson: false, left: '', right: '' })
const restore = reactive({ open: false, versionId: null, note: '' })
const snapshot = reactive({ open: false, note: '' })
const discard = reactive({ open: false })
const fallbackView = reactive({ open: false, text: '' })
const importJson = reactive({ open: false, text: '' })

// Category edit dialog state
const categoryDialog = reactive({
  open: false,
  isNew: true,
  originalName: '',
  form: {
    name: '',
    synonyms: [],
    regex: [],
    metadata: { is_illustration_data: false },
  },
});

let editor = null;

// Computed property for Monaco theme based on Vuetify theme
const monacoTheme = computed(() =>
  theme.global.current.value.dark ? 'vs-dark' : 'vs'
);

// No static example; always show backend data or an empty editor if unavailable

// Watch for theme changes and update Monaco editor theme
watch(monacoTheme, (newTheme) => {
  if (editor) {
    monaco.editor.setTheme(newTheme);
  }
});

// Watch taxonomyJson changes and update the computed categoryList
watch(taxonomyJson, () => {
  if (editor && editor.getValue() !== taxonomyJson.value) {
    editor.setValue(taxonomyJson.value || '');
  }
});

// When advanced editor is toggled on, create Monaco instance; dispose when off
watch(showAdvancedJsonEditor, async (enabled) => {
  try {
    if (enabled) {
      await nextTick();
      setTimeout(() => {
        if (editorContainer.value) {
          createEditor();
          // Ensure editor content is in sync on first open
          if (editor && editor.getValue() !== (taxonomyJson.value || '')) {
            editor.setValue(taxonomyJson.value || '');
          }
        }
      }, 0);
    } else {
      // Hide editor: dispose to free resources
      cleanup();
    }
  } catch (e) {
    // non-fatal
  }
});

function formatTs(ts) {
  try { return new Date(ts).toLocaleString(); } catch { return ts; }
}

const hasUnsavedChanges = computed(() => {
  function normalize(s) {
    try { return JSON.stringify(JSON.parse(s || '{}')); } catch { return (s || '').trim(); }
  }
  return normalize(taxonomyJson.value) !== normalize(baselineJson.value);
});

onMounted(async () => {
  await reloadFromServer();
  await refreshFallbackStatus();

  // Wait for DOM to be ready, then create Monaco editor
  await nextTick();
  setTimeout(() => {
    if (editorContainer.value) {
      createEditor();
    }
  }, 100);
});

// Reload settings when tenant changes
watch(currentTenant, async (n, o) => {
  if (o && n && o.id !== n.id) {
    await reloadFromServer();
    await refreshFallbackStatus();
  }
}, { deep: true });

function openSnapshotDialog() {
  snapshot.note = '';
  snapshot.open = true;
}

async function confirmSnapshot() {
  try {
    let parsed;
    try {
      parsed = JSON.parse(taxonomyJson.value || '{}');
    } catch {
      showError('Invalid JSON');
      return;
    }
    if (!parsed || typeof parsed !== 'object') {
      showError('Invalid JSON');
      return;
    }
    const resp = await adminAPI.createTaxonomyVersion(parsed, snapshot.note || undefined);
    if (resp?.success) {
      showSuccess('Snapshot saved');
      snapshot.open = false;
    } else {
      showError('Failed to save snapshot');
    }
  } catch (e) {
    const detail = e?.response?.data?.detail || 'Error saving snapshot';
    showError(detail);
  }
}

function openVersionHistory() {
  versions.open = true;
  versions.error = '';
  loadVersions();
}

async function loadVersions() {
  try {
    const resp = await adminAPI.listTaxonomyVersions(50, 0);
    versions.items = Array.isArray(resp?.versions) ? resp.versions : [];
  } catch (e) {
    versions.error = 'Failed to load versions';
  }
}

async function previewVersion(id) {
  try {
    const resp = await adminAPI.getTaxonomyVersion(id);
    const settings = resp?.settings || null;
    if (settings && typeof settings === 'object') {
      const content = JSON.stringify(settings, null, 2);
      taxonomyJson.value = content;
      if (editor) editor.setValue(content);
      showSuccess(`Loaded version ${id} into editor (not published)`);
    } else {
      showError('Version payload not found');
    }
  } catch (e) {
    showError('Failed to load version');
  }
}

async function restoreVersion(id) {
  try {
    const ok = window.confirm(`Restore version ${id}? This will overwrite the current taxonomy and publish.`);
    if (!ok) return;
    const resp = await adminAPI.restoreTaxonomyVersion(id);
    if (resp?.success) {
      showSuccess('Restored version');
      await reloadFromServer();
    } else {
      showError('Restore failed');
    }
  } catch (e) {
    const detail = e?.response?.data?.detail || 'Failed to restore version';
    showError(detail);
  }
}

const categoryList = computed(() => {
  try {
    const obj = JSON.parse(taxonomyJson.value || '{}');
    const cats = obj?.categories || {};
    return Object.keys(cats).map(k => ({ name: k, ...cats[k] }));
  } catch (e) {
    return [];
  }
});

// Helpers to manipulate taxonomy JSON via structured edits
function getTaxonomyObject() {
  try {
    const obj = JSON.parse(taxonomyJson.value || '{}') || {};
    if (!obj.version) obj.version = '1';
    if (!obj.categories || typeof obj.categories !== 'object') obj.categories = {};
    return obj;
  } catch {
    return { version: '1', categories: {} };
  }
}

function setTaxonomyObject(obj) {
  const content = JSON.stringify(obj, null, 2);
  taxonomyJson.value = content;
  if (editor) {
    editor.setValue(content);
  }
}

function insertTemplate() {
  try {
    const current = (taxonomyJson.value || '').trim();
    if (current) return; // only insert when empty
    const template = {
      version: '1',
      categories: {
        example: { synonyms: ['sample', 'demo'], regex: [], metadata: { is_illustration_data: false } }
      }
    };
    setTaxonomyObject(template);
    showSuccess('Inserted template');
  } catch {
    // no-op
  }
}

function openImportDialog() {
  importJson.text = '';
  importJson.open = true;
}

function exportJson() {
  const text = taxonomyJson.value || '';
  try {
    // validate pretty
    const parsed = JSON.parse(text || '{}');
    const content = JSON.stringify(parsed, null, 2);
    triggerDownload(content, 'taxonomy_draft.json');
  } catch {
    // export raw if it can't parse (unlikely)
    triggerDownload(text, 'taxonomy_draft.json');
  }
}

function confirmImportJson() {
  try {
    const parsed = JSON.parse(importJson.text || '{}');
    const content = JSON.stringify(parsed, null, 2);
    taxonomyJson.value = content;
    if (editor) editor.setValue(content);
    showSuccess('Imported draft JSON');
    importJson.open = false;
  } catch (e) {
    showError('Invalid JSON — please fix and try again');
  }
}

function openEditCategory(cat) {
  categoryDialog.isNew = false;
  categoryDialog.originalName = cat.name;
  categoryDialog.form.name = cat.name;
  categoryDialog.form.synonyms = Array.isArray(cat.synonyms) ? [...cat.synonyms] : [];
  categoryDialog.form.regex = Array.isArray(cat.regex) ? [...cat.regex] : [];
  const meta = (cat.metadata && typeof cat.metadata === 'object') ? cat.metadata : {};
  categoryDialog.form.metadata = { is_illustration_data: Boolean(meta.is_illustration_data) };
  categoryDialog.open = true;
}

function openAddCategory() {
  categoryDialog.isNew = true;
  categoryDialog.originalName = '';
  categoryDialog.form.name = '';
  categoryDialog.form.synonyms = [];
  categoryDialog.form.regex = [];
  categoryDialog.form.metadata = { is_illustration_data: false };
  categoryDialog.open = true;
}

function closeCategoryDialog() {
  categoryDialog.open = false;
}

function saveCategory() {
  try {
    const name = (categoryDialog.form.name || '').trim();
    if (!name) {
      showError('Category name is required');
      return;
    }

    const obj = getTaxonomyObject();
    const categories = obj.categories;

    // Enforce unique name (handle rename)
    const isRename = !categoryDialog.isNew && name !== categoryDialog.originalName;
    if ((categoryDialog.isNew && categories[name]) || (isRename && categories[name])) {
      showError('Another category with this name already exists');
      return;
    }

    const entry = {
      synonyms: (categoryDialog.form.synonyms || []).map(s => String(s).trim()).filter(Boolean),
      regex: (categoryDialog.form.regex || []).map(s => String(s).trim()).filter(Boolean),
      metadata: { is_illustration_data: Boolean(categoryDialog.form.metadata.is_illustration_data) },
    };

    if (categoryDialog.isNew) {
      categories[name] = entry;
    } else if (isRename) {
      // Rename key while preserving order semantics minimally
      delete categories[categoryDialog.originalName];
      categories[name] = entry;
    } else {
      categories[name] = entry;
    }

    setTaxonomyObject(obj);
    showSuccess('Category saved (remember to Publish)');
    closeCategoryDialog();
  } catch (e) {
    showError('Failed to save category');
  }
}

function deleteCategory() {
  try {
    const name = categoryDialog.originalName;
    if (!name) {
      showError('No category selected to delete');
      return;
    }
    promptDeleteCategory(name, { closeDialog: true });
  } catch (e) {
    showError('Failed to delete category');
  }
}

function deleteCategoryFromList(name) {
  try {
    if (!name) {
      showError('No category selected to delete');
      return;
    }
    promptDeleteCategory(name, { closeDialog: false });
  } catch (e) {
    showError('Failed to delete category');
  }
}

function promptDeleteCategory(name, options = { closeDialog: false }) {
  deleteConfirm.name = name;
  deleteConfirm.match = '';
  deleteConfirm.options = options || { closeDialog: false };
  deleteConfirm.open = true;
}

async function confirmDeleteAction() {
  const name = deleteConfirm.name;
  const { closeDialog } = deleteConfirm.options || { closeDialog: false };
  deleteConfirm.open = false;
  await performDelete(name, { closeDialog, autoPublish: true });
}

async function performDelete(name, { closeDialog = false, autoPublish = true } = {}) {
  const obj = getTaxonomyObject();
  if (obj.categories && Object.prototype.hasOwnProperty.call(obj.categories, name)) {
    const prev = obj.categories[name];
    delete obj.categories[name];
    setTaxonomyObject(obj);
    if (closeDialog) categoryDialog.open = false;
    showUndo(name, prev);
    showSuccess(`Deleted '${name}' from taxonomy`);
    if (autoPublishDeletes.value && autoPublish) await publish();
  } else {
    showError(`Category '${name}' not found`);
  }
}

// Monaco editor functions
const createEditor = () => {
  if (!editorContainer.value) {
    return;
  }

  // Cleanup existing editor
  if (editor) {
    editor.dispose();
  }

  try {
    editor = monaco.editor.create(editorContainer.value, {
      value: taxonomyJson.value || '',
      language: 'json',
      theme: monacoTheme.value,
      automaticLayout: true,
      minimap: { enabled: true },
      scrollBeyondLastLine: false,
      wordWrap: 'on',
      fontSize: 14,
      lineNumbers: 'on',
      folding: true,
      bracketMatching: 'always',
      autoIndent: 'advanced',
      formatOnPaste: true,
      formatOnType: true
    });

    // Attach basic JSON schema for inline validation
    try {
      monaco.languages.json.jsonDefaults.setDiagnosticsOptions({
        validate: true,
        allowComments: false,
        schemas: [
          {
            uri: 'inmemory://model/taxonomy-schema.json',
            fileMatch: ['*'],
            schema: {
              type: 'object',
              required: ['categories'],
              properties: {
                version: { type: 'string' },
                categories: {
                  type: 'object',
                  additionalProperties: {
                    type: 'object',
                    properties: {
                      synonyms: { type: 'array', items: { type: 'string' } },
                      regex: { type: 'array', items: { type: 'string' } },
                      metadata: {
                        type: 'object',
                        properties: { is_illustration_data: { type: 'boolean' } },
                        additionalProperties: true
                      },
                      routing: {
                        type: 'object',
                        properties: {
                          k: { type: 'number' },
                          score_threshold: { type: 'number' }
                        },
                        additionalProperties: true
                      }
                    },
                    additionalProperties: true
                  }
                },
                router: {
                  type: 'object',
                  properties: {
                    ignore_words: { type: 'array', items: { type: 'string' } }
                  },
                  additionalProperties: true
                }
              },
              // Allow future extensions at the top-level to avoid false errors in editor
              additionalProperties: true
            }
          }
        ]
      });
    } catch (e) {
      // non-fatal schema init
    }

    // Listen for content changes
    editor.onDidChangeModelContent(() => {
      const newContent = editor.getValue();
      taxonomyJson.value = newContent;
    });

    // Add keyboard shortcuts
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
      publish();
    });

    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyMod.Shift | monaco.KeyCode.KeyF, () => {
      formatJson();
    });

  } catch (err) {
    console.error('Failed to initialize Monaco Editor:', err);
    error.value = 'Failed to initialize code editor';
  }
};

const formatJson = () => {
  if (!editor) return;

  try {
    const content = editor.getValue();
    const parsed = JSON.parse(content);
    const formatted = JSON.stringify(parsed, null, 2);

    // Update editor content
    editor.setValue(formatted);
    taxonomyJson.value = formatted;

    showSuccess('JSON formatted successfully!');
  } catch (err) {
    error.value = 'Invalid JSON format. Cannot format the content.';
    setTimeout(() => {
      error.value = '';
    }, 3000);
  }
};

const cleanup = () => {
  if (editor) {
    editor.dispose();
    editor = null;
  }
};

async function reloadFromServer() {
  try {
    loading.value = true;
    const resp = await adminAPI.getTaxonomySettings();
    const settings = (resp?.settings) || null;
    if (settings && typeof settings === 'object') {
      const content = JSON.stringify(settings, null, 2);
      taxonomyJson.value = content;
      if (editor) editor.setValue(content);
      showSuccess('Reloaded taxonomy from server');
      try { baselineJson.value = JSON.stringify(settings); } catch { baselineJson.value = content; }
    } else {
      taxonomyJson.value = '';
      if (editor) editor.setValue('');
      showError('Server did not return taxonomy');
    }
  } catch (e) {
    showError('Failed to load taxonomy from server');
  } finally {
    loading.value = false;
  }
}

function validateJson() {
  error.value = '';
  try {
    const obj = JSON.parse(taxonomyJson.value);
    if (!obj || typeof obj !== 'object') throw new Error('Top-level JSON must be an object');
    if (!obj.categories || typeof obj.categories !== 'object') throw new Error('Missing \'categories\' object');
    // Basic schema checks per category
    for (const [name, cfg] of Object.entries(obj.categories)) {
      if (typeof name !== 'string' || !name.trim()) throw new Error('Category name must be a non-empty string');
      if (typeof cfg !== 'object') throw new Error(`Category '${name}' must be an object`);
      if (cfg.synonyms && !Array.isArray(cfg.synonyms)) throw new Error(`Category '${name}': 'synonyms' must be an array`);
      if (cfg.regex && !Array.isArray(cfg.regex)) throw new Error(`Category '${name}': 'regex' must be an array`);
      // quick regex validation
      if (Array.isArray(cfg.regex)) {
        for (const p of cfg.regex) {
          try {
            new RegExp(p);
          } catch {
            throw new Error(`Category '${name}': invalid regex '${p}'`);
          }
        }
      }
    }
    showSuccess('Looks valid ✅');
  } catch (e) {
    error.value = e.message || 'Invalid JSON';
  }
}

async function publish() {
  // Publish to backend; no local draft persistence
  try {
    error.value = '';
    // Validate JSON locally first
    let parsed;
    try {
      parsed = JSON.parse(taxonomyJson.value);
    } catch (e) {
      error.value = 'Invalid JSON. Fix before publishing.';
      return;
    }

    loading.value = true;
    const resp = await adminAPI.updateTaxonomySettings(parsed);
    if (resp?.success) {
      showSuccess('Taxonomy published');
      try { baselineJson.value = JSON.stringify(parsed); } catch { baselineJson.value = taxonomyJson.value; }
      // no-op
    } else {
      showError('Publish failed');
    }
  } catch (e) {
    const detail = e?.response?.data?.detail || 'Failed to publish taxonomy';
    showError(detail);
  } finally {
    loading.value = false;
  }
}

function runTest() {
  testResult.value = [];
  try {
    const obj = JSON.parse(taxonomyJson.value);
    const text = (testQuery.value || '').toLowerCase();
    const results = new Set();
    for (const [name, cfg] of Object.entries(obj.categories || {})) {
      const syn = (cfg.synonyms || []).map((s) => (s || '').toLowerCase());
      if (syn.some(s => s && text.includes(s))) results.add(name);
      for (const pat of cfg.regex || []) {
        try {
          if (new RegExp(pat).test(text)) results.add(name);
        } catch { /* ignore */
        }
      }
    }
    testResult.value = Array.from(results);
  } catch (e) {
    error.value = 'Enter valid JSON before testing';
  }
}

function showUndo(name, data) {
  undoSnack.name = name;
  undoSnack.data = data;
  undoSnack.open = true;
}

async function undoDelete() {
  try {
    if (!undoSnack.name || !undoSnack.data) {
      undoSnack.open = false;
      return;
    }
    const obj = getTaxonomyObject();
    obj.categories[undoSnack.name] = undoSnack.data;
    setTaxonomyObject(obj);
    undoSnack.open = false;
    await publish();
    showSuccess(`Restored '${undoSnack.name}'`);
    // reset
    undoSnack.name = '';
    undoSnack.data = null;
  } catch (e) {
    showError('Failed to restore category');
  }
}

function openAutoGenerate() {
  autoGen.open = true;
}

async function runAutoGenerate() {
  try {
    const opts = { ...autoGen.options };
    const resp = await adminAPI.autoGenerateTaxonomy(opts);
    const settings = resp?.settings || null;
    if (settings && typeof settings === 'object') {
      const content = JSON.stringify(settings, null, 2);
      taxonomyJson.value = content;
      if (editor) editor.setValue(content);
      showSuccess('Auto-generated taxonomy loaded. Review and Publish.');
    } else {
      showError('Failed to generate taxonomy');
    }
  } catch (e) {
    const detail = e?.response?.data?.detail || 'Error auto-generating taxonomy';
    showError(detail);
  } finally {
    autoGen.open = false;
  }
}

async function refreshFallbackStatus() {
  try {
    const resp = await adminAPI.getTaxonomyFallback();
    fallbackStatus.exists = Boolean(resp?.exists);
    fallbackStatus.invalid = Boolean(resp?.invalid);
  } catch (e) {
    // non-fatal
  }
}

async function uploadFallback() {
  try {
    if (!fallbackFile.value) return;
    const file = Array.isArray(fallbackFile.value) ? fallbackFile.value[0] : fallbackFile.value;

    // Optional quick client-side validation
    const text = await file.text();
    try { JSON.parse(text); } catch { showError('File is not valid JSON'); return; }

    loading.value = true;
    const resp = await adminAPI.uploadTaxonomyFallback(file);
    if (resp?.success) {
      showSuccess('Fallback taxonomy uploaded');
      await refreshFallbackStatus();
    } else {
      showError('Upload failed');
    }
  } catch (e) {
    const detail = e?.response?.data?.detail || 'Failed to upload fallback file';
    showError(detail);
  } finally {
    loading.value = false;
  }
}

function discardChanges() {
  if (!hasUnsavedChanges.value) return;
  discard.open = true;
}

async function downloadFallback() {
  try {
    const resp = await adminAPI.getTaxonomyFallback();
    if (resp?.exists && resp?.settings) {
      const content = JSON.stringify(resp.settings, null, 2);
      triggerDownload(content, 'topic_taxonomy.fallback.json');
    } else if (resp?.exists && resp?.invalid) {
      showError('Fallback exists but is invalid JSON');
    } else {
      showError('No fallback file found');
    }
  } catch (e) {
    showError('Failed to download fallback');
  }
}

async function viewFallback() {
  try {
    const resp = await adminAPI.getTaxonomyFallback();
    if (resp?.exists && resp?.settings) {
      fallbackView.text = JSON.stringify(resp.settings, null, 2);
      fallbackView.open = true;
    } else if (resp?.exists && resp?.invalid) {
      showError('Fallback exists but is invalid JSON');
    } else {
      showError('No fallback file found');
    }
  } catch (e) {
    showError('Failed to view fallback');
  }
}

function downloadFallbackTemplate() {
  const template = {
    version: '1',
    categories: {
      example: {
        synonyms: ['sample', 'demo'],
        regex: [],
        metadata: { is_illustration_data: false },
      },
    },
  };
  const content = JSON.stringify(template, null, 2);
  triggerDownload(content, 'taxonomy_template.json');
}

function triggerDownload(text, filename) {
  try {
    const blob = new Blob([text], { type: 'application/json;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }, 0);
  } catch (e) {
    showError('Browser blocked download');
  }
}

onUnmounted(() => {
  cleanup();
});

function confirmDiscard() {
  let content = '';
  try { content = JSON.stringify(JSON.parse(baselineJson.value || '{}'), null, 2); } catch { content = baselineJson.value || ''; }
  taxonomyJson.value = content;
  if (editor) editor.setValue(content);
  showSuccess('Reverted to last saved version');
  discard.open = false;
}

async function downloadVersion(id) {
  try {
    const resp = await adminAPI.getTaxonomyVersion(id);
    const settings = resp?.settings || null;
    if (settings && typeof settings === 'object') {
      const content = JSON.stringify(settings, null, 2);
      triggerDownload(content, `taxonomy_version_${id}.json`);
    } else {
      showError('Version payload not found');
    }
  } catch (e) {
    showError('Failed to download version');
  }
}

function computeDiff(left, right) {
  const a = (left && typeof left === 'object') ? left : { categories: {} }
  const b = (right && typeof right === 'object') ? right : { categories: {} }
  const ac = a.categories || {}
  const bc = b.categories || {}
  const added = []
  const removed = []
  const changed = []
  const aKeys = new Set(Object.keys(ac))
  const bKeys = new Set(Object.keys(bc))
  for (const k of bKeys) if (!aKeys.has(k)) added.push(k)
  for (const k of aKeys) if (!bKeys.has(k)) removed.push(k)
  for (const k of aKeys) {
    if (bKeys.has(k)) {
      const av = ac[k] || {}
      const bv = bc[k] || {}
      const synA = JSON.stringify((av.synonyms || []).slice().sort())
      const synB = JSON.stringify((bv.synonyms || []).slice().sort())
      const rxA = JSON.stringify((av.regex || []).slice().sort())
      const rxB = JSON.stringify((bv.regex || []).slice().sort())
      if (synA !== synB || rxA !== rxB) changed.push(k)
    }
  }
  return { added, removed, changed }
}

async function diffVersion(id) {
  try {
    const resp = await adminAPI.getTaxonomyVersion(id)
    const ver = resp?.settings || null
    if (!ver) { showError('Version not found'); return }
    let cur
    try { cur = JSON.parse(taxonomyJson.value || '{}') } catch { cur = { categories: {} } }
    const d = computeDiff(cur, ver)
    diff.versionId = id
    diff.data = d
    diff.left = JSON.stringify(cur, null, 2)
    diff.right = JSON.stringify(ver, null, 2)
    diff.showJson = false
    diff.open = true
  } catch (e) {
    showError('Failed to diff version')
  }
}

function openDiffDialog(id) {
  diffVersion(id)
}

function openRestoreDialog(id) {
  restore.versionId = id
  restore.note = ''
  restore.open = true
}

async function confirmRestore() {
  try {
    const id = restore.versionId
    const resp = await adminAPI.restoreTaxonomyVersion(id, restore.note || undefined)
    if (resp?.success) {
      showSuccess('Restored version')
      restore.open = false
      versions.open = false
      await reloadFromServer()
    } else {
      showError('Restore failed')
    }
  } catch (e) {
    const detail = e?.response?.data?.detail || 'Failed to restore version'
    showError(detail)
  }
}

async function saveSnapshot() {
  try {
    let parsed
    try {
      parsed = JSON.parse(taxonomyJson.value || '{}')
    } catch (e) {
      showError('Invalid JSON');
      return;
    }
    if (!parsed || typeof parsed !== 'object') {
      showError('Invalid JSON');
      return;
    }
    const note = window.prompt('Add an optional note for this snapshot:', '') || undefined
    const resp = await adminAPI.createTaxonomyVersion(parsed, note)
    if (resp?.success) {
      showSuccess('Snapshot saved')
    } else {
      showError('Failed to save snapshot')
    }
  } catch (e) {
    const detail = e?.response?.data?.detail || 'Error saving snapshot'
    showError(detail)
  }
}
</script>

<style scoped>
.taxonomy-settings {
  max-width: 1200px;
}

.preview-item {
  padding: 8px 0;
}

.item-title {
  font-weight: 600;
  font-size: 1.1rem;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  color: rgb(var(--v-theme-on-surface));
}

.item-line {
  font-size: 0.875rem;
  margin-bottom: 4px;
  color: rgba(var(--v-theme-on-surface), 0.8);
}

.item-line .label {
  color: rgba(var(--v-theme-on-surface), 0.6);
  margin-right: 8px;
  font-weight: 500;
}

.chips {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 6px;
  vertical-align: middle;
}

/* Settings row layout (mirrors other settings views) */
.setting-row {
  padding: 16px 0;
}
.setting-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.setting-left {
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 0;
}
.setting-icon { margin-right: 12px; }
.setting-info { flex: 1; min-width: 0; }
.setting-title { font-size: 16px; font-weight: 500; margin-bottom: 2px; }
.setting-description { font-size: 14px; }
.setting-right { display: flex; align-items: center; gap: 10px; margin-left: 24px; }
.setting-actions { flex-wrap: wrap; gap: 8px; }
.setting-status { font-size: 13px; }

/* Monaco Editor Styles */
.editor-container {
  border: 2px solid rgba(var(--v-theme-primary), 0.12);
  transition: all 0.3s ease;
  background: rgb(var(--v-theme-surface));
}

.editor-container:hover {
  border-color: rgba(var(--v-theme-primary), 0.24);
}

/* Monaco Editor theme integration */
:deep(.monaco-editor) {
  border-radius: 8px;
  background: rgb(var(--v-theme-surface)) !important;
}

/* Light theme adjustments */
:deep(.monaco-editor.vs) {
  background: rgb(var(--v-theme-surface)) !important;
}

:deep(.monaco-editor.vs .margin) {
  background: rgb(var(--v-theme-surface)) !important;
}

:deep(.monaco-editor.vs .monaco-editor-background) {
  background: rgb(var(--v-theme-surface)) !important;
}

/* Dark theme adjustments */
:deep(.monaco-editor.vs-dark) {
  background: rgb(var(--v-theme-surface)) !important;
}

:deep(.monaco-editor.vs-dark .margin) {
  background: rgb(var(--v-theme-surface)) !important;
}

:deep(.monaco-editor.vs-dark .monaco-editor-background) {
  background: rgb(var(--v-theme-surface)) !important;
}

/* Ensure consistent scrollbar styling */
:deep(.monaco-scrollable-element > .scrollbar > .slider) {
  background: rgba(var(--v-theme-on-surface), 0.2);
}

:deep(.monaco-scrollable-element > .scrollbar > .slider:hover) {
  background: rgba(var(--v-theme-on-surface), 0.4);
}
</style>
