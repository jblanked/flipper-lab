import { DJANGO_API_URL } from '$env/static/private';

export async function djangoFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${DJANGO_API_URL}${path}`, init);
  if (!res.ok) throw new Error(`Django ${res.status}: ${path}`);
  return res.json() as Promise<T>;
}
