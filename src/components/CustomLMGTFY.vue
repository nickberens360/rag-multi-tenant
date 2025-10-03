<template>
  <div
    class="lmgtfy-container"
    :class="{
      'typing-complete': typingComplete,
      'button-visible': showButtonVisible,
      'pointer-animating': pointerAnimating,
      'letters-bouncing': lettersBouncing,
      'animate-button-click': buttonClickAnimating,
    }"
  >
    <div class="google-container">
      <div class="google-heading">
        <span
          v-for="letter in letters"
          :key="letter.class"
          class="letter"
          :class="letter.class"
          :style="{ animationDelay: letter.animationDelay }"
        >
          {{ letter.char }}
        </span>
      </div>

      <div class="search-container">
        <input
          ref="searchInput"
          type="text"
          class="search-input"
          :value="displayText"
          readonly
          placeholder="Search"
        />
      </div>

      <p
        class="mt-0 font-bold text-center"
        style="color: red;"
      >
        Let me Google that for you.
      </p>

      <!-- Show button for new animations -->
      <div class="button-container">
        <button
          @click="handleSearch"
          class="search-button"
          :disabled="!playAnimation || !canSearch"
        >
          <span class="pointer-icon-container">
            <font-awesome-icon
              icon="arrow-pointer"
              class="pointer-icon"
            />
            <font-awesome-icon
              icon="arrow-pointer"
              class="pointer-icon-shadow"
            />
          </span>
          Google Search
        </button>
      </div>
      <div class="result-container text-on-light">
        <SkeletonLoader
          class="skeleton-loader"
          :class="{ 'skeleton-fade-out': !showSkeletonLoader }"
          v-show="showSkeletonLoader"
        />
        <div
          class="result-content"
          :class="{ 'result-fade-in': !showSkeletonLoader }"
          v-if="!playAnimation"
        >
          <p class="font-bold">Super Deep Research Results: </p>
          <div class="result">
            <a
              :href="googleSearchUrl"
              target="_blank"
              rel="noopener noreferrer"
              class="result-link"
            >
              <div class="result-link-top">
                <font-awesome-icon class="result-icon" icon="globe" />
                <span class="result-preview-url">www.google.com > {{displayText}}</span>
              </div>
              <div class="result-text">
                {{ displayText }}
              </div>
            </a>
            <p class="mt-2 mb-0">This is just meant to be a joke but the link works if you really want to learn more about <span class="font-bold">{{displayText}}</span>.</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, onMounted, nextTick, computed, onUnmounted } from 'vue';
import { updateMessageProperty } from '../stores/ai.js';

