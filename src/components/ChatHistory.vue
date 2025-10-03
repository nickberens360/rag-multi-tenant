<template>
  <div>
    <!-- Mobile backdrop - only show after mount to prevent layout shift -->
    <div
      v-if="isMounted"
      class="mobile-backdrop"
      :class="{ 'is-visible': isMobile && isMobileMenuOpen }"
      @click="closeMobileMenu"
    ></div>
    <!-- Placeholder to maintain layout while mounting -->
    <div
      v-if="!isMounted"
      class="chat-history-drawer collapsed theme-dark"
    >
      <div class="drawer-content">
        <div class="drawer-header">
          <button class="base-icon-button collapse-icon-button">
            <font-awesome-icon class="base-icon" icon="bars" />
          </button>
          <button class="new-chat-button">
            <font-awesome-icon icon="pen-to-square" class="base-icon" />
          </button>
        </div>
        <div class="mt-auto">
          <ChatStatus :showText="false" />
        </div>
      </div>
    </div>
    <!-- Main drawer - only show after mount with correct mobile state -->
    <div
      v-if="isMounted"
      class="chat-history-drawer"
      :class="[
        `theme-${theme}`,
        {
          'collapsed': !isVisible && !isMobile,
          'mobile-overlay': isMobile && isMobileMenuOpen,
          'mobile-hidden': isMobile && !isMobileMenuOpen
        }
      ]"
    >
      <div class="drawer-content">
      <div class="drawer-header">
        <div v-if="!isMobile">
          <button
            @click="handleToggleVisibility"
            class="base-icon-button collapse-icon-button"
          >
            <font-awesome-icon
              class="base-icon"
              icon="bars"
            />
          </button>
          <a
            v-if="!isMobile && false"
            href="/"
            class="base-icon-button"
          >
            <font-awesome-icon
              icon="house-chimney"
              class="base-icon"
            />
          </a>
        </div>
        <button
          @click="handleCreateNewChat"
          class="new-chat-button"
          :disabled="hasTypingMessage || currentChatHasNoMessages || isProcessing"
          :class="{ 'disabled': hasTypingMessage || currentChatHasNoMessages || isProcessing }"
          :title="hasTypingMessage ? 'Cannot create new chat while message is typing' :
                  currentChatHasNoMessages ? 'Cannot create new chat when welcome screen is displayed' :
                  isProcessing ? 'Cannot create new chat while processing your prompt' :
                  'Create new chat'"
        >
          <font-awesome-icon
            icon="pen-to-square"
            class="base-icon"
          />
          <span
            v-if="isVisible || isMobile"
            class="ml-2 fadeable-content"
            :class="{ 'content-visible': isDrawerFullyVisible }"
          >New Chat</span>
        </button>
        <button
          v-if="isMobile"
          @click="closeMobileMenu"
          class="base-icon-button mobile-close-button fadeable-content"
          :class="{ 'content-visible': isDrawerFullyVisible }"
        >
          <font-awesome-icon
            class="base-icon"
            icon="times"
          />
        </button>
      </div>
      <p
        v-if="isVisible || isMobile"
        class="history-heading fadeable-content"
        :class="{ 'content-visible': isDrawerFullyVisible }"
      >Recent</p>
      <div
        :class="{ 'disabled-history-items': hasTypingMessage || isProcessing }"
      >
        <div
          v-if="isVisible || isMobile"
          class="history-list fadeable-content"
          :class="{ 'content-visible': isDrawerFullyVisible }"
        >
          <div
            v-for="chat in chatList"
            :key="chat.id"
            :class="['history-item', { 'active': chat.id === currentChatId }]"

            @click="handleSelectChat(chat.id)"
          >
            {{ chat.title }}
          </div>
        </div>
        <div v-else>
          <div
            class="history-item-collapsed"
            @click="toggleVisibility"
          >
            {{ chatList.length }}
          </div>
        </div>
      </div>
      <div v-if="false" class="mt-auto">
        <p
          v-if="isVisible || isMobile"
          class="text-center text-italic text-hint"
        >Having issues? Try clearing localStorage.</p>
        <button
          @click="clearLocalStorage"
          class="clear-storage-button"
        >
          <font-awesome-icon
            icon="trash"
            class="base-icon"
          />
          <span
            v-if="isVisible || isMobile"
            class="ml-2"
          >Clear localStorage</span>
        </button>
      </div>
      <div class="mt-auto">
        <ChatStatus :showText="isVisible || isMobile" />
      </div>
    </div>
    </div>
  </div>
