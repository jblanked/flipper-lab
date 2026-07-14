import { djangoFetch } from '$lib/server/api';
import type { App, Category } from '$lib/types';

export async function load() {
  const [apps, categories] = await Promise.all([
    djangoFetch<App[]>('/api/apps/'),
    djangoFetch<Category[]>('/api/categories/')
  ]);
  return {
    totalApps: apps.length,
    totalCategories: categories.length,
    featured: apps.slice(0, 6)
  };
}
