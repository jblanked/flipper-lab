import { djangoFetch } from '$lib/server/api';
import { json } from '@sveltejs/kit';

export async function POST() {
  return json(await djangoFetch('/api/sync/', { method: 'GET' }));
}
