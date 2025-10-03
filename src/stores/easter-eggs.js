import { atom, computed, onMount } from 'nanostores';

// Local storage key
const EASTER_EGGS_STORAGE_KEY = 'nickgoldsworthy_easter_eggs';

// Default state
const defaultState = {
  easterEggs: [
    {
      name: 'egg1',
      hint: 'Clean yo screen, you nasty!',
      isComplete: false
    },
    {
      name: 'egg2',
      hint: 'We need to chat about eggs.',
      isComplete: false
    },
    {
      name: 'egg3',
      hint: 'Terminal velocity of an egg?',
      isComplete: false
    },
  ],
  totalEggsToComplete: 3,
  activeEggsCompleteCount: 0,
  // AnnoyingEyelash component state
  annoyingEyelash: {
    isVisible: true,
    currentX: undefined,  // Let component props determine initial position
    currentY: undefined,  // Let component props determine initial position
    dragAttempts: 0,
    isAnimating: false,
    isComponentVisible: true
  }
};

// Load state from localStorage
const loadStateFromStorage = () => {
  // Check if we're in a browser environment
  if (typeof window === 'undefined' || typeof localStorage === 'undefined') {
    return defaultState;
  }

  try {
    const savedState = localStorage.getItem(EASTER_EGGS_STORAGE_KEY);
    if (savedState) {
      const parsedState = JSON.parse(savedState);
      // Validate the loaded state has the expected structure
      if (parsedState.easterEggs && Array.isArray(parsedState.easterEggs)) {
        // Merge with defaultState to ensure all properties exist
        return {
          ...defaultState,
          ...parsedState,
          annoyingEyelash: {
            ...defaultState.annoyingEyelash,
            ...(parsedState.annoyingEyelash || {})
          }
        };
      }
    }
  } catch (error) {
    console.error('Error loading easter eggs from localStorage:', error);
  }
  return defaultState;
};

// Save state to localStorage
const saveStateToStorage = (state) => {
  // Check if we're in a browser environment
  if (typeof window === 'undefined' || typeof localStorage === 'undefined') {
    return;
  }

  try {
    localStorage.setItem(EASTER_EGGS_STORAGE_KEY, JSON.stringify(state));
  } catch (error) {
    console.error('Error saving easter eggs to localStorage:', error);
  }
};

// Initialize store with default state (will be updated from localStorage after mount)
export const easterEggsStore = atom(defaultState);

// Set up localStorage persistence on mount
onMount(easterEggsStore, () => {
  // Load saved state from localStorage on client-side mount
  const savedState = loadStateFromStorage();
  // Only update if we actually loaded something from localStorage
  if (typeof window !== 'undefined' && localStorage.getItem(EASTER_EGGS_STORAGE_KEY)) {
    easterEggsStore.set(savedState);
  }

  // Save to localStorage whenever the store changes
  const unsubscribe = easterEggsStore.subscribe(state => {
    saveStateToStorage(state);
  });

  // Return cleanup function
  return () => {
    unsubscribe();
  };
});

// Computed store for allEggsFound
export const allEggsFound = computed(easterEggsStore, (state) => {
  return state.activeEggsCompleteCount >= state.totalEggsToComplete;
});

// Function to update Easter egg completion status
export const updateEasterEgg = (eggName) => {
  const currentState = easterEggsStore.get();

  const eggIndex = currentState.easterEggs.findIndex(egg => egg.name === eggName);

  if (eggIndex !== -1 && !currentState.easterEggs[eggIndex].isComplete) {
    const updatedEggs = [...currentState.easterEggs];
    updatedEggs[eggIndex] = {
      ...updatedEggs[eggIndex],
      isComplete: true
    };

    // Don't set allEggsFound here - let the computed store handle it
    easterEggsStore.set({
      ...currentState,
      easterEggs: updatedEggs,
      activeEggsCompleteCount: currentState.activeEggsCompleteCount + 1
    });
  }
};

// Function to reset all Easter eggs (useful for testing)
export const resetEasterEggs = () => {
  easterEggsStore.set(defaultState);
  // Also reset the celebration shown state
  if (typeof window !== 'undefined' && typeof localStorage !== 'undefined') {
    localStorage.removeItem('nickgoldsworthy_celebration_shown');
  }
};

// Function to update AnnoyingEyelash state
export const updateAnnoyingEyelash = (updates) => {
  const currentState = easterEggsStore.get();
  easterEggsStore.set({
    ...currentState,
    annoyingEyelash: {
      ...currentState.annoyingEyelash,
      ...updates
    }
  });
};

// Computed store for annoying eyelash visibility
export const annoyingEyelashVisible = computed(easterEggsStore, (state) => {
  return state.annoyingEyelash?.isComponentVisible ?? true;
});
