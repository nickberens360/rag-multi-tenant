<template>
  <header
    v-if="!hideHeader"
    class="site-header"
    :class="[
      `theme-${overlayTheme}`,
      variant === 'mobile-condensed' ? 'site-header--mobile-condensed' : '',
      ]"
    :style="variant !== 'pod' ? headerStyles : {}"
    ref="siteHeader"
  >
    <div class="site-header__container">
      <div class="site-header__logo d-flex align-center">
        <a
          href="/"
          :class="variant === 'pod' ? 'pod' : ''"
          :style="variant === 'pod' ? headerStyles : {}"
          ref="logo"
          @click="handleLogoClick($event)"
        >
          <p class="site-header__name">{{ tenantDisplayName }}</p>
          <p class="site-header__name site-header__name--mobile">{{ tenantDisplayName }}</p>
        </a>
      </div>

      <div class="ml-auto"/>

      <nav
        class="site-header__nav mr-4"
        :class="[variant === 'pod' ? 'pod' : '']"
        :style="variant === 'pod' ? headerStyles : {}"
        ref="nav"
      >
        <ul class="site-header__nav-list">
          <li
            v-for="item in navItemsStore"
            :key="item.url"
            class="site-header__nav-item"
            :class="{ 'has-dropdown': item.hasDropdown }"
          >
            <a
              v-if="!item.hasDropdown"
              :href="item.url"
              :target="item.isExternal ? '_blank' : undefined"
              :rel="item.isExternal ? 'noopener noreferrer' : undefined"
              :aria-label="item.ariaLabel"
              @click="handleNavClick($event)"
            >
              <font-awesome-icon
                v-if="item.icon"
                size="2x"
                :icon="item.icon"
                :class="{ 'icon-bounce': navIconBouncing }"
              />
              <span v-else>{{ item.text }}</span>
            </a>
            <!-- Dropdown Menu -->
            <div
              v-if="item.hasDropdown"
              class="dropdown"
            >
              <button
                class="dropdown-toggle"
                @click="toggleDropdown(item.text)"
                :aria-expanded="isDropdownOpen(item.text)"
                aria-haspopup="menu"
                :aria-controls="getDropdownId(item)"
                @keydown.esc.stop.prevent="closeAllDropdowns"
              >
                <span :class="{ 'nav-border-animate': animatedParent === item.text }">{{ item.text }}</span>
                <font-awesome-icon
                  :icon="['fas', 'chevron-down']"
                  :class="{ 'rotated': isDropdownOpen(item.text) }"
                  class="dropdown-arrow"
                />
              </button>
              <ul
                v-if="isDropdownOpen(item.text)"
                class="dropdown-menu"
                :style="dropdownStyles"
                role="menu"
                :id="getDropdownId(item)"
                @keydown.esc.stop.prevent="closeAllDropdowns"
              >
                <li
                  v-if="!item.dropdownItems || item.dropdownItems.length === 0"
                  class="dropdown-item"
                >
                  <span>No fonts available</span>
                </li>
                <li
                  v-for="subItem in item.dropdownItems"
                  :key="subItem.url"
                  class="dropdown-item"
                >
                  <a
                    :href="subItem.url"
                    @click="handleDropdownItemClick(item.text, $event)"
                    role="menuitem"
                  >
                    {{ subItem.text }}
                  </a>
                </li>
              </ul>
            </div>
          </li>
        </ul>
      </nav>
      <div
        class="site-header__mobile-nav"
        :class="{ 'is-active': isMobileMenuOpen }"
        :style="headerStyles"
        role="dialog"
        aria-modal="true"
        :inert="!isMobileMenuOpen"
        @keydown.esc.stop.prevent="closeMobileMenu"
      >
        <button
          class="site-header__mobile-nav-close"
          @click="closeMobileMenu"
          aria-label="Close menu"
        >
          <font-awesome-icon :icon="['fas', 'times']"/>
        </button>
        <ul class="site-header__mobile-nav-list">
          <li
            v-for="item in navItemsStore"
            :key="item.url"
            class="site-header__mobile-nav-item"
          >
            <!-- Regular nav items -->
            <a
              v-if="!item.hasDropdown"
              :href="item.url"
              :target="item.isExternal ? '_blank' : undefined"
              :rel="item.isExternal ? 'noopener noreferrer' : undefined"
              :aria-label="item.ariaLabel"
              @click="handleMobileNavClick"
            >
              <font-awesome-icon
                v-if="item.icon"
                :icon="item.icon"
                :class="{ 'icon-bounce': navIconBouncing }"
              />
              <span
                v-if="item.icon"
                style="margin-left: 0.5em;"
              >{{ item.text }}</span>
              <span v-else>{{ item.text }}</span>
            </a>

            <!-- Mobile dropdown items -->
            <div
              v-if="item.hasDropdown"
              class="mobile-dropdown"
            >
              <button
                class="mobile-dropdown-toggle"
                @click="toggleMobileDropdown(item.text)"
                :aria-expanded="isMobileDropdownOpen(item.text)"
                aria-haspopup="menu"
                :aria-controls="getMobileDropdownId(item)"
                @keydown.esc.stop.prevent="closeMobileDropdowns"
              >
                <span :class="{ 'nav-border-animate': animatedParent === item.text }">{{ item.text }}</span>
                <font-awesome-icon
                  :icon="['fas', 'chevron-down']"
                  :class="{ 'rotated': isMobileDropdownOpen(item.text) }"
                  class="dropdown-arrow"
                />
              </button>
              <ul
                v-if="isMobileDropdownOpen(item.text)"
                class="mobile-dropdown-menu"
                role="menu"
                :id="getMobileDropdownId(item)"
                @keydown.esc.stop.prevent="closeMobileDropdowns"
              >
                <li
                  v-if="!item.dropdownItems || item.dropdownItems.length === 0"
                  class="mobile-dropdown-item"
                >
                  <span style="color: #666;">No fonts available</span>
                </li>
                <li
                  v-for="subItem in item.dropdownItems"
                  :key="subItem.url"
                  class="mobile-dropdown-item"
                >
                  <a
                    :href="subItem.url"
                    @click="handleMobileNavClick"
                  >
                    {{ subItem.text }}
                  </a>
                </li>
              </ul>
            </div>
          </li>
        </ul>
      </div>
      <div
        class="site-header__icons d-flex align-center"
        :class="variant === 'pod' ? 'pod' : ''"
        :style="variant === 'pod' ? headerStyles : {}"
      >
        <a
          href="/nick-ai"
          class="ai-icon"
          @click="handleAIClick($event)"
        >
          <img
            :src="aiIconSvg"
            alt="AI Icon"
            style="width: 34px;"
            :class="{ 'icon-bounce': aiIconBouncing }"
          />
        </a>
        <button
          class="site-header__hamburger "
          :class="[{ 'is-active': isMobileMenuOpen }, { 'icon-bounce': mobileNavItemClicked }]"
          @click="toggleMobileMenu"
          aria-label="Toggle menu"
        >
          🍔
        </button>
      </div>
    </div>
  </header>
