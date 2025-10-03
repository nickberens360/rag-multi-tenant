import { atom, map, computed } from 'nanostores';

// Helper to check if we're in a browser environment
const isBrowser = () => typeof window !== 'undefined' && typeof localStorage !== 'undefined';

// Helper to get tenant-scoped localStorage key
const getTenantStorageKey = (baseKey) => {
  if (!isBrowser()) return baseKey;

  // Extract tenant slug from URL path (e.g., /default, /test-org)
  const path = window.location.pathname;
  const match = path.match(/^\/([^/]+)/);
  const tenantSlug = match ? match[1] : 'default';

  return `${tenantSlug}_${baseKey}`;
};

// --- Load chat data from localStorage or use default ---
const loadChats = () => {
  if (isBrowser()) {
    try {
      const storageKey = getTenantStorageKey('allChats');
      const savedChats = localStorage.getItem(storageKey);
      if (savedChats) {
        return JSON.parse(savedChats);
      }
    } catch (error) {
      console.error('Error loading chat history, clearing corrupted data:', error);
      // Clear corrupted data for current tenant
      localStorage.removeItem(getTenantStorageKey('allChats'));
      localStorage.removeItem(getTenantStorageKey('activeChatId'));
    }
  }
  return {}; // Default empty chats object
};

// --- Load active chat ID from localStorage or use default ---
const loadActiveChatId = () => {
  if (isBrowser()) {
    try {
      const activeChatKey = getTenantStorageKey('activeChatId');
      const savedId = localStorage.getItem(activeChatKey);
      if (savedId) {
        // Verify that the chat actually exists
        const allChatsKey = getTenantStorageKey('allChats');
        const allChatsData = localStorage.getItem(allChatsKey);
        if (allChatsData) {
          const chats = JSON.parse(allChatsData);
          if (chats[savedId]) {
            return savedId;
          }
        }
        // If chat doesn't exist, clear the invalid activeChatId
        localStorage.removeItem(activeChatKey);
      }
    } catch (error) {
      console.error('Error loading active chat ID:', error);
      localStorage.removeItem(getTenantStorageKey('activeChatId'));
    }
  }
  return null; // Default to no active chat
};

// --- Load chat history visibility state from localStorage or use default ---
const loadChatHistoryVisibility = () => {
  if (isBrowser()) {
    try {
      const visibilityKey = getTenantStorageKey('isChatHistoryVisible');
      const savedVisibility = localStorage.getItem(visibilityKey);
      if (savedVisibility !== null) {
        return JSON.parse(savedVisibility);
      }
    } catch (error) {
      console.error('Error loading chat history visibility:', error);
    }
  }
  return true; // Default to visible
};

// Initialize stores with persisted data
export const allChats = map(loadChats());
export const activeChatId = atom(loadActiveChatId());
export const isChatHistoryVisible = atom(loadChatHistoryVisibility());
export const isPendingNewChat = atom(false);
export const isChatProcessing = atom(false);
export const isMobileMenuOpen = atom(false); // New store for mobile menu state

// Subscribe to changes and save to localStorage with tenant scoping
allChats.listen((value) => {
  if (isBrowser()) {
    try {
      const storageKey = getTenantStorageKey('allChats');
      localStorage.setItem(storageKey, JSON.stringify(value));
    } catch (error) {
      console.error('Error saving chat history:', error);
    }
  }
});

activeChatId.listen((value) => {
  if (isBrowser()) {
    try {
      const storageKey = getTenantStorageKey('activeChatId');
      localStorage.setItem(storageKey, value);
    } catch (error) {
      console.error('Error saving active chat ID:', error);
    }
  }
});

isChatHistoryVisible.listen((value) => {
  if (isBrowser()) {
    try {
      const storageKey = getTenantStorageKey('isChatHistoryVisible');
      localStorage.setItem(storageKey, JSON.stringify(value));
    } catch (error) {
      console.error('Error saving chat history visibility:', error);
    }
  }
});

export const activeChat = computed([allChats, activeChatId], (chats, id) => {
  return id ? chats[id] : null;
});

export const activeChatMessages = computed(activeChat, (chat) => {
  return chat ? chat.messages : [];
});

export function createNewChat() {
  const newId = Date.now().toString();
  const newChat = {
    id: newId,
    // Start with a generic title. This will be updated later.
    title: "New Chat",
    messages: [],
  };

  allChats.setKey(newId, newChat);
  activeChatId.set(newId);
  return newId;
}

export function selectChat(chatId) {
  activeChatId.set(chatId);
}

export function addMessageToActiveChat(message) {
  const currentChat = activeChat.get();
  if (currentChat) {
    const updatedMessages = [...currentChat.messages, message];
    allChats.setKey(currentChat.id, { ...currentChat, messages: updatedMessages });
  } else {
    console.error('No active chat found when trying to add message. Creating new chat.');
    // Fallback: create a new chat if none exists
    const newChatId = createNewChat();
    const newChat = activeChat.get();
    if (newChat) {
      const updatedMessages = [...newChat.messages, message];
      allChats.setKey(newChatId, { ...newChat, messages: updatedMessages });
    }
  }
}

// --- Function to update a chat's title ---
export function updateChatTitle(chatId, newTitle) {
  const chat = allChats.get()[chatId];
  if (chat) {
    allChats.setKey(chatId, { ...chat, title: newTitle });
  }
}

/**
 * Updates a specific property of a message within a chat.
 * This is used to mark a research message as "no longer new" after its animation has played.
 * @param {string} chatId - The ID of the chat containing the message.
 * @param {number} messageIndex - The index of the message to update.
 * @param {string} property - The name of the property to update on the message object.
 * @param {*} value - The new value for the property.
 */
export function updateMessageProperty(chatId, messageIndex, property, value) {
  const chat = allChats.get()[chatId];
  if (chat && chat.messages && chat.messages[messageIndex]) {
    const updatedMessages = [...chat.messages];
    // Create a new message object with the updated property
    updatedMessages[messageIndex] = {
      ...updatedMessages[messageIndex],
      [property]: value
    };
    // Update the chat in the store
    allChats.setKey(chatId, { ...chat, messages: updatedMessages });
  } else {
    console.warn(`Could not update message property. Chat or message not found. ChatID: ${chatId}, Index: ${messageIndex}`);
  }
}

/**
 * Updates a message in the currently active chat.
 * @param {number} messageIndex - The index of the message to update.
 * @param {Object} updatedMessage - The updated message object.
 */
export function updateMessageInActiveChat(messageIndex, updatedMessage) {
  const currentChatId = activeChatId.get();
  if (!currentChatId) {
    console.warn("Could not update message, no active chat ID.");
    return;
  }

  const currentChat = allChats.get()[currentChatId];

  if (currentChat && currentChat.messages && currentChat.messages[messageIndex]) {
    // Create a new array for messages to ensure reactivity
    const updatedMessages = [...currentChat.messages];
    updatedMessages[messageIndex] = updatedMessage;

    // Update the entire chat object in the map
    allChats.setKey(currentChat.id, { ...currentChat, messages: updatedMessages });
  } else {
    console.warn(`Could not update message in active chat. Chat or message not found. Index: ${messageIndex}`);
  }
}
