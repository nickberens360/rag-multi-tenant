<template>
  <v-card
    :loading="loading"
    class="chart-card"
  >
    <v-card-title class="d-flex align-center justify-space-between">
      <span>{{ title }}</span>
      
      <v-menu v-if="showExport">
        <template #activator="{ props }">
          <v-btn
            icon="$export"
            size="small"
            variant="text"
            v-bind="props"
          />
        </template>
        
        <v-list>
          <v-list-item @click="exportChart('png')">
            <v-list-item-title>Export as PNG</v-list-item-title>
          </v-list-item>
          <v-list-item @click="exportChart('svg')">
            <v-list-item-title>Export as SVG</v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>
    </v-card-title>

    <v-card-text>
      <div
        ref="chartContainer"
        class="chart-container"
        :style="{ height: `${height}px` }"
      >
        <canvas
          :id="chartId"
          ref="chartCanvas"
        />
        
        <div
          v-if="loading"
          class="loading-overlay"
        >
          <v-progress-circular
            indeterminate
            color="primary"
          />
        </div>
        
        <div
          v-else-if="!hasData"
          class="no-data-overlay"
        >
          <div class="text-center">
            <v-icon
              size="48"
              color="grey-lighten-1"
              class="mb-2"
            >
              $chart
            </v-icon>
            <div class="text-body-2 text-medium-emphasis">
              {{ noDataMessage }}
            </div>
          </div>
        </div>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  LineController,
  BarController,
  DoughnutController,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'
import { ChartTypes } from '@/types/admin'

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  LineController,
  BarController,
  DoughnutController,
  Title,
  Tooltip,
  Legend,
  Filler
)

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  data: {
    type: Object,
    required: true
  },
  type: {
    type: String,
    default: ChartTypes.LINE,
    validator: (value) => Object.values(ChartTypes).includes(value)
  },
  height: {
    type: Number,
    default: 400
  },
  loading: {
    type: Boolean,
    default: false
  },
  showExport: {
    type: Boolean,
    default: true
  },
  noDataMessage: {
    type: String,
    default: 'No data available'
  },
  options: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['chartClick'])

const chartCanvas = ref(null)
const chartContainer = ref(null)
const chart = ref(null)

const chartId = computed(() => `chart-${Math.random().toString(36).substring(7)}`)

const hasData = computed(() => {
  return props.data?.datasets?.length > 0 && props.data.datasets[0].data?.length > 0
})

const defaultOptions = computed(() => {
  const baseOptions = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      intersect: false,
      mode: 'index'
    },
    layout: {
      padding: {
        top: 10,
        right: 10,
        bottom: 10,
        left: 10
      }
    },
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          usePointStyle: true,
          padding: 20,
          boxWidth: 12,
          boxHeight: 12
        }
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleColor: 'white',
        bodyColor: 'white',
        borderColor: 'rgba(255, 255, 255, 0.2)',
        borderWidth: 1,
        cornerRadius: 8,
        displayColors: true,
        enabled: true
      }
    },
    scales: {},
    onClick: (event, elements) => {
      if (elements.length > 0) {
        emit('chartClick', { event, elements })
      }
    }
  }

  // Configure scales based on chart type
  if ([ChartTypes.LINE, ChartTypes.BAR].includes(props.type)) {
    baseOptions.scales = {
      x: {
        grid: {
          display: false
        },
        ticks: {
          maxRotation: 45
        }
      },
      y: {
        beginAtZero: true,
        grid: {
          color: 'rgba(0, 0, 0, 0.1)'
        }
      }
    }
  }

  // Line chart specific options
  if (props.type === ChartTypes.LINE) {
    baseOptions.elements = {
      point: {
        radius: 4,
        hoverRadius: 6
      },
      line: {
        tension: 0.4
      }
    }
  }

  // Doughnut chart specific options
  if (props.type === ChartTypes.DOUGHNUT) {
    baseOptions.cutout = '60%'
    baseOptions.plugins.legend = {
      position: 'bottom',
      labels: {
        usePointStyle: true,
        padding: 20
      }
    }
    baseOptions.animation = {
      animateScale: true,
      animateRotate: true
    }
    baseOptions.elements = {
      arc: {
        borderWidth: 2,
        borderColor: '#fff'
      }
    }
    // Remove scales for doughnut charts
    delete baseOptions.scales
  }

  return baseOptions
})

