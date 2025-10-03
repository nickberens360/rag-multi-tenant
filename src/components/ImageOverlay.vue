<template>
  <div
    v-if="isOpen"
    class="image-overlay"
    @click="closeOverlay"
  >
    <div class="overlay-content">
      <img :src="imageSrc" alt="Full size image" />
      <button class="close-button" @click.stop="closeOverlay">×</button>
    </div>
  </div>
</template>

<script>
import { useStore } from '@nanostores/vue';
import { computed } from 'vue';
import { imageOverlayStore, closeImageOverlay } from '../stores/ui.js';

export default {
  name: 'ImageOverlay',
  setup() {
    const overlay = useStore(imageOverlayStore);

    const closeOverlay = () => {
      closeImageOverlay();
    };

    return {
      isOpen: computed(() => overlay.value.isOpen),
      imageSrc: computed(() => overlay.value.imageSrc),
      closeOverlay
    };
  }
};
</script>

<style scoped>
.image-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.9);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: var(--z-index-overlay);
  cursor: pointer;
}

.overlay-content {
  position: relative;
  max-width: 90%;
  max-height: 90%;
}

.overlay-content img {
  max-width: 100%;
  max-height: 90vh;
  object-fit: contain;
  border-radius: 4px;
}

.close-button {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: rgb(41, 41, 41);
  border: none;
  color: white;
  font-size: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background-color 0.2s;
  z-index: var(--z-index-content);
}
</style>
