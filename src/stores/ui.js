import { atom } from 'nanostores';

// Font items store - will be populated dynamically
export const fontItems = atom([]);

// Blog items store - will be populated dynamically
export const blogItems = atom([]);

// Navigation items store
export const navItems = atom([
  { text: 'nick.AI', url: '/nick-ai' },
  { text: 'Illustrations', url: '/illustrations' },
  { text: 'Atomic Docs', url: '/atomic-docs' },
  { text: 'Blog', url: '/blog' },
  {
    text: 'Fonts',
    url: '#',
    hasDropdown: true,
    dropdownItems: [] // Will be populated from fontItems
  },
  { text: 'Resume', url: '/resume' },
 // { text: 'Contact', url: '/#contact' },
  {
    text: 'GitHub',
    url: 'https://github.com/nickberens360',
    isExternal: true,
    icon: ['fab', 'github'],
    ariaLabel: 'GitHub Profile'
  }
]);

// Helper function to update blog items (keeping for potential future use)
export const updateBlogItems = (blogs) => {
  const blogMenuItems = blogs.map(blog => {
    // For Astro content collections, blog.slug is the URL path
    // blog.data contains the actual content metadata
    const blogSlug = blog.slug || blog.id || 'unknown';
    const blogTitle = blog.data?.title || blog.title || 'Unknown Post';
    const menuItem = {
      text: blogTitle,
      url: `/blog/${blogSlug}`
    };
    return menuItem;
  });

  // Store blog items for potential future use
  blogItems.set(blogMenuItems);
};

// Helper function to update font items
export const updateFontItems = (fonts) => {
  const fontMenuItems = fonts.map(font => {
    // For Astro content collections, font.id is the filename without extension
    // font.data contains the actual JSON content
    const fontId = font.id || font.slug || 'unknown';
    const fontName = font.data?.name || font.name || 'Unknown Font';
    const menuItem = {
      text: fontName,
      url: `/fonts/${fontId}`
    };
    return menuItem;
  });

  // Add "All Fonts" link at the beginning
  const allFontsLink = { text: 'All Fonts', url: '/fonts' };
  const fontMenuItemsWithAll = [allFontsLink, ...fontMenuItems];

  fontItems.set(fontMenuItemsWithAll);

  // Update the navItems with the new font dropdown items
  const currentNavItems = navItems.get();

  const updatedNavItems = currentNavItems.map(item => {
    if (item.text === 'Fonts') {
      const updated = { ...item, dropdownItems: fontMenuItemsWithAll };
      return updated;
    }
    return item;
  });

  navItems.set(updatedNavItems);
};

// Image overlay state
export const imageOverlayStore = atom({
  isOpen: false,
  imageSrc: null
});

// Helper functions to open and close the overlay
export const openImageOverlay = (src) => {
  imageOverlayStore.set({
    isOpen: true,
    imageSrc: src
  });
};

export const closeImageOverlay = () => {
  imageOverlayStore.set({
    isOpen: false,
    imageSrc: null
  });
};