export default {
  name: 'CustomLMGTFY',
  props: {
    searchQuery: { type: String, required: true },
    playAnimation: { type: Boolean, default: false },
    chatId: { type: String, required: true },
    messageIndex: { type: Number, required: true }
  },
  emits: ['height-changed'],

  setup(props, { emit }) {
    const sleep = (ms) => new Promise(resolve => {
      const timeoutId = setTimeout(() => {
        resolve();
        // Remove from tracking array when executed
        activeTimeouts.value = activeTimeouts.value.filter(id => id !== timeoutId);
      }, ms);

      activeTimeouts.value.push(timeoutId);
    });

    // Track active timeouts for cleanup
    const activeTimeouts = ref([]);

    // Helper function to create tracked timeouts
    const createTimeout = (callback, delay) => {
      const timeoutId = setTimeout(() => {
        callback();
        // Remove from tracking array when executed
        activeTimeouts.value = activeTimeouts.value.filter(id => id !== timeoutId);
      }, delay);

      activeTimeouts.value.push(timeoutId);
      return timeoutId;
    };

    // === Centralized Animation Configuration ===
    const animationConfig = {
      typingSpeedMs: ref(150),
      logoBounceBaseMs: ref(300),
      logoBounceStaggerMs: ref(150),
      showButtonDelayMs: ref(300),
      buttonClickDurationMs: ref(300),
      pointerSpeedMs: ref(1000),
      buttonFadeMs: ref(300),
      bounceAnimationMs: ref(600),
      buttonScaleMs: ref(300),
      // Add skeleton loader timing
      skeletonLoaderDurationMs: ref(2000),
      // Add other timing constants
      pointerInitialDelayMs: ref(500),
      finalSearchDelayMs: ref(500),
    };

    // CSS bindings - computed properties for dynamic CSS
    const pointerSpeedCss = computed(() => `${animationConfig.pointerSpeedMs.value}ms`);
    const buttonFadeCss = computed(() => `${animationConfig.buttonFadeMs.value}ms`);
    const bounceAnimationCss = computed(() => `${animationConfig.bounceAnimationMs.value}ms`);
    const buttonScaleCss = computed(() => `${animationConfig.buttonScaleMs.value}ms`);

    const letters = reactive([
      { char: 'G', class: 'g1' },
      { char: '🙄', class: 'o1' },
      { char: '🙄', class: 'o2' },
      { char: 'g', class: 'g2' },
      { char: 'l', class: 'l' },
      { char: 'e', class: 'e' }
    ].map((letter, index) => ({
      ...letter,
      animationDelay: `${index * animationConfig.logoBounceStaggerMs.value}ms`
    })));

    const displayText = ref('');
    const typingComplete = ref(false);
    const showButtonVisible = ref(!props.playAnimation);
    const pointerAnimating = ref(false);
    const buttonClickAnimating = ref(false);
    const showSkeletonLoader = ref(false)
    const lettersBouncing = ref(false);
    const canSearch = ref(!props.playAnimation);

    const logoBounceTotalMs = computed(() =>
      animationConfig.logoBounceBaseMs.value + animationConfig.logoBounceStaggerMs.value * letters.length
    );

    const truncatedQuery = computed(() => {
      const maxLength = 20;
      return props.searchQuery.length > maxLength
        ? props.searchQuery.substring(0, maxLength) + '...'
        : props.searchQuery;
    });

    // Computed property for Google search URL
    const googleSearchUrl = computed(() => {
      const encodedQuery = encodeURIComponent(props.searchQuery);
      return `https://google.com/search?q=${encodedQuery}`;
    });

    // === Animation functions ===
    const typeQuery = async (speed = animationConfig.typingSpeedMs.value) => {
      const text = truncatedQuery.value;

      displayText.value = '';
      for (const char of text) {
        displayText.value += char;
        await sleep(speed);
      }
      typingComplete.value = true;
    };

    const animateGoogleLogo = () => {
      lettersBouncing.value = true;
    };

    const showButton = () => {
      showButtonVisible.value = true;
    };

    const animatePointer = () => {
      pointerAnimating.value = true;
      canSearch.value = true;
    };

    const animateButtonClick = async () => {
      buttonClickAnimating.value = true;
      createTimeout(() => {
        buttonClickAnimating.value = false;
      showSkeletonLoader.value = true;
      }, animationConfig.buttonClickDurationMs.value);
    };

    const performSearch = async () => {
      await sleep(animationConfig.skeletonLoaderDurationMs.value);
      showSkeletonLoader.value = false;
    };

    const showTextInstantly = () => {
      displayText.value = truncatedQuery.value;
      typingComplete.value = true;
    };

    const enableSearchInstantly = () => {
      showButtonVisible.value = true;
      canSearch.value = true;
    };

    // === Timeline with dynamic speed refs ===
    const createNormalTimeline = () => [
      { step: () => typeQuery(animationConfig.typingSpeedMs.value), delay: 0 },
      { step: () => animateGoogleLogo(), delay: logoBounceTotalMs.value },
      { step: () => showButton(), delay: animationConfig.showButtonDelayMs.value },
      { step: () => animatePointer(), delay: animationConfig.pointerSpeedMs.value + animationConfig.pointerInitialDelayMs.value },
      { step: () => animateButtonClick(), delay: animationConfig.buttonClickDurationMs.value },
      { step: () => performSearch(), delay: animationConfig.finalSearchDelayMs.value }
    ];

    const createFastTimeline = () => [
      { step: () => showTextInstantly(), delay: 0 },
      { step: () => enableSearchInstantly(), delay: 0 }
    ];

    const runTimeline = async (timeline) => {
      for (const { step, delay } of timeline) {
        await step();
        if (delay) await sleep(delay);
      }
      if (props.chatId && props.messageIndex != null) {
        updateMessageProperty(props.chatId, props.messageIndex, 'isNewResearch', false);
      }
      await nextTick();
    };

    const handleSearch = () => {
      if (!canSearch.value) return;
      runTimeline([
        { step: () => animateButtonClick(), delay: animationConfig.buttonClickDurationMs.value + animationConfig.finalSearchDelayMs.value },
        { step: () => performSearch(), delay: 0 }
      ]);
    };

    onMounted(() => {
      displayText.value = '';
      const timeline = props.playAnimation ? createNormalTimeline() : createFastTimeline();
      runTimeline(timeline);
    });

    // Cleanup function
    onUnmounted(() => {
      activeTimeouts.value.forEach(timeoutId => clearTimeout(timeoutId));
      activeTimeouts.value = [];
    });

    return {
      letters,
      displayText,
      typingComplete,
      showButtonVisible,
      pointerAnimating,
      buttonClickAnimating,
      lettersBouncing,
      canSearch,
      googleSearchUrl,
      // CSS binding computed properties
      pointerSpeedCss,
      buttonFadeCss,
      bounceAnimationCss,
      buttonScaleCss,
      handleSearch,
      showSkeletonLoader
    };
  }
};
</script>

