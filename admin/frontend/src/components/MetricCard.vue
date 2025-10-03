<template>
  <v-card
    :loading="loading"
    elevation="1"
    :class="{ 'cursor-pointer': clickable }"
    @click="handleClick"
  >
    <v-card-text>
      <div class="d-flex align-center">
        <v-icon 
          v-if="icon"
          :color="color" 
          size="large" 
          class="me-3"
        >
          {{ icon }}
        </v-icon>
        <div>
          <div class="text-h6">
            <span v-if="typeof value === 'number'">
              <CountUp
                :end-val="value"
                :duration="1.5"
              />{{ unit }}
            </span>
            <span v-else>{{ value }}{{ unit }}</span>
          </div>
          <div class="text-body-2 text-medium-emphasis">
            {{ title }}
          </div>
        </div>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup>
import CountUp from '@/components/CountUp.vue'

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  value: {
    type: [Number, String],
    required: true
  },
  unit: {
    type: String,
    default: ''
  },
  icon: {
    type: String,
    default: ''
  },
  color: {
    type: String,
    default: 'primary'
  },
  loading: {
    type: Boolean,
    default: false
  },
  clickable: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['click'])

const handleClick = () => {
  if (props.clickable) {
    emit('click')
  }
}
</script>

<style scoped>
.cursor-pointer {
  cursor: pointer;
  transition: all 0.3s ease;
}

.cursor-pointer:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}
</style>