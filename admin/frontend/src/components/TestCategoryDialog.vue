<template>
  <v-dialog
    v-model="dialog"
    max-width="500px"
    persistent
  >
    <v-card>
      <v-card-title>
        Test Dialog
      </v-card-title>
      
      <v-card-text>
        <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.</p>
        <p>Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.</p>
      </v-card-text>
      
      <v-card-actions>
        <v-spacer />
        <v-btn
          color="grey"
          variant="text"
          @click="cancel"
        >
          Cancel
        </v-btn>
        <v-btn
          color="primary"
          variant="text"
          @click="save"
        >
          Save
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
export default {
  name: 'TestCategoryDialog',
  props: {
    modelValue: {
      type: Boolean,
      default: false
    }
  },
  emits: ['update:modelValue', 'save', 'cancel'],
  computed: {
    dialog: {
      get() {
        return this.modelValue
      },
      set(value) {
        this.$emit('update:modelValue', value)
      }
    }
  },
  watch: {
    modelValue(newValue) {
      // Dialog visibility changed
    }
  },
  methods: {
    save() {
      this.$emit('save', { test: 'data' })
    },
    cancel() {
      this.$emit('cancel')
    }
  }
}
</script>