</template>

<script>

import { useStore } from '@nanostores/vue';
import aiIconSvg from '../assets/svg/ai-icon.svg?url';

import { navItems } from '../stores/ui';

export default {
  name: 'SiteHeader',
  components: {},
  props: {
    gitBranch: {
      type: String,
      default: 'main'
    },
    hideHeader: {
      type: Boolean,
      default: false
    },
    variant: {
      type: String,
      default: 'default',
      validator: value => ['default', 'pod', 'mobile-condensed'].includes(value)
    },
    tenantSlug: {
      type: String,
      default: 'nickberens'
    }
  },
  data() {
    return {
      overlayTheme: 'light',
      headerBackgroundColor: 'transparent',
      isMobileMenuOpen: false,
      scrollTimeout: null,
      isTicking: false,
      aiIconSvg,
      openDropdownId: null,
      openMobileDropdownId: null,
      animatedParent: null,
      mobileNavItemClicked: false,
      aiIconBouncing: false,
      navIconBouncing: false,
    };
  },
  computed: {
    navItemsStore() {
      return this.navItemsStoreRaw;
    },
    tenantDisplayName() {
      // Capitalize first letter and replace hyphens with spaces
      return this.tenantSlug
        .split('-')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
    },
    headerStyles() {
      let backgroundColor = this.headerBackgroundColor;

      // Apply rgba with alpha 0.8 only for pod variant
      if (this.variant === 'pod') {
        backgroundColor = this.convertToRgba(backgroundColor, 0.2);
      }

      return {
        backgroundColor: backgroundColor,
      };
    },
    dropdownStyles() {
      let backgroundColor = this.headerBackgroundColor;
      let styles = {};

      // For pod variant, adjust opacity but don't add backdrop-filter
      // since parent already has it
      if (this.variant === 'pod') {
        // Use lower alpha for glass effect since parent has backdrop-filter
        backgroundColor = this.convertToRgba(backgroundColor, 0.6);

        styles = {
          backgroundColor: backgroundColor,
          // Don't add backdrop-filter here - parent pod already has it
          border: '1px solid rgba(255, 255, 255, 0.2)',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)'
        };

        // Adjust for dark theme
        if (this.overlayTheme === 'dark') {
          styles.border = '1px solid rgba(255, 255, 255, 0.1)';
          // Add subtle gradient overlay for dark theme
          styles.backgroundImage = `linear-gradient(135deg, rgba(255, 255, 255, 0.03), rgba(255, 255, 255, 0.01))`;
        }
      } else {
        styles = {
          backgroundColor: backgroundColor
        };
      }

      return styles;
    }
  },
  setup() {
    const navItemsStoreRaw = useStore(navItems);
    return {
      navItemsStoreRaw
    };
  },
  mounted() {
    // Ensure body scroll is enabled when component mounts
    this.isMobileMenuOpen = false;
    document.body.style.overflow = '';

    // Perform initial scroll check to set proper background colors
    this.performScrollCheck();

    // Existing code
    window.addEventListener('scroll', this.handleScroll, { passive: true });

    // Re-run theme detection on page navigation (for view transitions)
    document.addEventListener('astro:page-load', this.boundPageLoad);
    document.addEventListener('astro:after-swap', this.boundAfterSwap);

    // Close dropdowns when clicking outside
    document.addEventListener('click', this.handleClickOutside);
  },
  created() {
    // Create bound methods for event listeners so we can remove them properly
    this.boundPageLoad = () => {
      this.closeAllDropdowns();
      this.performScrollCheck();
    };

    this.boundAfterSwap = () => {
      this.performScrollCheck();
      // Wait for next frame to ensure DOM updates are complete after view transition
      // This ensures proper theme detection after page swap
      requestAnimationFrame(() => this.performScrollCheck());
    };
  },
  beforeUnmount() {
    window.removeEventListener('scroll', this.handleScroll);
    document.removeEventListener('astro:page-load', this.boundPageLoad);
    document.removeEventListener('astro:after-swap', this.boundAfterSwap);
    document.removeEventListener('click', this.handleClickOutside);
    if (this.scrollTimeout) {
      clearTimeout(this.scrollTimeout);
    }
  },
  watch: {
    openDropdownId(newVal) {
      if (newVal) {
        if (this.headerBackgroundColor === 'transparent' && window.scrollY === 0) {
          this.performScrollCheck();
        }
      }
    }
  },
  methods: {
    handleDropdownItemClick(parentText) {
      this.animatedParent = parentText;
      this.closeAllDropdowns();
      // Allow navigation to proceed; animation cleans up on transition
    },
    safeBase64(str) {
      try {
        if (typeof btoa === 'function') return btoa(str);
        if (typeof Buffer !== 'undefined') return Buffer.from(str, 'utf-8').toString('base64');
      } catch (_) {}
      // Fallback to a slug if encoding not possible
      return String(str || '').toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-_]/g, '');
    },
    _getGeneratedId(prefix, item) {
      const text = typeof item === 'string' ? item : item.text;
      const url = typeof item === 'object' && item.url ? item.url : '';
      const uniquePart = url ? this.safeBase64(url).substring(0, 8) : String(text || '').toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-_]/g, '');
      return `${prefix}-${uniquePart}`;
    },
    getDropdownId(item) {
      return this._getGeneratedId('dropdown', item);
    },
    getMobileDropdownId(item) {
      return this._getGeneratedId('mobile-dropdown', item);
    },
    convertToRgba(color, alpha = 0.8) {
      // Handle transparent case
      if (color === 'transparent') {
        return 'transparent';
      }

      // Handle named colors
      const namedColors = {
        'white': '255, 255, 255',
        'black': '0, 0, 0',
        'red': '255, 0, 0',
        'blue': '0, 0, 255',
        'green': '0, 128, 0',
      };

      if (namedColors[color.toLowerCase()]) {
        return `rgba(${namedColors[color.toLowerCase()]}, ${alpha})`;
      }

      // Handle hex colors
      if (color.startsWith('#')) {
        const hex = color.replace('#', '');

        // Validate hex color length (must be 3 or 6 characters)
        if (hex.length !== 3 && hex.length !== 6) {
          // Return original color for invalid hex lengths
          return color;
        }

        // Validate that all characters are valid hex digits
        if (!/^[0-9A-Fa-f]+$/.test(hex)) {
          return color;
        }

        let r, g, b;

        if (hex.length === 3) {
          // Handle 3-character hex (e.g., #f00 -> #ff0000)
          r = parseInt(hex.slice(0, 1) + hex.slice(0, 1), 16);
          g = parseInt(hex.slice(1, 2) + hex.slice(1, 2), 16);
          b = parseInt(hex.slice(2, 3) + hex.slice(2, 3), 16);
        } else {
          // Handle 6-character hex (e.g., #ff0000)
          r = parseInt(hex.slice(0, 2), 16);
          g = parseInt(hex.slice(2, 4), 16);
          b = parseInt(hex.slice(4, 6), 16);
        }

        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
      }

      // Handle rgb colors - convert to rgba
      if (color.startsWith('rgb(')) {
        const rgbValues = color.match(/\d+/g);
        if (rgbValues && rgbValues.length === 3) {
          return `rgba(${rgbValues[0]}, ${rgbValues[1]}, ${rgbValues[2]}, ${alpha})`;
        }
      }

      // Handle rgba colors - update alpha
      if (color.startsWith('rgba(')) {
        const rgbaMatch = color.match(/rgba\((\d+),\s*(\d+),\s*(\d+),\s*[\d.]+\)/);
        if (rgbaMatch) {
          return `rgba(${rgbaMatch[1]}, ${rgbaMatch[2]}, ${rgbaMatch[3]}, ${alpha})`;
        }
      }

      // Fallback - return original color if can't convert
      return color;
    },
    toggleMobileMenu() {
      this.isMobileMenuOpen = !this.isMobileMenuOpen;
      document.body.style.overflow = this.isMobileMenuOpen ? 'hidden' : '';
    },
    closeMobileMenu() {
      this.isMobileMenuOpen = false;
      this.openMobileDropdownId = null;
      document.body.style.overflow = '';
    },
    toggleDropdown(itemText) {
      this.openDropdownId = this.openDropdownId === itemText ? null : itemText;
    },
    toggleMobileDropdown(itemText) {
      this.openMobileDropdownId = this.openMobileDropdownId === itemText ? null : itemText;
    },
    isDropdownOpen(itemText) {
      return this.openDropdownId === itemText;
    },
    isMobileDropdownOpen(itemText) {
      return this.openMobileDropdownId === itemText;
    },
    closeAllDropdowns() {
      this.openDropdownId = null;
    },
    closeMobileDropdowns() {
      this.openMobileDropdownId = null;
    },
    handleClickOutside(event) {
      // Check if the click is outside all dropdown elements
      if (!event.target.closest('.dropdown') && !event.target.closest('.mobile-dropdown')) {
        this.openDropdownId = null;
        this.openMobileDropdownId = null;
      }
    },
    handleScroll() {
      if (this.isTicking) return;
      this.isTicking = true;
      requestAnimationFrame(() => {
        this.performScrollCheck();
        this.isTicking = false;
      });
    },
    performScrollCheck() {
      const headerEl = this.$refs.siteHeader;
      if (!headerEl) return;

      // Use requestAnimationFrame to ensure DOM is ready
      requestAnimationFrame(() => {
        // Check for pages with single dark full-height sections (like nick-ai, resume)
        const allPageSections = document.querySelectorAll('.page-section');
        const darkSections = document.querySelectorAll('[data-section-theme="dark"]');
        const blackSections = document.querySelectorAll('[data-section-color="black"]');


        // Apply dark theme if there's exactly one PageSection AND it has dark theme
        if (allPageSections.length === 1 && darkSections.length === 1 && blackSections.length === 1) {
          this.headerBackgroundColor = blackSections[0].dataset.sectionColor;
          this.overlayTheme = darkSections[0].dataset.sectionTheme;
          return;
        }

        // Fallback: Try intersection detection with multiple check points
        const headerRect = headerEl.getBoundingClientRect();
        const checkPoints = [
          { x: window.innerWidth / 2, y: headerRect.bottom + 20 },
          { x: window.innerWidth / 2, y: headerRect.bottom + 50 },
          { x: window.innerWidth / 2, y: headerRect.bottom + 100 }
        ];

        // Temporarily disable pointer events
        headerEl.style.pointerEvents = 'none';

        let colorSection = null;
        let themeSection = null;

        for (const point of checkPoints) {
          const elementUnder = document.elementFromPoint(point.x, point.y);
          if (elementUnder && elementUnder.tagName !== 'HTML' && elementUnder.tagName !== 'BODY') {
            colorSection = elementUnder.closest('[data-section-color]');
            themeSection = elementUnder.closest('[data-section-theme]');
            if (colorSection || themeSection) break;
          }
        }

        headerEl.style.pointerEvents = 'auto';

        this.headerBackgroundColor = colorSection
          ? colorSection.dataset.sectionColor
          : (window.scrollY > 0 ? 'white' : 'transparent');
        this.overlayTheme = themeSection ? themeSection.dataset.sectionTheme : 'light';

      });
    },
    handleNavClick(event) {
      const link = event.currentTarget;

      // Check if it's an icon or text - look for FontAwesome components
      const iconElement = link.querySelector('svg[data-icon], .fa-icon, [class*="fa-"]');
      const textElement = link.querySelector('span:not([class*="fa"]):not([data-icon])');

      if (iconElement) {
        // Handle icon animation (like GitHub) - only prevent default for external links
        this.navIconBouncing = true;
        // Reset the flag after the animation duration to stop the animation
        setTimeout(() => {
          this.navIconBouncing = false;
        }, 600); // Corresponds to animation duration

        if (link.target === '_blank') {
          event.preventDefault();
          const newWin = window.open(link.href, '_blank', 'noopener,noreferrer');
          if (newWin) newWin.opener = null;
        }
      } else if (textElement && textElement.textContent.trim()) {
        // Handle text animation with border effect - don't prevent default
        // Add border animation class to the text element
        textElement.classList.add('nav-border-animate');
        // Don't remove the class - let the view transition handle cleanup
      }
    },
    handleLogoClick(event) {
      const link = event.currentTarget;
      const nameElements = link.querySelectorAll('.site-header__name');

      // Add border animation to visible name elements
      nameElements.forEach(nameEl => {
        if (nameEl.offsetParent !== null) { // Check if visible
          nameEl.classList.add('nav-border-animate');
        }
      });
    },
    handleAIClick(event) {
      this.aiIconBouncing = true;
      // Reset the flag after the animation duration to stop the animation
      setTimeout(() => {
        this.aiIconBouncing = false;
      }, 600); // Corresponds to animation duration
    },
    animateHamburger() {
      this.mobileNavItemClicked = true;
      // Reset the flag after the animation duration
      setTimeout(() => {
        this.mobileNavItemClicked = false;
      }, 600); // Corresponds to animation duration
    },
    handleMobileNavClick() {
      // Combined method for mobile navigation clicks
      this.animateHamburger();
      this.closeMobileMenu();
    }
  }
};
</script>

