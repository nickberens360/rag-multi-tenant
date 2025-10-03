import { defineCollection, z } from 'astro:content';

const blogCollection = defineCollection({
  type: 'content', // 'content' or 'data'
  schema: z.object({
    title: z.string(),
    description: z.string(),
    pubDate: z.date(),
    updatedDate: z.date().optional(),
    heroImage: z.string().optional(),
    tags: z.array(z.string()).optional(),
    author: z.string().optional(),
    backgroundColor: z.string().optional(), // Add backgroundColor property
    theme: z.enum(['light', 'dark']).optional(), // Add theme property for styling
    aiPrompt: z.string().optional(), // Add aiPrompt property for AI-generated content
  }),
});

const fontsCollection = defineCollection({
  type: 'data',
  schema: z.object({
    name: z.string(),
    family: z.string(),
    category: z.enum(['serif', 'sans-serif', 'display', 'handwriting', 'monospace']),
    weight: z.union([z.number(), z.array(z.number())]).default(400),
    style: z.enum(['normal', 'italic']).default('normal'),
    source: z.string().optional(),
    cssImport: z.string().optional(),
    description: z.string().optional(),
    specimen: z.string().default('The quick brown fox jumps over the lazy dog.'),
    backgroundColor: z.string().optional(),
    isTitleFontBold: z.boolean().default(true),
    titleFontSize: z.string().optional(),
    fontUrl: z.string().optional(),
    sizes: z.array(z.number()).default([12, 14, 16, 18, 20, 24, 28, 32, 36, 48, 60, 72]),
  }),
});

export const collections = {
  'blog': blogCollection,
  'fonts': fontsCollection,
};
