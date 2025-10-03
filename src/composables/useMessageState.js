// composables/useMessageState.js
import { ref, computed } from 'vue';
import { activeChatMessages, activeChatId, allChats } from '../stores/ai.js';

export function useMessageState() {
  const typingMessages = ref(new Set());
  const typingTimeouts = ref(new Map());
  const typingMessageChats = ref(new Map()); // Track which chat each typing message belongs to

  // Constants for typing animation
  const TYPING_SPEED = 10;
  const BATCH_SIZE = 5; // Number of characters to type at once

  const hasTypingMessage = computed(() => {
    return activeChatMessages.get().some(msg => msg.isTyping);
  });

  const updateMessageTyping = (messageIndex, fullText, targetChatId) => {
    return new Promise((resolve) => {
      typingMessages.value.add(messageIndex);
      typingMessageChats.value.set(messageIndex, targetChatId); // Track the chat for this message
      let currentText = '';
      let currentIndex = 0;

      const typeChar = () => {
        // Check if typing was stopped
        if (!typingMessages.value.has(messageIndex)) {
          cleanupTypingTimeouts();
          resolve();
          return;
        }

        if (currentIndex < fullText.length) {
          // Determine how many characters to add (up to BATCH_SIZE)
          const charsToAdd = Math.min(BATCH_SIZE, fullText.length - currentIndex);
          currentText += fullText.substring(currentIndex, currentIndex + charsToAdd);

          // Update the message in the SPECIFIC chat (not necessarily the active one)
          const targetChat = allChats.get()[targetChatId];
          if (targetChat && targetChat.messages[messageIndex]) {
            const updatedMessages = [...targetChat.messages];
            updatedMessages[messageIndex] = {
              ...updatedMessages[messageIndex],
              text: currentText,
              isTyping: true
            };

            allChats.setKey(targetChatId, {
              ...targetChat,
              messages: updatedMessages
            });
          }

          currentIndex += charsToAdd;
          const timeoutId = setTimeout(typeChar, TYPING_SPEED);
          typingTimeouts.value.set(messageIndex, timeoutId);
        } else {
          // Typing complete naturally (not stopped)
          typingMessages.value.delete(messageIndex);
          typingTimeouts.value.delete(messageIndex);
          typingMessageChats.value.delete(messageIndex); // Clean up chat tracking

          const targetChat = allChats.get()[targetChatId];
          if (targetChat && targetChat.messages[messageIndex]) {
            const updatedMessages = [...targetChat.messages];
            updatedMessages[messageIndex] = {
              ...updatedMessages[messageIndex],
              isTyping: false,
              wasStopped: false
            };

            allChats.setKey(targetChatId, {
              ...targetChat,
              messages: updatedMessages
            });
          }
          resolve();
        }
      };

      // Start typing immediately
      const initialTimeoutId = setTimeout(typeChar, TYPING_SPEED);
      typingTimeouts.value.set(messageIndex, initialTimeoutId);
    });
  };

  const cleanupTypingTimeouts = () => {
    // Clear all active timeouts
    for (const [messageIndex, timeoutId] of typingTimeouts.value.entries()) {
      clearTimeout(timeoutId);
      typingTimeouts.value.delete(messageIndex);
    }

    // Clear typing messages tracking
    typingMessages.value.clear();
    typingMessageChats.value.clear();
  };

  const stopTyping = (messageIndex, targetChatId) => {
    // Clear the timeout for this message
    if (typingTimeouts.value.has(messageIndex)) {
      clearTimeout(typingTimeouts.value.get(messageIndex));
      typingTimeouts.value.delete(messageIndex);
    }

    // Remove from typing messages set and clean up chat tracking
    typingMessages.value.delete(messageIndex);
    typingMessageChats.value.delete(messageIndex);

    // Update the message in the SPECIFIC chat to show it's no longer typing and was stopped
    const targetChat = allChats.get()[targetChatId];
    if (targetChat && targetChat.messages[messageIndex]) {
      const updatedMessages = [...targetChat.messages];
      updatedMessages[messageIndex] = {
        ...updatedMessages[messageIndex],
        isTyping: false,
        wasStopped: true
      };

      allChats.setKey(targetChatId, {
        ...targetChat,
        messages: updatedMessages
      });
    }
  };

  return {
    typingMessages,
    typingTimeouts,
    typingMessageChats,
    hasTypingMessage,
    updateMessageTyping,
    stopTyping,
    cleanupTypingTimeouts
  };
}