<style scoped>
.site-header {
  position: fixed;
  right: 0;
  left: 0;
  top: 0;
  width: 100%;
  z-index: var(--z-index-header);
  transition: background-color 0.3s ease-in-out, box-shadow 0.3s ease-in-out, color 0.3s ease-in-out;
  height: var(--site-header-height);
}

.site-header__container {
  margin: 0 auto;
  padding: 0 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100%;
}

.site-header__logo {
  position: relative;
  z-index: var(--z-index-modal);
  color: var(--text-color, #000);
  text-decoration: none;
  height: 100%;
}

.site-header__name--mobile {
  display: none;
}

.theme-dark .site-header__logo {
  color: #fff;
}

.site-header__logo a {
  color: black;
  text-decoration: none;
}

.theme-dark .site-header__logo a {
  color: #fff;
}

.site-header__logo p {
  margin: 0;
  font-size: clamp(1rem, 1rem + 0.5vw, 1.5rem);
  font-weight: bold;
}

.site-header__nav {
  display: block;
}

.site-header__nav-list {
  display: flex;
  align-items: center;
  list-style: none;
  margin: 0;
  padding: 0;
}

.site-header__nav-item {
  margin-left: 1.5rem;
}

.site-header__nav-item:first-child {
  margin-left: 0;
}

.site-header__nav-item a {
  text-decoration: none;
  color: inherit;
  font-weight: 500;
  transition: color 0.3s ease;
}

.site-header.theme-light .site-header__nav-item a:hover {
  color: #2a2a2a;
}

/* Hamburger Menu Button - Hidden on desktop */
.site-header__hamburger {
  display: none;
  background: none;
  border: none;
  cursor: pointer;
  z-index: var(--z-index-drawer);
  font-size: 2rem;
  line-height: 1;
  padding: 0;
}

.site-header__icons {
  gap: .5rem;
}

.ai-icon {
  text-decoration: none;
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.pod {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 0.5rem;
  height: 85%;
  padding: 0 1.5rem;
  border-radius: 200px;

  /* Enhanced glass effect */
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 10px 15px -3px #0000004d, 0 -4px 6px -2px #0000000d;
  transition: all 0.3s ease-in-out;
}

.theme-dark .pod {
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37),
  inset 0 1px 0 0 rgba(255, 255, 255, 0.1),
  0 1px 0 0 rgba(255, 255, 255, 0.05);

  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.05),
    rgba(255, 255, 255, 0.02)
  );
}