</template>

<script>
import { useStore } from '@nanostores/vue';
import ChatStatus from './ChatStatus.vue';
import {
  allChats,
  activeChatId,
  createNewChat,
  selectChat,
  isChatHistoryVisible,
  isPendingNewChat,
  isChatProcessing,
  isMobileMenuOpen
} from '../stores/ai.js';
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { useMobile } from '../composables/useMobile.js';

export default {
  name: 'ChatHistory',
  components: {
    ChatStatus
  },
  props: {
    theme: {
      type: String,
      default: 'dark',
      validator: (value) => ['light', 'dark'].includes(value)
    }
  },
  setup() {
    const chats = useStore(allChats);
    const currentChatId = useStore(activeChatId);
    const isVisible = useStore(isChatHistoryVisible);
    const isProcessing = useStore(isChatProcessing);
    const mobileMenuOpen = useStore(isMobileMenuOpen);
    const isDrawerFullyVisible = ref(false);

    // Constants
    const DRAWER_ANIMATION_DURATION = 300; // Match the CSS transition duration
    let fadeTimer;

    // Use mobile detection composable
    const { isMobile, isMounted } = useMobile();

    // Check if any message across ALL chats is currently typing
    const hasTypingMessage = computed(() => {
      const allChatsData = chats.value;

      // Check all chats for typing messages
      for (const chatId in allChatsData) {
        const chat = allChatsData[chatId];
        if (chat.messages && chat.messages.some(msg => msg.isTyping)) {
          return true;
        }
      }

      return false;
    });

    // Add computed property to check if the current chat has no messages
    const currentChatHasNoMessages = computed(() => {
      // If there's no current chat ID, return true (welcome screen is shown)
      if (!currentChatId.value) return true;

      // Get the current chat
      const currentChat = chats.value[currentChatId.value];

      // If the chat doesn't exist or has no messages, return true
      return !currentChat || !currentChat.messages || currentChat.messages.length === 0;
    });

    // Convert the map of chats into a sorted array for display (newest first).
    const chatList = computed(() => {
      return Object.values(chats.value).sort((a, b) => b.id.localeCompare(a.id));
    });

    // Helper function to manage drawer content visibility
    const setDrawerContentVisibility = (visible) => {
      clearTimeout(fadeTimer);
      if (visible) {
        fadeTimer = setTimeout(() => {
          isDrawerFullyVisible.value = true;
        }, DRAWER_ANIMATION_DURATION);
      } else {
        isDrawerFullyVisible.value = false;
      }
    };

    const toggleVisibility = () => {
      const newVisibilityState = !isVisible.value;
      isChatHistoryVisible.set(newVisibilityState);
      setDrawerContentVisibility(newVisibilityState);
    };

    const handleToggleVisibility = () => {
      if (isMobile.value) {
        // On mobile, toggle the mobile menu
        isMobileMenuOpen.set(!mobileMenuOpen.value);
      } else {
        // On desktop, toggle the rail state
        toggleVisibility();
      }

    };

    const closeMobileMenu = () => {
      isMobileMenuOpen.set(false);
    };

    // Track the drawer state before it was collapsed due to screen size
    const wasVisibleBeforeCollapse = ref(null);

    // Watch for mobile state changes to handle transitions
    watch(isMobile, (newIsMobile, oldIsMobile) => {
      if (newIsMobile && !oldIsMobile) {
        // Transitioning to mobile
        if (isVisible.value && wasVisibleBeforeCollapse.value === null) {
          wasVisibleBeforeCollapse.value = true;
        }
        // This is needed to ensure the main content layout adjusts correctly on mobile.
        isChatHistoryVisible.set(false);
        // Close mobile menu when transitioning to mobile
        isMobileMenuOpen.set(false);
        isDrawerFullyVisible.value = false;
      } else if (!newIsMobile && oldIsMobile) {
        // Transitioning from mobile to desktop
        if (wasVisibleBeforeCollapse.value !== null) {
          isChatHistoryVisible.set(wasVisibleBeforeCollapse.value);
          wasVisibleBeforeCollapse.value = null;
        }
        // Ensure mobile menu is closed when going to desktop
        isMobileMenuOpen.set(false);
        // Update drawer content visibility based on desktop state
        if (isVisible.value) {
          setDrawerContentVisibility(true);
        }
      }
    });

    // Watch for mobile menu changes to handle content visibility
    watch(mobileMenuOpen, (isOpen) => {
      if (isMobile.value) {
        setDrawerContentVisibility(isOpen);
      }
    });

    // Modified createNewChat function that checks for empty messages and closes the drawer on mobile
    const handleCreateNewChat = () => {
      // Don't allow new chat creation if there's a typing message or if processing
      if (hasTypingMessage.value || isProcessing.value) {
        // Cannot create new chat while message is typing or processing
        return;
      }

      // Get the current active chat
      const currentChat = chats.value[currentChatId.value];

      // If there's no current chat or it has messages, set the pending state
      if (!currentChat || currentChat.messages.length > 0) {
        // Instead of creating a new chat immediately, set the pending state
        isPendingNewChat.set(true);

        // Clear the current chat if it has messages
        if (currentChat && currentChat.messages.length > 0) {
          activeChatId.set(null);
        }
      }

      // If on mobile, close the mobile menu
      if (isMobile.value) {
        isMobileMenuOpen.set(false);
      }
    };

    // Add a wrapper for selectChat to close the drawer on mobile
    const handleSelectChat = (chatId) => {
      // Call the original selectChat function
      selectChat(chatId);

      // If on mobile, close the mobile menu
      if (isMobile.value) {
        isMobileMenuOpen.set(false);
      }
    };

    onMounted(() => {
      // Note: Resize listener is now handled by useMobile composable
      // Set initial state for drawer content visibility
      isDrawerFullyVisible.value = isVisible.value || (isMobile.value && mobileMenuOpen.value);
    });

    onUnmounted(() => {
      clearTimeout(fadeTimer);
    });

    // Add the clearLocalStorage function
    const clearLocalStorage = () => {
      if (confirm('Are you sure you want to clear all chat history? This action cannot be undone.')) {
        localStorage.clear();
        window.location.reload(); // Reload the page to reflect changes
      }
    };

    return {
      chatList,
      currentChatId,
      currentChatHasNoMessages,
      hasTypingMessage,
      isProcessing,
      handleCreateNewChat,
      handleSelectChat,
      isVisible,
      isMobile,
      isMounted,
      isMobileMenuOpen: mobileMenuOpen,
      handleToggleVisibility,
      closeMobileMenu,
      clearLocalStorage,
      isDrawerFullyVisible
    };
  },
};
</script>

