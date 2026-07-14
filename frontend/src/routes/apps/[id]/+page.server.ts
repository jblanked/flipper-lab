import { djangoFetch } from '$lib/server/api';
import type { App } from '$lib/types';

export async function load({ params }) {
  return { app: await djangoFetch<App>(`/api/apps/${params.id}/`) };
}
