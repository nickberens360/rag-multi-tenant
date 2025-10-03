<template>
  <div v-if="aiPrompt" class="content-prompt" :class="themeClass">
    <div class="content-prompt__header">
      <img
        :src="aiIconSvg"
        alt="AI Icon"
        style="width: 34px;"
      />
      <div>
        <p class="content-prompt__label">AI Prompt</p>
        <p class="content-prompt__label content-prompt__sub-label">Most likely
          hallucinated</p>
      </div>
    </div>
    <div class="content-prompt__content">
      {{ aiPrompt }}
    </div>
  </div>
</template>

<script>
import aiIconSvg from '../../assets/svg/ai-icon.svg?url';
export default {
  name: 'ContentPrompt',
  props: {
    aiPrompt: {
      type: String,
      default: ''
    },
    theme: {
      type: String,
      default: 'light'
    }
  },
  computed: {
    themeClass() {
      return this.theme === 'light' ? 'theme-light' : 'theme-dark';
    }
  },
  data() {
    return {
      aiIconSvg
    };
  },
}
</script>

<style scoped>
.content-prompt {
  position: relative;
  overflow: hidden;
  max-width: 800px;
  border-radius: 12px;
  padding: 1.5rem;
  /*box-shadow: 0 5px 10px rgba(0, 0, 0, 0.1);*/
  margin: 2rem auto;
}

.content-prompt::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
}

.content-prompt__header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
  position: relative;
  z-index: 1;
}

.content-prompt__icon {
  width: 20px;
  height: 20px;
  opacity: 0.9;
}

.content-prompt__label {
  font-size: 0.875rem;
  font-weight: 600;
  font-style: normal;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  opacity: 0.9;
  margin: 0;
}
.content-prompt__sub-label {
  font-size: 0.75rem;
  margin: 0;
  text-transform: none;
}
.content-prompt__content {
  font-size: 1rem;
  line-height: 1.6;
  position: relative;
  z-index: 1;
  font-style: italic;
}

/* Theme-based styling */
.theme-light .content-prompt__label {
  color: #333333;
}

.theme-light .content-prompt__content {
  color: #555555;
}

.theme-dark .content-prompt__label {
  color: #e0e0e0;
}

.theme-dark .content-prompt__content {
  color: #cccccc;
}

@media (max-width: 768px) {
  .content-prompt {
    padding: 1.25rem;
    margin: 1.5rem 0;
  }

  .content-prompt__content {
    font-size: 0.95rem;
  }
}
</style>