<style scoped>
.chat-history-drawer {
  width: 280px;
  background-color: #111111;
  color: #d1d5db;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #333333;
  flex-shrink: 0;
  transition: width 0.3s ease;
  position: relative;
  height: 100%;
}

/* Mobile states */
@media (max-width: 768px) {
  .chat-history-drawer {
    position: fixed;
    top: var(--site-header-height, 0);
    bottom: 0;
    left: 0;
    height: 100vh;
    z-index: var(--z-index-drawer);
    transform: translateX(-100%);
    transition: transform 0.3s ease;
  }

  .chat-history-drawer.mobile-overlay {
    transform: translateX(0);
    box-shadow: 2px 0 10px rgba(0, 0, 0, 0.3);
  }

  .chat-history-drawer.mobile-hidden {
    transform: translateX(-100%);
  }
}

/* Mobile backdrop */
.mobile-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: var(--z-index-overlay);
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
}

.mobile-backdrop.is-visible {
  opacity: 1;
  pointer-events: auto;
}

/* Drawer content wrapper */
.drawer-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  position: relative;
  z-index: var(--z-index-base);
}

/* Fadeable content that should transition */
.fadeable-content {
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
}

.fadeable-content.content-visible {
  opacity: 1;
  pointer-events: auto;
}

.base-icon-button {
  background: none;
  color: #d1d5db;
  border: none;
  border-radius: 50%;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 12px;
}