.site-header__hamburger.pod {
  display: none;
}


/* Mobile Navigation */
.site-header__mobile-nav {
  display: none;
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100vh;
  z-index: var(--z-index-highest);
  /* Semi-transparent background for backdrop-filter to work */
  background-color: rgba(255, 255, 255, 0.8);
  /* Add backdrop-filter for blur effect */
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  padding-top: 80px;
  transform: translateY(-100%);
  transition: transform 0.3s ease;
}

.theme-dark .site-header__mobile-nav {
  /* Semi-transparent dark background */
  background-color: rgba(26, 26, 26, 0.8);
  color: #fff;
}

@supports not (height: 100dvh) {
  .site-header__mobile-nav {
    height: 100vh;
  }
}

@supports (height: 100dvh) {
  .site-header__mobile-nav {
    height: 100dvh;
  }
}

.site-header__mobile-nav.is-active {
  transform: translateY(0);
}

.site-header__mobile-nav-list {
  list-style: none;
  padding: 0;
  margin: 0;
  text-align: center;
}

.site-header__mobile-nav-item {
  margin: 1.5rem 0;
}

.site-header__mobile-nav-item a {
  text-decoration: none;
  color: inherit;
  font-size: clamp(1.3rem, 1.3rem + 0.5vw, 1.8rem);
  transition: color 0.3s ease;
}

