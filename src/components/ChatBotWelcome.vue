<template>
  <div
    class="welcome-container"
    :class="`theme-${theme}`"
  >
    <div class="welcome-content">
      <h2>Welcome to nick.AI</h2>
      <p>Try asking me some questions like:</p>
      <ul
        v-if="welcomeQuestions.length"
        class="example-prompts"
      >
        <li v-if="loading" class="loading-placeholder">
          <span class="prompt-icon">...</span>
          Loading questions...
        </li>
        <li
          v-else
          v-for="question in welcomeQuestions"
          :key="question.id"
          @click="selectPrompt(question.question_text)"
        >
          <span class="prompt-icon">→</span>
          {{ question.question_text }}
        </li>
      </ul>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useTenantAPI } from '../composables/useTenantAPI'

export default {
  name: 'ChatBotWelcome',
  props: {
    theme: {
      type: String,
      default: 'dark',
      validator: (value) => ['light', 'dark'].includes(value)
    }
  },
  emits: ['select-prompt'],
  setup(props, { emit }) {
    const loading = ref(true)
    const welcomeQuestions = ref([])
    const { fetchWithTenant } = useTenantAPI()

    const selectPrompt = (prompt) => {
      emit('select-prompt', prompt);
    };

    const fetchWelcomeQuestions = async () => {
      try {
        // Use the same API URL logic as other components
        const isDev = import.meta.env.DEV || window.location.hostname === 'localhost';
        const apiUrl = isDev
          ? 'http://localhost:8001'
          : import.meta.env.PUBLIC_API_URL || 'https://nickberens-astro-production.up.railway.app';

        const response = await fetchWithTenant(`${apiUrl}/welcome-questions`)
        const data = await response.json()

        // Sort questions by sort_order and assign to reactive ref
        welcomeQuestions.value = (data.questions || []).sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))
      } catch (error) {
        console.error('Failed to fetch welcome questions:', error)
        // Fallback to default questions
        welcomeQuestions.value = [
          { id: 1, question_text: "Tell me about yourself", sort_order: 1 },
          { id: 2, question_text: "Show me your resume", sort_order: 2 },
          { id: 3, question_text: "Show me your illustrations", sort_order: 3 }
        ]
      } finally {
        loading.value = false
      }
    }

    onMounted(() => {
      fetchWelcomeQuestions()
    })

    return {
      loading,
      welcomeQuestions,
      selectPrompt
    };
  }
};
</script>

<style scoped>
.welcome-container {
  /*background: radial-gradient(circle, rgba(230, 115, 115, 0.05), rgba(115, 230, 115, 0.05), rgba(115, 115, 230, 0.05));*/
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 2rem;
  text-align: center;
  color: #f9fafb;
}

.welcome-content {
  max-width: 500px;
  margin: 0 auto;
}

.welcome-content__ascii {
  background: linear-gradient(to right, #ff0000, #00ff00, #0000ff);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  font-weight: bold;
}

h2 {
  margin-bottom: 1rem;
  font-size: 1.5rem;
  font-weight: 600;
}

p {
  margin-bottom: 1.5rem;
  font-size: 1rem;
  color: #d1d5db;
}

.example-prompts {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.example-prompts li {
  padding: 0.75rem 1.25rem;
  background-color: #222222;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
  display: flex;
  align-items: center;
  color: #f9fafb;
}

.example-prompts li:hover {
  background-color: #333333;
  transform: translateY(-2px);
}

.loading-placeholder {
  opacity: 0.6;
  cursor: default !important;
}

.loading-placeholder:hover {
  background-color: #222222 !important;
  transform: none !important;
}

.prompt-icon {
  margin-right: 0.5rem;
  font-weight: bold;
}

/* Light theme styles would go here in the future with .theme-light prefix */

@media (max-width: 768px) {
  .welcome-content__ascii {
    font-size: 8px;
  }
}
</style>