.base-icon {
  font-size: 16px;
  transition: transform 0.2s ease;
  flex-shrink: 0;
}

.mobile-close-button {
  position: absolute;
  right: 0;
  top: -2px;
}

.collapsed {
  width: 50px;
  padding: 1rem 0.5rem;
}

.new-chat-button {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  left: 4px;
  border: none;
  background: none !important;
  margin-bottom: 1rem;
  outline: none;
  color: white;
  cursor: pointer;
  transition: opacity 0.2s ease;
  height: 22px;
}

.collapse-icon-button {
  margin-bottom: 1.5rem;
}

.drawer-header {
  margin-bottom: 1rem;
  position: relative;
}

.history-heading {
  margin-top: 0;
  margin-bottom: 1rem;
  font-size: .75rem;
}

.collapsed .history-item-collapsed {
  margin-top: 0 !important;
}

.new-chat-button:disabled,
.new-chat-button.disabled {
  background-color: #333333;
  opacity: 0.5;
  cursor: not-allowed;
}

.new-chat-button:disabled:hover,
.new-chat-button.disabled:hover {
  opacity: 0.5;
}

.history-list {
  overflow-y: auto;
  flex-grow: 1;
}

.history-item {
  padding: 0.75rem;
  border-radius: 100px;
  font-size: 14px;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: #6c7889;
  transition: background-color 0.2s;
  margin-bottom: 0.5rem;
}

.history-item:hover {
  background-color: #222222;
}

.history-item.active {
  background-color: #1c2539;
  font-weight: bold;
  color: #f9fafb;
  padding-left: 1rem;
}

.history-item-collapsed {
  display: flex;
  flex-direction: column;
  justify-content: center;
  text-align: center;
  color: #c0c9d4;
  cursor: pointer;
  height: 30px;
  width: 30px;
  border-radius: 50%;
  background-color: #213e6b;
  font-size: 12px;
  font-weight: bold;
  position: relative;
}

.history-item-collapsed::after {
  content: '';
  position: absolute;
  width: 0;
  height: 0;
  border-left: 8px solid #213e6b;
  border-top: 8px solid transparent;
  border-bottom: 8px solid transparent;
  right: -3px;
  top: 50%;
  transform: translateY(0) rotate(30deg);
}

.disabled-history-items .history-item {
  pointer-events: none;
  opacity: 0.5;
  cursor: not-allowed;
}

.clear-storage-button {
  margin-top: auto;
  padding: 0.75rem;
  border: none;
  color: #d1d5db;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  border-radius: 4px;
  transition: background-color 0.2s;
  background-color: #222222;
}

.clear-storage-button:hover {
  background-color: #1c1c1c;
  color: #f9fafb;
}

.clear-storage-button .base-icon {
  color: #ff6b6b;
}

.text-hint {
  color: #9ca3af;
  margin-top: 0.5rem;
  font-size: 12px;
}


</style>