.site-header__mobile-nav-item a:hover {
  color: #666;
}

.site-header__mobile-nav-close {
  position: absolute;
  top: 20px;
  right: 20px;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.5rem;
  color: inherit;
  z-index: var(--z-index-drawer);
  padding: 0.5rem;
  border-radius: 50%;
  height: 40px;
  width: 40px;
  transition: background-color 0.3s ease, color 0.3s ease;
}

.site-header__mobile-nav-close:hover {
  background-color: rgba(0, 0, 0, 0.1);
}

.theme-dark .site-header__mobile-nav-close:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.site-header__hamburger.pod {
  height: 57px;
  width: 57px;
  border-radius: 50%;
  padding: 0;
}

/* Media Query for Mobile Layout */
@media (max-width: 1200px) {
  .site-header__container {
    padding: 0 1rem;
  }

  .site-header__hamburger.pod {
    display: flex;
  }

  /* Hide desktop navigation */
  .site-header__nav {
    display: none;
  }

  /* Show hamburger menu */
  .site-header__hamburger {
    display: block;
  }

  /* Show mobile navigation menu */
  .site-header__mobile-nav {
    display: block;
  }
}

@media (max-width: 768px) {
  .site-header__container {
    padding: 0 .75rem;
  }

  .site-header--mobile-condensed .ai-icon {
    display: none !important;
  }

  .pod {
    height: 65%;
    padding: 0 .75rem;
  }

  .site-header__hamburger.pod {
    height: 45px;
    width: 45px;
  }
}

