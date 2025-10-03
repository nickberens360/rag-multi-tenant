import { defineConfig } from 'astro/config';
import vue from '@astrojs/vue';
import mdx from '@astrojs/mdx';
import icon from "astro-icon";

export default defineConfig({
  // Set canonical site URL so Astro.site is available in code
  site: 'https://nickberens.me',

  integrations: [
    vue({
      appEntrypoint: '/src/plugins/vue-app.js'
    }),
    mdx(),
    icon()
  ],
  vite: {
    // Ensure environment variables are properly loaded
    envPrefix: 'PUBLIC_',
    // Make non-prefixed env vars available to server-side code
    ssr: {
      noExternal: [
        '@fortawesome/fontawesome-svg-core',
        '@fortawesome/free-brands-svg-icons',
        '@fortawesome/free-solid-svg-icons',
        '@fortawesome/vue-fontawesome'
      ]
    }
  }
});
