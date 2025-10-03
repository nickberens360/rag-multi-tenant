<template>
  <div class="input-form">
    <div class="input-container">
      <!-- ChatMessageInput functionality -->
      <div class="input-wrapper">
        <textarea
          :value="userInput"
          @input="handleInput"
          @keydown="handleKeydown"
          :placeholder="inputPlaceholder"
          class="message-input"
          :class="{
            'warning': isNearLimit,
            'error': isOverLimit
          }"
          :disabled="hasTypingMessage || backendStatus !== 'online'"
          aria-label="Chat message input"
          :aria-describedby="hasTypingMessage ? 'typing-status' : null"
          rows="1"
          ref="textareaRef"
        ></textarea>

        <!-- Character count and warnings -->
        <div v-if="false" class="input-info">
          <div class="character-count" :class="{
            'warning': isNearLimit,
            'error': isOverLimit
          }">
            {{ characterCount }}/{{ maxLength }}
            <span v-if="isNearLimit && !isOverLimit" class="warning-text">
              (approaching limit)
            </span>
            <span v-if="isOverLimit" class="error-text">
              (over limit - will be truncated)
            </span>
          </div>
        </div>
      </div>

      <div class="d-flex justify-between items-center w-full pt-2">
        <!-- ChatModelSelector functionality with rate limit awareness -->
        <div class="model-selector-bar">
          <div class="model-selector-container">
            <select
              :value="selectedModel"
              @change="$emit('update:selectedModel', $event.target.value)"
              class="model-selector"
              :disabled="hasTypingMessage || backendStatus !== 'online'"
            >
              <option
                v-for="option in modelOptions"
                :key="option.value"
                :value="option.value"
                :disabled="option.disabled"
              >
                {{ option.label }}
              </option>
            </select>
          </div>
        </div>

        <button
          @click="handleResearchClick"
          class="research-button ml-auto"
          :disabled="!userInput.trim() || hasTypingMessage || backendStatus !== 'online'"
          title="Research this topic"
        >
          <font-awesome-icon icon="globe" />
          <span class="research-button-label ml-2">Super Deep Research</span>
        </button>

        <!-- ChatSendButton functionality -->
        <button
          @click="handleSendButtonClick"
          class="send-button"
          :class="{
            'stop-mode': isInStopMode,
            'retry-mode': isInRetryMode && !isInStopMode
          }"
          :disabled="false"
          :title="buttonTitle"
        >
          <!-- Stop state: when loading or typing (takes priority) -->
          <span v-if="isInStopMode" class="button-content">
            <font-awesome-icon icon="stop" />
          </span>
          <!-- Retry state: when we have a stopped prompt and not loading/typing -->
          <span v-else-if="isInRetryMode" class="button-content">
            <font-awesome-icon icon="rotate-right" />
          </span>
          <!-- Default send state -->
          <span v-else class="button-content">
            <font-awesome-icon icon="arrow-up" />
          </span>
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { computed, ref, nextTick, watch } from 'vue';