@media (max-width: 600px) {
  .site-header__name {
    display: none;
  }

  .site-header__name--mobile {
    display: block;
  }
}

/* Theme-based Styling for Text */
.site-header.theme-light {
  color: #000000;
}

.site-header.theme-light .git {
  color: blue;
}

.site-header.theme-light .git-branch {
  color: red;
}

.site-header.theme-dark {
  color: #ffffff;
}

.site-header.theme-dark .git {
  color: #82aaff;
}

.site-header.theme-dark .git-branch {
  color: #ff8282;
}

.site-header.theme-dark .git-paren {
  color: #82aaff;
}


/* Dropdown Styles */
.site-header__nav-item.has-dropdown {
  position: relative;
}

.dropdown {
  position: relative;
}

.dropdown-toggle {
  background: none;
  border: none;
  color: inherit;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: inherit;
  padding: 0;
}

.dropdown-arrow {
  font-size: 0.8em;
  transition: transform 0.3s ease;
}

.dropdown-arrow.rotated {
  transform: rotate(180deg);
}

.dropdown-menu {
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  list-style: none;
  padding: 0.5rem 0;
  min-width: 180px;
  z-index: var(--z-index-modal);
  margin: 0.5rem 0 0;
  transition: background-color 0.2s ease, box-shadow 0.2s ease;
}

