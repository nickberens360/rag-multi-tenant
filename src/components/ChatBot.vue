<template>
  <div
    class="chatbot-container"
    :class="{ 'is-drawer-open': chatHistoryVisible }"
  >
    <MobileChatBar />
    <div
      v-if="backendStatus === 'checking'"
      class="status-notification checking"
    >
      <p>🔄 Checking backend status...</p>
    </div>
    <div
      v-else-if="backendStatus === 'offline'"
      class="status-notification offline"
    >
      <p>❌ Backend service is currently offline. Please try again later.</p>
    </div>

    <div
      v-if="rateLimitNotification && false"
      class="status-notification rate-limit"
      role="status"
      aria-live="polite"
    >
      <p>{{ rateLimitNotification }}</p>
    </div>

    <ChatMessageList
      :messages="messages"
      :is-loading="isLoading"
      :has-typing-message="hasTypingMessage"
      :theme="theme"
      :backend-status="backendStatus"
      :chat-id="chatId"
      @image-click="handleImageClick"
      @followup-click="handleFollowupClick"
      @prompt-select="handlePromptSelect"
    />

    <ChatInput
      v-model:userInput="userInput"
      v-model:selectedModel="selectedModel"
      :rate-limits="rateLimits"
      :is-loading="isLoading"
      :has-typing-message="hasTypingMessage"
      :last-stopped-prompt="lastStoppedPrompt"
      :backend-status="backendStatus"
      @send-message="sendMessage"
      @stop-action="stopCurrentAction"
      @research-message="handleResearchMessage"
      @easter-egg-found="handleEasterEggFound"
    />

    <ImageOverlay/>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { useStore } from '@nanostores/vue';
import {
  activeChatId,
  activeChatMessages,
  addMessageToActiveChat,
  createNewChat,
  updateChatTitle,
  isPendingNewChat,
  updateMessageInActiveChat,
  isChatHistoryVisible,
  isChatProcessing,
  // isMobileMenuOpen,
} from '../stores/ai.js';
import { openImageOverlay } from '../stores/ui.js';
import { backendStatus } from '../stores/backendStatus.js';
import { updateEasterEgg } from '../stores/easter-eggs.js';
import { useChatAPI } from '../composables/useChatAPI.js';
import { useTenantAPI } from '../composables/useTenantAPI.js';
import ChatMessageList from './ChatMessageList.vue';
import ChatInput from './ChatInput.vue';
import ImageOverlay from './ImageOverlay.vue';
import MobileChatBar from './MobileChatBar.vue';

