// composables/useScrollToBottom.js
import { nextTick } from 'vue';

export function useScrollToBottom(messagesWindowRef) {
  const scrollToBottom = () => {
    nextTick(() => {
      if (messagesWindowRef.value) {
        messagesWindowRef.value.scrollTop = messagesWindowRef.value.scrollHeight;
      }
    });
  };

  return {
    scrollToBottom
  };
}
