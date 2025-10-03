<template>
  <div class="easter-egg-chat-wrapper">
    <div class="easter-egg-celebration">
      <div class="egg-icon-bounce">🥚</div>
      <h3>Easter Egg Found!</h3>
      <p>{{ eggMessage }}</p>
      <div class="confetti-container">
        <span class="confetti" v-for="n in 20" :key="n">✨</span>
      </div>
    </div>
  </div>
</template>

<script>
import { computed } from 'vue';

export default {
  name: 'ChatEasterEgg',
  props: {
    eggName: {
      type: String,
      required: true
    }
  },
  setup(props) {
    const eggMessage = computed(() => {
      const messages = {
        egg1: 'You cleaned your screen! The eyelash is gone! 🧹',
        egg2: 'We had a great chat about eggs! 🥚',
        egg3: 'Terminal velocity of an egg calculated! 🚀'
      };
      return messages[props.eggName] || 'You found a secret!';
    });

    return {
      eggMessage
    };
  }
};
</script>

<style scoped>
.easter-egg-chat-wrapper {
  padding: 1rem;
  margin: 0.5rem 0;
}

.easter-egg-celebration {
  border-radius: 12px;
  padding: 2rem;
  text-align: center;
  position: relative;
  overflow: hidden;
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

.egg-icon-bounce {
  font-size: 3rem;
  animation: bounce 1s ease-in-out infinite;
  margin-bottom: 0.5rem;
}

@keyframes bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

.easter-egg-celebration h3 {
  color: white;
  margin: 0.5rem 0;
  font-size: 1.5rem;
}

.easter-egg-celebration p {
  color: rgba(255, 255, 255, 0.9);
  margin: 0.5rem 0;
  font-size: 1.1rem;
}

.confetti-container {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.confetti {
  position: absolute;
  font-size: 1.2rem;
  animation: confetti-fall 3s ease-out infinite;
}

.confetti:nth-child(odd) {
  animation-delay: 0.1s;
  left: 10%;
}

.confetti:nth-child(even) {
  animation-delay: 0.3s;
  left: 20%;
}

.confetti:nth-child(3n) {
  animation-delay: 0.5s;
  left: 30%;
}

.confetti:nth-child(4n) {
  animation-delay: 0.7s;
  left: 40%;
}

.confetti:nth-child(5n) {
  animation-delay: 0.9s;
  left: 50%;
}

.confetti:nth-child(6n) {
  animation-delay: 1.1s;
  left: 60%;
}

.confetti:nth-child(7n) {
  animation-delay: 1.3s;
  left: 70%;
}

.confetti:nth-child(8n) {
  animation-delay: 1.5s;
  left: 80%;
}

.confetti:nth-child(9n) {
  animation-delay: 1.7s;
  left: 90%;
}

@keyframes confetti-fall {
  0% {
    top: -10%;
    transform: rotate(0deg);
    opacity: 1;
  }
  100% {
    top: 110%;
    transform: rotate(720deg);
    opacity: 0;
  }
}
</style>