const chartOptions = computed(() => {
  return { ...defaultOptions.value, ...props.options }
})

const createChart = async () => {
  if (!chartCanvas.value || !hasData.value) return

  await nextTick()

  try {
    // Destroy existing chart
    if (chart.value) {
      chart.value.destroy()
      chart.value = null
    }

    const ctx = chartCanvas.value.getContext('2d')
    
    // Ensure data structure is valid and add missing properties
    const sanitizedDatasets = (props.data.datasets || []).map(dataset => ({
      ...dataset,
      hidden: dataset.hidden || false,
      clip: false,
      pointRadius: dataset.pointRadius || 4,
      pointHoverRadius: dataset.pointHoverRadius || 6
    }))

    const chartData = {
      ...props.data,
      datasets: sanitizedDatasets
    }

    chart.value = new ChartJS(ctx, {
      type: props.type,
      data: chartData,
      options: chartOptions.value
    })
  } catch (error) {
    console.error('Error creating chart:', error)
    console.error('Chart type:', props.type)
    console.error('Chart data:', props.data)
    console.error('Chart options:', chartOptions.value)
  }
}

const updateChart = () => {
  if (!chart.value || !hasData.value) return

  try {
    // Sanitize datasets before updating
    const sanitizedDatasets = (props.data.datasets || []).map(dataset => ({
      ...dataset,
      hidden: dataset.hidden || false,
      clip: false,
      pointRadius: dataset.pointRadius || 4,
      pointHoverRadius: dataset.pointHoverRadius || 6
    }))

    // Update chart data
    chart.value.data = {
      ...props.data,
      datasets: sanitizedDatasets
    }
    
    // Update options
    chart.value.options = chartOptions.value
    
    // Update chart with animation mode
    chart.value.update('none')
  } catch (error) {
    console.error('Error updating chart:', error)
    // If update fails, recreate the chart
    createChart()
  }
}

const exportChart = (format) => {
  if (!chart.value) return

  try {
    let dataURL
    
    if (format === 'png') {
      dataURL = chart.value.toBase64Image('image/png', 1.0)
    } else if (format === 'svg') {
      // For SVG export, we'd need a different approach or library
      console.warn('SVG export not implemented yet')
      return
    }

    // Create download link
    const link = document.createElement('a')
    link.download = `${props.title.toLowerCase().replace(/\s+/g, '-')}-chart.${format}`
    link.href = dataURL
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  } catch (error) {
    console.error('Error exporting chart:', error)
  }
}

// Watch for data changes
watch(() => props.data, async (newData, oldData) => {
  // Skip update if data hasn't really changed
  if (JSON.stringify(newData) === JSON.stringify(oldData)) return
  
  await nextTick()
  
  if (chart.value && hasData.value) {
    updateChart()
  } else if (hasData.value) {
    createChart()
  } else if (chart.value) {
    chart.value.destroy()
    chart.value = null
  }
}, { deep: true })

watch(() => hasData.value, async (newHasData) => {
  await nextTick()
  
  if (newHasData && !chart.value) {
    createChart()
  } else if (!newHasData && chart.value) {
    chart.value.destroy()
    chart.value = null
  }
})

// Watch for type changes
watch(() => props.type, () => {
  if (chart.value) {
    chart.value.destroy()
    chart.value = null
  }
  if (hasData.value) {
    createChart()
  }
})

onMounted(async () => {
  await nextTick()
  if (hasData.value) {
    createChart()
  }
})

onBeforeUnmount(() => {
  if (chart.value) {
    chart.value.destroy()
  }
})
</script>

<style scoped>
.chart-card {
  position: relative;
}

.chart-container {
  position: relative;
  width: 100%;
}

.loading-overlay,
.no-data-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.9);
  z-index: 10;
}

.no-data-overlay {
  background: rgba(248, 249, 250, 0.95);
}
</style>