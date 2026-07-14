import { djangoFetch } from '$lib/server/api';
import type { App, Category } from '$lib/types';

export async function load({ params }) {
  // "all" is a virtual category - fetch every app, no filter
  const appsUrl = params.id === 'all'
    ? '/api/apps/'
    : `/api/apps/?category_id=${params.id}`;

  const [apps, categories] = await Promise.all([
    djangoFetch<App[]>(appsUrl),
    djangoFetch<Category[]>('/api/categories/')
  ]);

  const activeCategory = params.id === 'all'
    ? null
    : categories.find((c) => String(c.id) === params.id) ?? null;

  return { apps, categories, activeCategory };
}
