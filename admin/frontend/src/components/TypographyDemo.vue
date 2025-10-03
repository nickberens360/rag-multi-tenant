<template>
  <div class="typography-demo">
    <v-container>
      <!-- Header -->
      <div class="mb-8">
        <h1 class="text-h3 mb-4">
          Typography System
        </h1>
        <p class="text-body-1">
          Clean, simple typography using JetBrains Mono globally for the entire admin dashboard.
        </p>
      </div>

      <v-row>
        <!-- Standard Vuetify Typography -->
        <v-col
          cols="12"
          md="6"
        >
          <v-card class="pa-6 mb-6">
            <v-card-title class="text-h5 pb-4">
              Standard Vuetify Typography
            </v-card-title>
            
            <div class="mb-4">
              <div class="text-h1 mb-2">
                Heading 1
              </div>
              <div class="text-caption text-medium-emphasis">
                text-h1
              </div>
            </div>
            
            <div class="mb-4">
              <div class="text-h2 mb-2">
                Heading 2
              </div>
              <div class="text-caption text-medium-emphasis">
                text-h2
              </div>
            </div>
            
            <div class="mb-4">
              <div class="text-h3 mb-2">
                Heading 3
              </div>
              <div class="text-caption text-medium-emphasis">
                text-h3
              </div>
            </div>
            
            <div class="mb-4">
              <div class="text-h4 mb-2">
                Heading 4
              </div>
              <div class="text-caption text-medium-emphasis">
                text-h4
              </div>
            </div>
            
            <div class="mb-4">
              <div class="text-h5 mb-2">
                Heading 5
              </div>
              <div class="text-caption text-medium-emphasis">
                text-h5
              </div>
            </div>
            
            <div class="mb-4">
              <div class="text-h6 mb-2">
                Heading 6
              </div>
              <div class="text-caption text-medium-emphasis">
                text-h6
              </div>
            </div>
          </v-card>
        </v-col>

        <!-- Body Typography -->
        <v-col
          cols="12"
          md="6"
        >
          <v-card class="pa-6 mb-6">
            <v-card-title class="text-h5 pb-4">
              Body Typography
            </v-card-title>
            
            <div class="mb-4">
              <div class="text-body-1 mb-2">
                Body 1: This is regular body text with comfortable line height. 
                Perfect for paragraphs and longer text content. All using JetBrains Mono!
              </div>
              <div class="text-caption text-medium-emphasis">
                text-body-1
              </div>
            </div>
            
            <div class="mb-4">
              <div class="text-body-2 mb-2">
                Body 2: Smaller body text for secondary information and compact layouts.
                Good for captions and auxiliary content.
              </div>
              <div class="text-caption text-medium-emphasis">
                text-body-2
              </div>
            </div>
            
            <div class="mb-4">
              <div class="text-caption mb-2">
                Caption: Small text for labels, metadata, and fine print.
              </div>
              <div class="text-caption text-medium-emphasis">
                text-caption
              </div>
            </div>
            
            <div class="mb-4">
              <div class="text-overline mb-2">
                OVERLINE TEXT
              </div>
              <div class="text-caption text-medium-emphasis">
                text-overline
              </div>
            </div>
          </v-card>
        </v-col>

        <!-- Code Blocks -->
        <v-col
          cols="12"
          md="6"
        >
          <v-card class="pa-6 mb-6">
            <v-card-title class="text-h5 pb-4">
              Code Styling
            </v-card-title>
            
            <div class="mb-4">
              <div class="mb-2">
                <span>Inline code: </span>
                <span class="code-inline">const message = "Hello World"</span>
              </div>
              <div class="text-caption text-medium-emphasis">
                code-inline class
              </div>
            </div>
            
            <div class="mb-4">
              <div class="code-block mb-2">
                // Code block example
                function calculateMetrics(data) {
                return {
                total: data.length,
                average: data.reduce((a, b) => a + b, 0) / data.length
                };
                }
              </div>
              <div class="text-caption text-medium-emphasis">
                code-block class
              </div>
            </div>
          </v-card>
        </v-col>

        <!-- Admin Dashboard Examples -->
        <v-col
          cols="12"
          md="6"
        >
          <v-card class="pa-6 mb-6">
            <v-card-title class="text-h5 pb-4">
              Admin Dashboard Examples
            </v-card-title>
            
            <v-row>
              <v-col cols="6">
                <div class="text-center">
                  <div class="text-h4 font-weight-bold text-primary">
                    1,247
                  </div>
                  <div class="text-caption text-medium-emphasis">
                    Total Queries
                  </div>
                </div>
              </v-col>
              
              <v-col cols="6">
                <div class="text-center">
                  <div class="text-h4 font-weight-bold text-success">
                    98.2%
                  </div>
                  <div class="text-caption text-medium-emphasis">
                    Success Rate
                  </div>
                </div>
              </v-col>
            </v-row>
            
            <v-divider class="my-4" />
            
            <div class="mb-3">
              <div class="text-subtitle-1 font-weight-medium">
                Recent Query
              </div>
              <div class="code-block bg-surface-variant pa-3 rounded text-body-2">
                What is Nick's experience with Vue.js development?
              </div>
            </div>
          </v-card>
        </v-col>

        <!-- Vuetify Component Integration -->
        <v-col cols="12">
          <v-card class="pa-6">
            <v-card-title class="text-h5 pb-4">
              Component Integration
            </v-card-title>
            
            <v-row>
              <v-col
                cols="12"
                md="4"
              >
                <h6 class="text-h6 mb-3">
                  Buttons
                </h6>
                <div class="d-flex flex-column ga-2">
                  <v-btn
                    color="primary"
                    block
                  >
                    Primary Button
                  </v-btn>
                  <v-btn
                    color="secondary"
                    variant="outlined"
                    block
                  >
                    Secondary Button
                  </v-btn>
                  <v-btn
                    color="success"
                    variant="tonal"
                    block
                  >
                    Success Button
                  </v-btn>
                </div>
              </v-col>
              
              <v-col
                cols="12"
                md="4"
              >
                <h6 class="text-h6 mb-3">
                  Form Fields
                </h6>
                <div class="d-flex flex-column ga-2">
                  <v-text-field
                    label="Email Address"
                    placeholder="Enter your email"
                    variant="outlined"
                  />
                  <v-select
                    label="Select Option"
                    :items="['Option 1', 'Option 2', 'Option 3']"
                    variant="outlined"
                  />
                </div>
              </v-col>
              
              <v-col
                cols="12"
                md="4"
              >
                <h6 class="text-h6 mb-3">
                  Chips & Lists
                </h6>
                <div class="d-flex flex-wrap ga-2 mb-3">
                  <v-chip
                    color="primary"
                    size="small"
                  >
                    Vue.js
                  </v-chip>
                  <v-chip
                    color="secondary"
                    size="small"
                  >
                    TypeScript
                  </v-chip>
                  <v-chip
                    color="success"
                    size="small"
                  >
                    Vuetify
                  </v-chip>
                  <v-chip
                    color="info"
                    size="small"
                  >
                    JavaScript
                  </v-chip>
                </div>
                
                <v-list
                  density="compact"
                  class="bg-transparent"
                >
                  <v-list-item>
                    <v-list-item-title>Primary List Item</v-list-item-title>
                    <v-list-item-subtitle>Secondary text</v-list-item-subtitle>
                  </v-list-item>
                  <v-list-item>
                    <v-list-item-title>Another List Item</v-list-item-title>
                    <v-list-item-subtitle>With subtitle</v-list-item-subtitle>
                  </v-list-item>
                </v-list>
              </v-col>
            </v-row>
          </v-card>
        </v-col>
      </v-row>

      <!-- Font Info -->
      <v-row>
        <v-col cols="12">
          <v-alert
            type="info"
            variant="tonal"
            class="mt-4"
          >
            <v-alert-title>Simplified Typography System</v-alert-title>
            All text in this admin dashboard now uses <strong>JetBrains Mono</strong> globally. 
            No complex font variables or custom typography classes needed - just use standard Vuetify typography classes
            like <code>text-h1</code>, <code>text-body-1</code>, <code>text-caption</code>, etc.
          </v-alert>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup>
// No reactive data needed for this demo component
</script>

<style scoped>
.typography-demo {
  /* Additional styles if needed */
}

/* Ensure proper spacing in demo */
.v-card-title {
  border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.12);
}
</style>