export default {
  name: 'ChatInput',
  props: {
    userInput: {
      type: String,
      required: true
    },
    selectedModel: {
      type: String,
      required: true
    },
    rateLimits: {
      type: Object,
      default: () => ({ claude: false, gemini: false })
    },
    isLoading: {
      type: Boolean,
      default: false
    },
    hasTypingMessage: {
      type: Boolean,
      default: false
    },
    lastStoppedPrompt: {
      type: String,
      default: ''
    },
    backendStatus: {
      type: String,
      default: 'checking'
    }
  },
  emits: [
    'update:userInput',
    'update:selectedModel',
    'send-message',
    'stop-action',
    'research-message',
    'easter-egg-found'
  ],
  setup(props, { emit }) {
    const textareaRef = ref(null);
    const maxLength = 1000; // Match backend Query model limit
    const warningThreshold = Math.floor(maxLength * 0.9); // 90% of max length

    // Character counting and warning states
    const characterCount = computed(() => props.userInput.length);
    const isNearLimit = computed(() => characterCount.value >= warningThreshold && characterCount.value < maxLength);
    const isOverLimit = computed(() => characterCount.value >= maxLength);

    // Model options with rate limit awareness
    const modelOptions = computed(() => {
      return [
        {
          value: 'claude',
          label: props.rateLimits.claude ? 'Claude (rate limit exhausted)' : 'Claude',
          disabled: props.rateLimits.claude
        },
        {
          value: 'gemini',
          label: props.rateLimits.gemini ? 'Gemini (rate limit exhausted)' : 'Gemini',
          disabled: props.rateLimits.gemini
        }
      ];
    });

    // Auto-resize textarea
    const autoResize = () => {
      if (textareaRef.value) {
        textareaRef.value.style.height = 'auto';
        textareaRef.value.style.height = Math.min(textareaRef.value.scrollHeight, 120) + 'px';
      }
    };

    // Handle input with truncation
    const handleInput = (event) => {
      let value = event.target.value;

      // If over limit, truncate and show warning
      if (value.length > maxLength) {
        value = value.substring(0, maxLength);
        // Optional: Show a brief notification about truncation
        console.warn(`Input truncated to ${maxLength} characters`);
      }

      emit('update:userInput', value);
      nextTick(() => autoResize());
    };

    // Handle keyboard events
    const handleKeydown = (event) => {
      // Enter without Shift sends message
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        if (props.userInput.trim() && !props.hasTypingMessage && props.backendStatus === 'online') {
          emit('send-message');
        }
      }
      // Shift+Enter adds new line (default behavior)
    };

    // Watch for external changes to userInput to trigger resize
    watch(() => props.userInput, () => {
      nextTick(() => autoResize());
    });

    // Input placeholder logic
    const inputPlaceholder = computed(() => {
      // First check backend status
      if (props.backendStatus !== 'online') {
        switch (props.backendStatus) {
          case 'checking':
            return '🔄 Checking backend status...';
          case 'building':
            return '⚠️ Backend building, please wait...';
          case 'initializing':
            return '🔄 Backend initializing, please wait...';
          case 'offline':
            return '❌ Backend offline, please try again later';
          default:
            return 'Backend not ready...';
        }
      }

      // If backend is online, show normal placeholders
      return props.lastStoppedPrompt && !props.userInput.trim()
        ? 'Press Enter to retry stopped response...'
        : 'Ask about Nick...';
    });

    // Send button state logic
    const isInStopMode = computed(() => {
      return props.isLoading || props.hasTypingMessage;
    });

    const isInRetryMode = computed(() => {
      // Show retry when we have a stopped prompt AND the input is empty
      // AND we're not currently typing (loading is OK - we want stop during loading)
      return Boolean(
        props.lastStoppedPrompt &&
        !props.userInput.trim() &&
        !props.hasTypingMessage
      );
    });

    const buttonTitle = computed(() => {
      if (isInStopMode.value) {
        return props.isLoading ? 'Stop loading' : 'Stop typing';
      } else if (isInRetryMode.value) {
        return 'Retry stopped message';
      } else {
        return 'Send message';
      }
    });

    const handleSendButtonClick = () => {
      if (isInStopMode.value) {
        // If we're loading or typing, emit stop
        emit('stop-action');
      } else {
        // For both retry and normal send, emit 'send-message'
        emit('send-message');
      }
    };

    const handleResearchClick = () => {
      emit('research-message');
    };

    return {
      textareaRef,
      maxLength,
      characterCount,
      isNearLimit,
      isOverLimit,
      modelOptions,
      handleInput,
      handleKeydown,
      inputPlaceholder,
      isInStopMode,
      isInRetryMode,
      buttonTitle,
      handleSendButtonClick,
      handleResearchClick
    };
  }
};
</script>

<style scoped>
/* Input form styles */
.input-form {
  display: flex;
  padding: 0 1rem 1rem;
}

