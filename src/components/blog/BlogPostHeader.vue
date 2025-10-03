<template>
  <div class="blog-post-header" :class="themeClass">
    <div class="blog-post-header__inner">
      <h1 class="blog-post-header__title">{{ title }}</h1>
      <div class="blog-post-header__meta">
        <time :datetime="toISOString(pubDate)">
          {{ formatDate(pubDate) }}
        </time>
        <span
          v-if="author"
          class="blog-post-header__author"
        >by {{ author }}</span>
      </div>
      <BlogTags
        v-if="tags && tags.length > 0"
        :tags="tags"
        :theme="theme"
      />
    </div>
  </div>
</template>

<script>
import BlogTags from './BlogTags.vue';

export default {
  name: 'BlogPostHeader',
  components: {
    BlogTags
  },
  props: {
    title: {
      type: String,
      required: true
    },
    pubDate: {
      type: [Date, String],
      required: true
    },
    author: {
      type: String,
      default: ''
    },
    tags: {
      type: Array,
      default: () => []
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
  methods: {
    formatDate(value) {
      const date = value instanceof Date ? value : new Date(value);
      if (Number.isNaN(date.getTime())) return '';
      return date.toLocaleDateString('en-us', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    },
    toISOString(value) {
      const date = value instanceof Date ? value : new Date(value);
      return Number.isNaN(date.getTime()) ? '' : date.toISOString();
    }
  }
};
</script>

<style scoped>
.blog-post-header {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding-top: 4rem;
}

.blog-post-header__inner {
  max-width: 800px;
  text-align: center;
}

.blog-post-header__title {
  font-size: clamp(2.5rem, 5vw, 3.5rem);
  margin-bottom: 0.5rem;
  text-align: center;
}

.blog-post-header__meta {
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: 1rem;
}

.blog-post-header__author {
  font-style: italic;
  text-align: center;
}

/* Theme-based styling */
.theme-light .blog-post-header__title {
  color: #1a1a1a;
}

.theme-light .blog-post-header__meta {
  color: #666;
}

.theme-dark .blog-post-header__title {
  color: #ffffff;
}

.theme-dark .blog-post-header__meta {
  color: #b0b0b0;
}
</style>
