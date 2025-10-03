<template>
  <footer
    v-if="!hideFooter"
    class="site-footer"
    :class="[`theme-${computedTheme}`]"
    :style="computedBackgroundColor ? { backgroundColor: computedBackgroundColor } : {}"
  >
    <div class="site-footer__container">
      <div class="site-footer__content">
        <p class="copyright">
          <span class="font-bold">© 2025 Nick Berens</span>
        </p>
        <p class="site-footer__text">
          <span class="git">OK ❤️ you byyyye.</span>
          <span v-if="false" class="git">latest-commit: <span
            class="git-paren">(
          </span><span class="git-hash">
            <span class="tooltip-container">
              <a :href="`${repoUrl}/commit/${commitHash}`" target="_blank" rel="noopener noreferrer">
                {{ commitHash }}
              </a>
              <span class="tooltip">{{ typeof commitMessage === 'object' ? commitMessage.message : commitMessage }}</span>
            </span>
          </span><span class="git-paren">)</span></span>
        </p>
      </div>
    </div>
  </footer>
</template>

<script>
export default {
  name: 'SiteFooter',
  props: {
    commitHash: {
      type: String,
      default: 'unknown'
    },
    commitMessage: {
      type: [String, Object],
      default: 'No commit message available'
    },
    repoUrl: {
      type: String,
      default: 'https://github.com'
    },
    theme: {
      type: String,
      default: 'light'
    },
    backgroundColor: {
      type: String,
      default: null
    },
    hideFooter: {
      type: Boolean,
      default: false,
    }
  },
  data() {
    return {
      lastSectionColor: null,
      lastSectionTheme: null
    }
  },
  computed: {
    computedTheme() {
      return this.lastSectionTheme || this.theme;
    },
    computedBackgroundColor() {
      return this.lastSectionColor || this.backgroundColor;
    }
  },
  mounted() {
    // Find all page sections
    const pageSections = document.querySelectorAll('.page-section');

    // If there are page sections, get the last one
    if (pageSections.length > 0) {
      const lastSection = pageSections[pageSections.length - 1];

      if (lastSection.dataset.footerColor) {
        this.lastSectionColor = lastSection.dataset.footerColor;
      } else {
        this.lastSectionColor = lastSection.dataset.sectionColor || null;
      }
      if (lastSection.dataset.footerTheme) {
        this.lastSectionTheme = lastSection.dataset.footerTheme;
      } else if (lastSection.dataset.sectionTheme) {
        this.lastSectionTheme = lastSection.dataset.sectionTheme;
      }
    }
  }
}
</script>

<style scoped>
.site-footer {
  padding: 1rem 0;
  width: 100%;
  transition: background-color 0.3s ease-in-out, color 0.3s ease-in-out;
  border-top: 1px dashed #222222;
}

/* Custom tooltip styles */
.tooltip-container {
  position: relative;
  display: inline-block;
}

@media (max-width: 768px) {
  .site-footer__text {
    font-size: 0.8rem;
  }
}

.tooltip {
  visibility: hidden;
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  background-color: #333;
  color: white;
  text-align: center;
  padding: 5px 10px;
  border-radius: 4px;
  white-space: nowrap;
  z-index: 1;
  opacity: 0;
  transition: opacity 0.1s ease-in-out;
  margin-bottom: 5px;
  font-size: 0.8rem;
  max-width: 250px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tooltip::after {
  content: "";
  position: absolute;
  top: 100%;
  left: 50%;
  margin-left: -5px;
  border-width: 5px;
  border-style: solid;
  border-color: #333 transparent transparent transparent;
}

.tooltip-container:hover .tooltip {
  visibility: visible;
  opacity: 1;
}

.site-footer__container {
  margin: 0 auto;
  padding: 0 1.5rem;
  display: flex;
  justify-content: center;
  align-items: center;
}

.site-footer__content {
  text-align: center;
  display: flex;
  align-items: center;
}

.site-footer__text {
  margin: 0;
  font-size: 0.9rem;
}

/* Theme-based Styling */
.site-footer.theme-light {
  color: white;
  background-color: black;
}

.site-footer.theme-light .git {
  color: blue;
}

.site-footer.theme-light .git-hash a {
  color: red;
  text-decoration: none;
}

.site-footer.theme-light .git-hash a:hover {
  text-decoration: underline;
}

.site-footer.theme-dark .git {
  color: #82aaff;
}

.site-footer.theme-dark .git-paren {
  color: #82aaff;
}

.site-footer.theme-dark .git-hash a {
  color: #ff8282;
  text-decoration: none;
}

.site-footer.theme-dark .git-hash a:hover {
  text-decoration: underline;
}

.copyright {
  display: block;
  font-size: 0.9rem;
  margin-right: 2rem;
}

.theme-light .copyright {
  color: black;
}

.theme-dark .copyright {
  color: yellow;
}



@media (max-width: 768px) {
  .site-footer {
    text-align: center;
    padding: .5rem 0;
  }
  .site-footer__container, .site-footer__content {
    display: block;
  }
  .copyright {
    margin: 0;
  }
}
</style>