export default {
  name: 'ChatBot',
  components: { MobileChatBar, ChatMessageList, ChatInput, ImageOverlay },
  props: {
    theme: { type: String, default: 'dark' }
  },
  setup() {
    const userInput = ref('');
    const isLoading = ref(false); // Used briefly before the stream starts
    const messages = useStore(activeChatMessages);
    const chatId = useStore(activeChatId);
    const pendingNewChat = useStore(isPendingNewChat);
    const chatHistoryVisible = useStore(isChatHistoryVisible);
    const lastStoppedPrompt = ref('');
    const currentPrompt = ref(''); // Track the current prompt being processed
    const selectedModel = ref('claude'); // Will be updated with server default
    const backendStatusValue = useStore(backendStatus);
    const rateLimitNotification = ref('');
    const rateLimitNotificationTimeout = ref(null);

    const { sendChatMessage, stopLoading, checkBackendStatus, checkRateLimits, rateLimits } = useChatAPI();
    const { fetchWithTenant } = useTenantAPI();

    // Fetch default model from server on component mount
    const fetchDefaultModel = async () => {
      try {
        // Use the same API URL logic as other endpoints
        const isDev = import.meta.env.DEV || window.location.hostname === 'localhost';
        const apiUrl = isDev
          ? 'http://localhost:8001'
          : import.meta.env.PUBLIC_API_URL || 'https://nickberens-astro-production.up.railway.app';

        const response = await fetchWithTenant(`${apiUrl}/default-model`);
        if (response.ok) {
          const data = await response.json();
          selectedModel.value = data.default_model || 'claude';
        }
      } catch (error) {
        console.warn('Could not fetch default model, using fallback:', error);
        // Keep the fallback default 'claude'
      }
    };

    const hasTypingMessage = computed(() => messages.value.some(msg => msg.isTyping));

    // Computed property to get available models
    const availableModels = computed(() => {
      return Object.keys(rateLimits.value).filter(model => !rateLimits.value[model]);
    });

    // Function to show rate limit notification
    const showRateLimitNotification = (message) => {
      rateLimitNotification.value = message;

      // Clear any existing timeout
      if (rateLimitNotificationTimeout.value) {
        clearTimeout(rateLimitNotificationTimeout.value);
      }

      // Auto-hide after 5 seconds
      rateLimitNotificationTimeout.value = setTimeout(() => {
        rateLimitNotification.value = '';
      }, 5000);
    };

    // Function to handle model switching due to rate limits
    const handleModelRateLimit = (currentModel, newRateLimits) => {
      // Update rate limits
      Object.assign(rateLimits.value, newRateLimits);

      // If current selected model is now rate limited, switch to available one
      if (rateLimits.value[currentModel] && availableModels.value.length > 0) {
        const oldModel = currentModel;
        selectedModel.value = availableModels.value[0];

        // Model switched due to rate limit
        showRateLimitNotification(`⚠️ Switched to ${selectedModel.value} - ${oldModel} rate limit reached`);

        return true; // Model was switched
      }

      return false; // No model switch needed
    };

    let statusInterval = null;
    onMounted(async () => {
      if (!activeChatId.get() && !isPendingNewChat.get()) createNewChat();
      await checkBackendStatus();

      // Fetch default model from server settings
      await fetchDefaultModel();

      // Initial rate limit check
      await checkRateLimits();

      // Set up the status check interval
      statusInterval = setInterval(async () => {
        try {
          await checkBackendStatus();
          await checkRateLimits(); // Also check rate limits periodically
        } catch (error) {
          console.error('Status check failed:', error);
        }
      }, 15000);
    });

    onUnmounted(() => {
      if (statusInterval) clearInterval(statusInterval);
      if (rateLimitNotificationTimeout.value) {
        clearTimeout(rateLimitNotificationTimeout.value);
      }
    });

    watch(userInput, (newValue) => {
      if (newValue.trim()) lastStoppedPrompt.value = '';
    });

    const sendMessage = async () => {
      if (userInput.value.trim() === '' && lastStoppedPrompt.value) {
        userInput.value = lastStoppedPrompt.value;
        lastStoppedPrompt.value = '';
      }
      if (!userInput.value.trim() || hasTypingMessage.value || backendStatusValue.value !== 'online') return;

      const question = userInput.value;

      // Check for easter egg keywords BEFORE submission
      const lowerQuestion = question.toLowerCase();
      if (lowerQuestion.includes('egg') || lowerQuestion.includes('easter')) {
        // Handle easter egg: add user message and easter egg response, but skip backend
        const currentChatId = activeChatId.get() || createNewChat();
        if (activeChatMessages.get().length === 0) updateChatTitle(currentChatId, userInput.value);

        addMessageToActiveChat({ text: question, sender: 'user' });
        userInput.value = '';
        handleEasterEggFound('egg2');
        return; // Exit early - don't submit to backend
      }

      const currentChatId = activeChatId.get() || createNewChat();
      const chatHistoryForAPI = activeChatMessages.get().slice(-10); // Send last 10 messages
      if (activeChatMessages.get().length === 0) updateChatTitle(currentChatId, userInput.value);

      currentPrompt.value = question; // Store the current prompt

      addMessageToActiveChat({ text: question, sender: 'user' });
      userInput.value = '';

      isLoading.value = true;
      isChatProcessing.set(true);

      addMessageToActiveChat({ text: '', sender: 'bot', isTyping: true });
      const botMessageIndex = activeChatMessages.get().length - 1;

      const onChunk = (chunk) => {
        isLoading.value = false; // Stop loading indicator once first chunk arrives
        const currentMessages = activeChatMessages.get();

        // Defensive check: Ensure the index is within bounds
        if (botMessageIndex >= currentMessages.length) {
          console.error('Bot message index out of bounds during chunk update');
          return;
        }

        const msg = currentMessages[botMessageIndex];

        // Defensive check: Ensure we are updating the correct message
        if (msg && msg.sender === 'bot') {
          msg.text += chunk;
          updateMessageInActiveChat(botMessageIndex, msg);
        }
      };

      const onComplete = ({ model, followups, images, rateLimits: newRateLimits, isInitial, isFinal }) => {
        const currentMessages = activeChatMessages.get();
        const msg = currentMessages[botMessageIndex];
        if (!msg) return;

        if (isInitial) {
          msg.model = model;
          msg.followup_questions = followups;
          msg.images = images;

          // Handle rate limit updates
          if (newRateLimits) {
            const modelSwitched = handleModelRateLimit(selectedModel.value, newRateLimits);

            // If user requested one model but got another due to rate limits, notify user
            if (model && model !== selectedModel.value && model !== 'cached' && !modelSwitched) {
              showRateLimitNotification(`ℹ️ Response generated using ${model} instead of ${selectedModel.value}`);
            }
          }
        }
        if (isFinal) {
          msg.isTyping = false;
          isChatProcessing.set(false);
          currentPrompt.value = ''; // Clear tracked prompt on successful completion
        }
        updateMessageInActiveChat(botMessageIndex, msg);
      };

      const onError = (errorMessage) => {
        const currentMessages = activeChatMessages.get();
        const msg = currentMessages[botMessageIndex];
        if (msg) {
          msg.text = errorMessage;
          msg.isTyping = false;
          msg.model = 'error';
          updateMessageInActiveChat(botMessageIndex, msg);
        }
        isLoading.value = false;
        isChatProcessing.set(false);
        currentPrompt.value = ''; // Clear tracked prompt on error
      };

      const onStop = (stopMessage) => {
        const currentMessages = activeChatMessages.get();
        const msg = currentMessages[botMessageIndex];
        if (msg) {
          msg.text = stopMessage;
          msg.isTyping = false;
          msg.wasStopped = true;
          // Don't set model to 'error' for stopped messages
          updateMessageInActiveChat(botMessageIndex, msg);
        }
        isLoading.value = false;
        isChatProcessing.set(false);
        currentPrompt.value = ''; // Clear tracked prompt on stop
      };

      await sendChatMessage(question, chatHistoryForAPI, selectedModel.value, onChunk, onComplete, onError, onStop);
    };

    const stopCurrentAction = () => {
      stopLoading(); // Aborts the fetch request
      isChatProcessing.set(false);
      isLoading.value = false;

      // Save the current prompt and put it back in the input
      if (currentPrompt.value) {
        lastStoppedPrompt.value = currentPrompt.value;
        userInput.value = currentPrompt.value;
        currentPrompt.value = ''; // Clear the tracked prompt
      }

      const typingMessageIndex = messages.value.findIndex(msg => msg.isTyping);
      if (typingMessageIndex !== -1) {
        const msg = messages.value[typingMessageIndex];
        // ✅ Create a new object instead of mutating the existing one
        const updatedMsg = {
          ...msg,
          isTyping: false,
          wasStopped: true
        };
        updateMessageInActiveChat(typingMessageIndex, updatedMsg);
      }
    };

    const handlePromptSelect = (prompt) => {
      userInput.value = prompt;
      sendMessage();
    };

    const handleFollowupClick = (question) => {
      userInput.value = question;
      sendMessage();
    };

    const handleImageClick = (src) => {
      openImageOverlay(src);
    };

    const handleResearchMessage = () => {
      if (!userInput.value.trim()) return;
      const currentChatId = activeChatId.get() || createNewChat();
      if (activeChatMessages.get().length === 0) updateChatTitle(currentChatId, `Research: ${userInput.value}`);
      const question = userInput.value;
      addMessageToActiveChat({ text: question, sender: 'user' });
      userInput.value = '';
      addMessageToActiveChat({
        text: `Let me research "${question}" for you...`,
        sender: 'bot',
        model: 'research',
        lmgtfyQuery: question,
        isNewResearch: true
      });
    };

    const handleEasterEggFound = (eggName) => {
      // Update the easter egg store
      updateEasterEgg(eggName);

      // Add a special message to the chat
      addMessageToActiveChat({
        text: '',
        sender: 'bot',
        model: 'easter-egg',
        easterEggName: eggName,
        isEasterEgg: true
      });
    };

    return {
      userInput,
      messages,
      isLoading,
      hasTypingMessage,
      selectedModel,
      rateLimits,
      rateLimitNotification,
      lastStoppedPrompt,
      backendStatus: backendStatusValue,
      chatId,
      sendMessage,
      stopCurrentAction,
      handlePromptSelect,
      handleFollowupClick,
      handleImageClick,
      handleResearchMessage,
      handleEasterEggFound,
      chatHistoryVisible,
    };
  },
};
</script>

<style scoped>
/* Scoped styles are unchanged */
.chatbot-container {
  display: flex;
  flex-direction: column;
  flex-grow: 1;
  background-color: #1a1a1a;
  overflow: hidden;
}

.status-notification {
  padding: 10px;
  text-align: center;
  font-weight: bold;
}

.status-notification.checking {
  background-color: #334155;
  color: #f1f5f9;
}

.status-notification.offline {
  background-color: #7f1d1d;
  color: #fecaca;
}

.status-notification.rate-limit {
  background-color: #92400e;
  color: #fed7aa;
}
</style>
