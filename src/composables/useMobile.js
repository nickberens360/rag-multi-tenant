// composables/useMobile.js
import { ref, onMounted, onUnmounted } from 'vue';

const MOBILE_BREAKPOINT = 768;

export function useMobile(breakpoint = MOBILE_BREAKPOINT) {
  const isMobile = ref(false); // Default to false for SSR compatibility
  const isMounted = ref(false); // Track if component is mounted to prevent layout shift

  const updateMobileState = () => {
    isMobile.value = window.innerWidth <= breakpoint;
  };

  // Debounced resize handler to improve performance
  let resizeTimer;
  const debouncedUpdateMobileState = () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      updateMobileState();
    }, 150);
  };

  onMounted(() => {
    // Set initial state after mount when window is available
    updateMobileState();
    isMounted.value = true;
    window.addEventListener('resize', debouncedUpdateMobileState);
  });

  onUnmounted(() => {
    clearTimeout(resizeTimer);
    window.removeEventListener('resize', debouncedUpdateMobileState);
  });

  return { isMobile, isMounted };
}
