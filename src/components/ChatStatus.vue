<template>
  <div class="backend-status">
    <p
      v-if="backendStatusValue === 'online'"
      class="backend-status__item online"
    >
      <span v-if="showText" class="ml-2">online</span>
    </p>
    <p
      v-else
      class="backend-status__item offline"
    >
      <span v-if="showText" class="ml-2">offline</span>
    </p>
  </div>
</template>

<script>
import { useStore } from '@nanostores/vue';
import { backendStatus } from '../stores/backendStatus.js';

export default {
  name: 'ChatStatus',
  props: {
    showText: {
      type: Boolean,
      default: true
    }
  },
  setup() {
    const backendStatusValue = useStore(backendStatus);

    return {
      backendStatusValue
    };
  },
};
</script>

<style scoped>
.backend-status__item {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  padding: 0;
  margin: 0;
}

.backend-status__item::before {
  content: '';
  position: relative;
  height: 8px;
  width: 8px;
  display: inline-block;
  border-radius: 50%;
  background: #d1d5db;
}

.backend-status__item.online {
  color: #22c55e;
}

.backend-status__item.online::before {
  background: #22c55e;
}

.backend-status__item.offline {
  color: #ef4444;
}

.backend-status__item.offline::before {
  background: #ef4444;
}

.ml-2 {
  margin-left: 0.5rem;
}
</style>
