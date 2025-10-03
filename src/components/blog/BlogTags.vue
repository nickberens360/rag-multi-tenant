<template>
  <div class="blog-tags" :class="themeClass">
    <span v-for="tag in tags" :key="tag" class="blog-tag">{{ tag }}</span>
  </div>
</template>

<script>
export default {
  name: 'BlogTags',
  props: {
    tags: {
      type: Array,
      required: true
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
  }
}
</script>

<style scoped>
.blog-tags {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.5rem;
}

.blog-tag {
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.8rem;
}

/* Theme-based styling */
.theme-light .blog-tag {
  background-color: rgba(0, 0, 0, 0.07);
  color: #333333;
}

.theme-dark .blog-tag {
  background-color: rgba(255, 255, 255, 0.39);
  color: #e0e0e0;
}
</style>
