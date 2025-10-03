<template>
  <!-- This component doesn't render anything, it just loads blog data -->
</template>

<script>
import { updateBlogItems } from '../stores/ui.js';

export default {
  name: 'BlogMenuLoader',
  props: {
    posts: {
      type: Array,
      required: true
    }
  },
  watch: {
    posts: {
      handler(newPosts) {
        if (newPosts && newPosts.length > 0) {
          // Helper function to convert to Date
          const toDate = (post) => {
            const value = (post && (post.data?.pubDate ?? post.pubDate)) ?? 0;
            const date = value instanceof Date ? value : new Date(value || 0);
            return Number.isNaN(date.getTime()) ? new Date(0) : date;
          };

          // Sort posts by date (newest first) before adding to menu
          const sortedPosts = [...newPosts].sort((a, b) => {
            return toDate(b).getTime() - toDate(a).getTime();
          });

          // Limit to most recent 10 posts for the dropdown
          const recentPosts = sortedPosts.slice(0, 10);

          updateBlogItems(recentPosts);
        }
      },
      deep: true,
      immediate: true
    }
  }
};
</script>
