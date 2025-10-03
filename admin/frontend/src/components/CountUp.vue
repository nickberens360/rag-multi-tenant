<template>
  <span>{{ displayValue }}</span>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { formatNumber } from '@/types/admin'

const props = defineProps({
  endVal: {
    type: Number,
    required: true
  },
  startVal: {
    type: Number,
    default: 0
  },
  duration: {
    type: Number,
    default: 2
  },
  decimals: {
    type: Number,
    default: 0
  },
  useFormat: {
    type: Boolean,
    default: true
  },
  useEasing: {
    type: Boolean,
    default: true
  }
})

const displayValue = ref(props.startVal)

const easeOutQuart = (t) => {
  return 1 - Math.pow(1 - t, 4)
}

let rafId = null
const animate = (from, to, duration) => {
  if (rafId) {
    cancelAnimationFrame(rafId)
    rafId = null
  }
  if (!Number.isFinite(duration) || duration <= 0) {
    displayValue.value = props.useFormat ? formatNumber(to) : to.toFixed(props.decimals)
    return
  }
  const startTime = Date.now()
  const range = to - from

  const step = () => {
    const now = Date.now()
    const elapsed = now - startTime
    const progress = Math.min(elapsed / (duration * 1000), 1)

    const easedProgress = props.useEasing ? easeOutQuart(progress) : progress
    const currentValue = from + (range * easedProgress)

    // Only apply formatting to the final value, use rounded integers during animation
    displayValue.value = props.useFormat ? Math.round(currentValue).toString() : currentValue.toFixed(props.decimals)

    if (progress < 1) {
      rafId = requestAnimationFrame(step)
    } else {
      // Apply proper formatting only to the final value
      displayValue.value = props.useFormat ? formatNumber(to) : to.toFixed(props.decimals)
      rafId = null
    }
  }

  rafId = requestAnimationFrame(step)
}

const startAnimation = () => {
  animate(props.startVal, props.endVal, props.duration)
}

watch(() => props.endVal, (newVal, oldVal) => {
  animate(oldVal || props.startVal, newVal, props.duration)
})

onMounted(() => {
  startAnimation()
})
</script>