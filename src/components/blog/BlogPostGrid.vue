<template>
  <div class="blog-post-grid">
    <BlogPostCard
      v-for="post in posts"
      :key="post.slug"
      :post="post"
    />
  </div>
</template>

<script>
import BlogPostCard from './BlogPostCard.vue';

export default {
  name: 'BlogPostGrid',
  components: {
    BlogPostCard
  },
  props: {
    posts: {
      type: Array,
      required: true
    }
  }
}
</script>

<style scoped>
.blog-post-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 2rem;
  margin-top: 2rem;
}
</style>