.pod .dropdown-menu {
  top: 180%;
}

.theme-dark .dropdown-menu {
  border: 1px solid #404040;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  color: #fff;
}

.theme-light .dropdown-menu {
  color: #000;
}

.dropdown-item {
  margin: 0;
}

.dropdown-item a {
  display: block;
  padding: 0.5rem 1rem;
  color: inherit;
  text-decoration: none;
  transition: background-color 0.2s ease;
}

.dropdown-item a:hover {
  background-color: rgba(0, 0, 0, 0.05);
}

.theme-dark .dropdown-item a:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

/* Mobile dropdown styles */
.mobile-dropdown-toggle {
  background: none;
  border: none;
  color: inherit;
  font-size: clamp(1.3rem, 1.3rem + 0.5vw, 1.8rem);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0;
  width: 100%;
  justify-content: center;
}

.mobile-dropdown-menu {
  list-style: none;
  margin: 0.5rem 0 0 0;
  padding: 0;
}

.mobile-dropdown-item {
  margin: 0.5rem 0;
}

.mobile-dropdown-item a {
  display: block;
  color: inherit;
  text-decoration: none;
  font-size: 1.1rem;
  padding: 0.25rem 0;
  transition: color 0.3s ease;
}

.mobile-dropdown-item a:hover {
  color: #666;
}


/* Navigation border animation */
@keyframes navBorderGrow {
  0% {
    width: 0%;
  }
  100% {
    width: 100%;
  }
}

:deep(.nav-border-animate) {
  position: relative;
}

:deep(.nav-border-animate::after) {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 0;
  height: 2px;
  background-color: currentColor;
  animation: navBorderGrow 0.8s ease-out forwards;
}

/* Icon bounce animation */
@keyframes iconBounce {
  0%, 100% {
    transform: translateY(0);
  }
  25% {
    transform: translateY(-8px);
  }
  50% {
    transform: translateY(0);
  }
  75% {
    transform: translateY(-4px);
  }
}

:deep(.icon-bounce) {
  animation: iconBounce 0.6s ease-out;
}

</style>
