<template>
  <section
    class="page-section"
    :class="{
      'page-section--full-height': fullHeight,
      'page-section--full-width': fullWidth,
      'page-section--no-padding': noPadding,
    }"
    :style="{ backgroundColor: backgroundColor }"
    v-bind="$attrs"
  >
    <div
      class="page-section__inner"
      :class="[themeClass, { 'page-section__inner--full-width': fullWidth }]"
      :style="fullWidth ? {} : { maxWidth: width + 'px' }"
    >
      <slot name="default"></slot>
    </div>
  </section>
</template>

<script>
export default {
  name: 'PageSection',
  inheritAttrs: false,
  props: {
    backgroundColor: {
      type: String,
      default: 'transparent'
    },
    fullHeight: {
      type: Boolean,
      default: false
    },
    fullWidth: {
      type: Boolean,
      default: false
    },
    noPadding: {
      type: Boolean,
      default: false
    },
    width: {
      type: [String, Number],
      default: 1400
    }
  },
  computed: {
    themeClass() {
      const theme = this.$attrs['data-section-theme'];
      return theme ? `text-on-${theme}` : '';
    }
  },
}
</script>

<style scoped>
.page-section {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4rem 1.5rem;
}

.page-section__inner {
  width: 100%;
  margin: 0 auto;
}

@supports not (height: 100dvh) {
  .page-section--full-height {
    min-height: calc(100vh - var(--site-header-height) + var(--space-5));
  }
}


@supports (height: 100dvh) {
  .page-section--full-height {
    min-height: calc(100dvh - var(--site-header-height) + var(--space-5));
  }
}


.page-section--full-width {
  padding: 4rem 0;
}
.page-section--full-width.page-section--full-height {
  padding: 0;
}
.page-section--no-padding {
  padding: 0;
}

.page-section__inner--full-width {
  width: 100%;
  padding: 0;
}
</style>
