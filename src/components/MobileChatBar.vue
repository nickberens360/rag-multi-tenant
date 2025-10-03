<template>
  <div v-if="isMobile" class="mobile-chat-bar">
    <button
      @click="openMobileMenu"
      class="mobile-menu-button"
      aria-label="Open chat history menu"
    >
      <font-awesome-icon
        icon="bars"
        class="menu-icon"
      />
    </button>
    <ChatStatus />
    <a
      v-if="false"
      href="/"
      class="mobile-menu-button mobile-menu-button--link"
    >
      <font-awesome-icon
        icon="house-chimney"
        class="base-icon"
      />
    </a>
  </div>
</template>

<script>
import { useStore } from '@nanostores/vue';
import { isMobileMenuOpen } from '../stores/ai.js';
import { useMobile } from '../composables/useMobile.js';
import ChatStatus from './ChatStatus.vue';

export default {
  name: 'MobileChatBar',
  components: { ChatStatus },
  setup() {
    const mobileMenuOpen = useStore(isMobileMenuOpen);
    const { isMobile } = useMobile();

    const openMobileMenu = () => {
      isMobileMenuOpen.set(true);
    };

    return {
      isMobile,
      isMobileMenuOpen: mobileMenuOpen,
      openMobileMenu
    };
  }
};
</script>

<style scoped>
.mobile-chat-bar {
  position: relative;
  padding: 0 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  pointer-events: none;
  background-color: #1a1a1a;
}
.mobile-menu-button {
  position: relative;
  pointer-events: auto;
  z-index: var(--z-index-mobile-nav);
  background-color: transparent;
  color: #d1d5db;
  outline: none;
  border: none;
  border-radius: 50%;
  padding: 0;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: none;
  transition: background-color 0.2s ease;
}

.mobile-menu-button--link {
  color: #d1d5db;
  text-decoration: none;
}

.mobile-menu-button:hover {
  background-color: transparent;
}

.menu-icon {
  font-size: 18px;
}
</style>