.input-container {
  box-shadow: 0 -8px 20px 10px rgba(26, 26, 26, .9);
  width: 100%;
  border: 1px solid #afafaf;
  color: #f9fafb;
  border-radius: 8px;
  padding: 0.5rem;
  max-width: 800px;
  margin: 0 auto;
}

/* Input wrapper styles */
.input-wrapper {
  width: 100%;
}

/* Message input styles */
.message-input {
  flex-grow: 0;
  padding: 0.75rem;
  font-size: 1rem;
  border: none !important;
  background: none !important;
  color: #f9fafb;
  width: 100%;
  resize: none;
  min-height: 24px;
  max-height: 120px;
  overflow-y: auto;
  line-height: 1.5;
  transition: border-color 0.2s ease;
}

.message-input.warning {
  border-left: 3px solid #f59e0b !important;
}

.message-input.error {
  border-left: 3px solid #ef4444 !important;
}

.message-input::placeholder {
  color: #999999;
}

.message-input:focus {
  outline: none;
  border-color: #555555;
  box-shadow: none !important;
}

/* Model selector styles */
.model-selector-bar {
  padding-left: .5rem;
}

.model-selector-container {
  display: flex;
  align-items: center;
  gap: 1rem;
  max-width: 800px;
  margin: 0 auto;
}

.model-selector {
  background-color: #222222;
  border: 1px solid #444444;
  border-radius: 6px;
  color: #b8ccfb;
  padding: 0.375rem 0.75rem;
  font-size: 0.875rem;
  cursor: pointer;
  width: 100px;
}

.model-selector:focus {
  outline: none;
}

.model-selector:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Style for disabled options in the select dropdown */
.model-selector option:disabled {
  color: #666666;
  font-style: italic;
}

.research-button {
  background-color: rgba(87, 115, 174, 0.41);
  outline: none;
  border: 1px solid #718096;
  color: #bfd4ff;
  border-radius: 6px;
  padding: 0.375rem 0.75rem;
  font-size: 0.875rem;
  cursor: pointer;
  margin-left: 0.5rem;
  transition: all 0.2s ease;
}

.research-button:hover:not(:disabled) {
  background-color: #4a5568;
  border-color: #718096;
}

.research-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Send button styles */
.send-button {
  margin-left: 1rem;
  margin-right: 0.5rem;
  border: none;
  background-color: rgba(87, 115, 174, 0.41);
  color: #9cbcf9;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s ease;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.send-button:hover:not(:disabled) {
  background-color: rgba(49, 89, 175, 0.41);
}

.send-button.stop-mode {
  background-color: rgba(248, 128, 128, 0.41);
  color: #fec5c5;
}

.send-button.stop-mode:hover:not(:disabled) {
  background-color: rgba(252, 69, 69, 0.41);
}

.send-button.retry-mode {
  background-color: rgba(245, 204, 140, 0.27);
  color: #f59e0b;
}

.send-button.retry-mode:hover:not(:disabled) {
  background-color: rgba(217, 119, 6, 0.42);
}

.send-button:disabled {
  background-color: #6b7280;
  cursor: not-allowed;
  opacity: 0.5;
}

.button-content {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
}

/* Add a subtle animation for the stop state */
.send-button.stop-mode .button-content {
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

/* Input info and character count styles */
.input-info {
  display: flex;
  justify-content: flex-end;
  padding: 0.25rem 0.75rem 0;
}

.character-count {
  font-size: 0.75rem;
  color: #9ca3af;
  transition: color 0.2s ease;
}

.character-count.warning {
  color: #f59e0b;
}

.character-count.error {
  color: #ef4444;
}

.warning-text,
.error-text {
  font-weight: 500;
  margin-left: 0.25rem;
}

.warning-text {
  color: #f59e0b;
}

.error-text {
  color: #ef4444;
}

@media (max-width: 767px) {
  .input-form {
    padding: 0 0.5rem 0.5rem;
  }
  .model-selector {
    padding: 0.375rem 0.5rem;
  }
  .character-count {
    font-size: 0.7rem;
  }
  .research-button-label {
    display: none;
  }
}
</style>
