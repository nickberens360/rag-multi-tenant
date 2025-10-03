<template>
  <div
    class="messages-window"
    ref="messagesWindow"
  >
    <div class="messages-content">
      <ChatBotWelcome
        v-if="messages.length === 0"
        :theme="theme"
        @select-prompt="$emit('prompt-select', $event)"
      />

      <div
        v-for="(pair, index) in conversationPairs"
        :key="index"
        class="conversation-pair"
      >
        <!-- User message (if exists) -->
        <div v-if="pair.userMessage" class="message user">
          <div class="message-bubble">
            <p>{{ pair.userMessage.text }}</p>
          </div>
        </div>

        <!-- Bot message (if exists) -->
        <div v-if="pair.botMessage" class="message bot">
          <div class="message-bubble">
            <div class="bot-message-wrapper">

              <div
                v-if="pair.botMessage.text"
                class="markdown-content-wrapper"
              >
                <span
                  v-html="renderMarkdown(pair.botMessage.text)"
                  class="markdown-content"
                ></span>
                <span
                  v-if="pair.botMessage.isTyping"
                  class="typing-cursor"
                >|</span>
              </div>

              <div
                v-if="!pair.botMessage.text && pair.botMessage.isTyping"
                class="typing-indicator"
              >
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
              </div>

              <div
                v-if="pair.botMessage.wasStopped && !pair.botMessage.isTyping"
                class="stopped-indicator"
              >
                <span class="stopped-icon">⏹</span>
                Response stopped
              </div>

              <div
                v-if="pair.botMessage.lmgtfyQuery && !pair.botMessage.isTyping"
                class="lmgtfy-wrapper fade-in"
              >
                <CustomLMGTFY
                  :search-query="pair.botMessage.lmgtfyQuery"
                  :play-animation="pair.botMessage.isNewResearch === true"
                  :chat-id="chatId"
                  :message-index="pair.botMessageIndex"
                />
              </div>

              <!-- Easter Egg Component -->
              <div
                v-if="pair.botMessage.isEasterEgg && !pair.botMessage.isTyping"
                class="easter-egg-wrapper fade-in"
              >
                <ChatEasterEgg
                  :egg-name="pair.botMessage.easterEggName"
                />
              </div>

              <div
                v-if="pair.botMessage.images && pair.botMessage.images.length && !pair.botMessage.isTyping"
                class="image-gallery fade-in"
              >
                <img
                  v-for="src in pair.botMessage.images"
                  :key="src"
                  :src="src"
                  alt="Illustration"
                  class="chat-image"
                  @click="$emit('image-click', src)"
                />
              </div>

              <div
                v-if="pair.botMessage.model && !pair.botMessage.isTyping && !pair.botMessage.isEasterEgg"
                class="model-indicator"
              >
                <span
                  class="model-badge"
                  :class="{
                   'error': pair.botMessage.model === 'error' || backendStatus === 'offline'
                  }"
                >
                  {{ pair.botMessage.model }}
                </span>
              </div>

              <div
                v-if="shouldShowFollowups(pair.botMessage)"
                class="followup-container fade-in"
              >
                <p class="followup-label">💡 You might also want to ask:</p>
                <div class="followup-buttons">
                  <button
                    v-for="(question, qIndex) in pair.botMessage.followup_questions"
                    :key="qIndex"
                    @click="$emit('followup-click', question)"
                    class="followup-button"
                  >
                    {{ question }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>


<script>
import { ref, nextTick, watch, onMounted, computed } from 'vue';
import { useScrollToBottom } from '../composables/useScrollToBottom.js';
import ChatBotWelcome from './ChatBotWelcome.vue';
import CustomLMGTFY from './CustomLMGTFY.vue';
import ChatEasterEgg from './ChatEasterEgg.vue';
import { marked } from 'marked';

// Debounce utility function
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

export default {
  components: { ChatBotWelcome, CustomLMGTFY, ChatEasterEgg },
  props: {
    messages: { type: Array, required: true },
    isLoading: { type: Boolean, default: false },
    hasTypingMessage: { type: Boolean, default: false },
    backendStatus: { type: String, default: null },
    theme: { type: String, default: 'dark' },
    chatId: { type: String, default: null }
  },
  emits: ['prompt-select', 'image-click', 'followup-click'],
  setup(props) {
    const messagesWindow = ref(null);
    const { scrollToBottom } = useScrollToBottom(messagesWindow);

    // Create debounced scroll function with 100ms delay
    const debouncedScrollToBottom = debounce(() => {
      nextTick(() => scrollToBottom());
    }, 100);

    // Watch for message changes
    watch(() => props.messages, () => {
      debouncedScrollToBottom();
    }, { deep: true });

    // Handle initial mount
    onMounted(() => {
      if (props.messages.length > 0) {
        debouncedScrollToBottom();
      }
    });

    const renderMarkdown = (text) => {
      return marked(text || '');
    };

    const shouldShowFollowups = (message) => {
      return message.followup_questions &&
        message.followup_questions.length &&
        message.sender === 'bot' &&
        !message.isTyping;
    };

    const conversationPairs = computed(() => {
      const pairs = [];
      let currentPair = null;

      props.messages.forEach((message, messageIndex) => {
        if (message.sender === 'user') {
          // Start a new conversation pair
          currentPair = {
            userMessage: message,
            userMessageIndex: messageIndex,
            botMessage: null,
            botMessageIndex: null
          };
          pairs.push(currentPair);
        } else if (message.sender === 'bot') {
          if (currentPair) {
            // Add bot message to current pair
            currentPair.botMessage = message;
            currentPair.botMessageIndex = messageIndex;
            currentPair = null; // Reset for next pair
          } else {
            // Handle orphaned bot message (e.g., welcome message)
            pairs.push({
              userMessage: null,
              userMessageIndex: null,
              botMessage: message,
              botMessageIndex: messageIndex
            });
          }
        }
      });

      return pairs;
    });

    return {
      messagesWindow,
      renderMarkdown,
      shouldShowFollowups,
      conversationPairs,
    };
  }
};
</script>

<style scoped>
.messages-window {
  padding: 1rem;
  overflow-y: auto;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  scroll-behavior: smooth;
}

.messages-content {
  max-width: 800px;
  width: 100%;
  margin: 0 auto;
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.conversation-pair {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.conversation-pair:last-child {
  margin-bottom: 0;
}

.message {
  display: flex;
}

.message-bubble {
  padding: 0.75rem 1.25rem;
  border-radius: 1.25rem;
  max-width: 100%;
  line-height: 1.5;
}

.user {
  justify-content: flex-end;
}

.user .message-bubble {
  background-color: #1c2539;
  color: white;
  padding: 0 1.25rem;
  border-bottom-right-radius: 4px;
}

.bot {
  justify-content: flex-start;
}

.bot .message-bubble {
  width: 100%;
  background: none;
  color: #f9fafb;
  border-bottom-left-radius: 4px;
}

@supports not (height: 100dvh) {
  .conversation-pair:last-of-type {
    height: calc(100vh - var(--chat-bot-form-height) - var(--site-header-height) - 25px);
  }
}
@supports (height: 100dvh) {
  .conversation-pair:last-of-type {
    height: calc(100dvh - var(--chat-bot-form-height) - var(--site-header-height) - 25px);
  }
}


/* Real typing cursor style */
.typing-cursor {
  display: inline-block;
  animation: blink 1s infinite;
  font-weight: bold;
  vertical-align: baseline;
  color: #60a5fa;
}

@keyframes blink {
  0%, 50% {
    opacity: 1;
  }
  51%, 100% {
    opacity: 0;
  }
}

/* Other styles like typing-indicator, followup-container etc. remain the same */
.typing-indicator {
  display: flex;
  align-items: center;
  gap: 5px
}

.typing-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #666;
  animation: typing 1.2s infinite ease-in-out
}

.typing-dot:nth-child(2) {
  animation-delay: .2s
}

.typing-dot:nth-child(3) {
  animation-delay: .4s
}

@keyframes typing {
  0%, 100% {
    transform: translateY(0);
    opacity: .5
  }
  40% {
    transform: translateY(-5px);
    opacity: 1
  }
}

.stopped-indicator {
  margin-top: .5rem;
  padding: .25rem .5rem;
  font-size: .75rem;
  color: #9ca3af;
  font-style: italic
}

/* Fade-in animation for dynamic content */
.fade-in {
  animation: fadeIn 0.6s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Easter egg wrapper */
.easter-egg-wrapper {
  margin-top: 0.75rem;
}

/* LMGTFY wrapper */
.lmgtfy-wrapper {
  margin-top: 0.75rem;
}

.image-gallery {
  display: grid;
  grid-template-columns:repeat(auto-fill, minmax(150px, 1fr));
  gap: .5rem;
  margin-top: .75rem
}

.chat-image {
  width: 100%;
  height: auto;
  border-radius: 8px;
  border: 1px solid #444;
  cursor: pointer;
  transition: transform .2s ease
}

.chat-image:hover {
  transform: scale(1.05)
}

.model-indicator {
  margin-top: .5rem
}

.model-badge {
  background-color: rgba(132, 250, 96, .1);
  border: 1px solid rgba(132, 250, 96, .3);
  color: #84fa60;
  padding: .125rem .375rem;
  border-radius: 4px;
  font-size: .6875rem;
  font-weight: 500;
  text-transform: uppercase
}

.model-badge.error {
  background-color: rgba(239, 68, 68, .1);
  border-color: rgba(239, 68, 68, .3);
  color: #ef4444
}

.followup-container {
  margin-top: 1rem;
  padding-top: .75rem;
  border-top: 1px solid #333
}

.followup-label {
  font-size: .875rem;
  color: #9ca3af;
  margin-bottom: .5rem
}

.followup-buttons {
  position: relative;
  padding-bottom: .7rem;
}

.followup-button {
  display: block;
  background-color: #222222;
  color: #f9fafb;
  width: 100%;
  border: none;
  border-radius: 8px;
  padding: 1rem;
  font-size: .875rem;
  cursor: pointer;
  transition: background-color .2s;
  text-align: left;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: .5rem;
  scroll-snap-align: start;
}

.followup-button:focus-visible {
  outline: 2px solid #60a5fa;
  outline-offset: 2px;
}

.followup-button:hover {
  background-color: #404040
}

:deep(.markdown-content) {
  display: block;
}
:deep(.markdown-content h1) {
  font-size: 2.5rem;
  margin: 0 0 1rem;
}
:deep(.markdown-content h2) {
  font-size: 1.75rem;
  margin: 0 0 1rem;
}
:deep(.markdown-content h3) {
  font-size: 1.25rem;
  margin: 0 0 1rem;
}
:deep(.markdown-content a) {
  color: #60a5fa;
}

@media (max-width: 640px) {
  .message-bubble {
    padding: 0.5rem 0;
  }
}

</style>
