<template>
  <v-select
    :model-value="modelValue"
    :items="timeRangeOptions"
    item-title="label"
    item-value="value"
    variant="outlined"
    density="compact"
    hide-details
    class="time-range-selector"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <template #prepend-inner>
      <v-icon size="small">
        $clock
      </v-icon>
    </template>
  </v-select>
</template>

<script setup>
import { computed } from 'vue'
import { TimeRanges } from '@/types/admin'

defineProps({
  modelValue: {
    type: String,
    default: TimeRanges.DAY
  }
})

defineEmits(['update:modelValue'])

const timeRangeOptions = computed(() => [
  { label: 'Last Hour', value: TimeRanges.HOUR },
  { label: 'Last 6 Hours', value: TimeRanges.SIX_HOURS },
  { label: 'Last 24 Hours', value: TimeRanges.DAY },
  { label: 'Last 7 Days', value: TimeRanges.WEEK },
  { label: 'Last 30 Days', value: TimeRanges.MONTH }
])
</script>

<style scoped>
.time-range-selector {
  max-width: 150px;
}
</style>