<style scoped>
@keyframes bounce {
  0%, 20%, 50%, 80%, 100% {
    transform: translateY(0);
  }
  40% {
    transform: translateY(-20px);
  }
  60% {
    transform: translateY(-10px);
  }
}

.lmgtfy-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  margin: 20px 0;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  position: relative;
  min-height: 600px;
}

.google-container {
  position: relative;
  padding: 20px 10px;
  z-index: 20;
  background: #fff;
  width: 100%;
}

.google-heading {
  font-size: 90px;
  font-family: 'Product Sans', Arial, sans-serif;
  font-weight: 400;
  letter-spacing: -2px;
  margin-bottom: 20px;
  text-align: center;
}

.letter {
  display: inline-block;
}

.g1 {
  color: #4285f4;
}

.o1 {
  color: #ea4335;
}

.o2 {
  color: #fbbc05;
}

.g2 {
  color: #4285f4;
}

.l {
  color: #34a853;
}

.e {
  color: #ea4335;
}

.search-container {
  width: 100%;
  max-width: 584px;
  margin-bottom: 30px;
  margin-left: auto;
  margin-right: auto;
  position: relative;
}

.search-input {
  width: 100%;
  height: 44px;
  border: 1px solid #676767;
  border-radius: 24px;
  padding: 0 16px;
  font-size: 16px;
  background: #fff;
  color: #202124;
}

.search-input:focus {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  border-color: transparent;
}

.button-container {
  position: relative;
  min-height: 54px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform v-bind(buttonScaleCss) ease;
}

.search-button {
  background-color: #4285f4;
  border-radius: 4px;
  border: none;
  color: white;
  font-family: arial, sans-serif;
  font-size: 14px;
  margin: 11px 4px;
  padding: 0 16px;
  line-height: 27px;
  height: 36px;
  min-width: 120px;
  cursor: pointer;
  opacity: 0;
  transition: opacity v-bind(buttonFadeCss) ease;
}

.search-button:hover:not(:disabled) {
  background-color: #3367d6;
}

.search-button:disabled {
  cursor: not-allowed;
  opacity: 0.6 !important;
}

.result-container {
  position: relative;
  min-height: 120px;
  max-width: 584px;
  margin: 40px auto;
  transition: min-height 300ms ease;
}

.skeleton-loader {
  position: absolute;
  z-index: 10;
  top: 0;
  left: 0;
  width: 100%;
  opacity: 1;
  transition: opacity 300ms ease-out;
}

.skeleton-fade-out {
  opacity: 0;
  pointer-events: none;
}

.result-content {
  opacity: 0;
  transition: opacity 300ms ease-in;
}

.result-fade-in {
  opacity: 1;
}

.result {
  padding: 8px 16px;
  background: #eee;
  border-left: 4px solid #4285f4;
  border-radius: 6px;
}

.result-link {
  color: black;
  text-decoration: none;
  font-size: 16px;
  border-radius: 4px;
  transition: background-color 0.2s ease;
}

.result-link:hover {
  background-color: rgba(66, 133, 244, 0.1);
  text-decoration: none;
}

.result-link-top {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #5f6368;
  margin-bottom: 8px;
}

.result-text {
  color: #4285f4;
  font-weight: bold;
  font-size: 18px;
}

.result-link:hover .result-text {
  text-decoration: underline;
}

.pointer-icon-container {
  position: absolute;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  transform: translate(-60px, -120px);
  transition: transform v-bind(pointerSpeedCss) ease;
}

.pointer-icon {
  position: absolute;
  left: 0;
  top: 0;
  z-index: 10;
  color: black;
  font-size: 24px;
}

.pointer-icon-shadow {
  left: -1px;
  top: 1px;
  z-index: 5;
  transform: scale(1.1);
  color: white;
}

@media (max-width: 768px) {
  .lmgtfy-container {
    min-height: 250px;
    padding: 20px 10px;
  }

  .google-heading {
    font-size: 60px;
  }
}

@media (max-width: 450px) {
  .google-heading {
    font-size: 40px;
  }
}

.lmgtfy-container.button-visible .search-button {
  opacity: 1;
}

.lmgtfy-container.pointer-animating .pointer-icon-container {
  transform: translate(0, 0);
}

.lmgtfy-container.letters-bouncing .letter {
  animation: bounce v-bind(bounceAnimationCss) ease-in-out;
}

.lmgtfy-container.animate-button-click .button-container {
  transform: scale(0.95);
}
</style>
