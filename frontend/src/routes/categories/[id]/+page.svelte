<script lang="ts">
  import AppListing from '$lib/AppListing.svelte';
  import { categoryIcon } from '$lib/categories';
  import { page } from '$app/state';
  let { data } = $props();

  // "all apps" (no active category) uses the Apps title + apps.svg;
  // a real category uses its name + its icon
  let title = $derived(data.activeCategory ? `${data.activeCategory.name}` : 'Apps');
  let icon = $derived(
    data.activeCategory && categoryIcon(data.activeCategory.name)
      ? `category-icons/${categoryIcon(data.activeCategory.name)}`
      : 'apps.svg'
  );
</script>

<svelte:head><title>{data.activeCategory?.name ?? 'All'} Apps - Flipper Lab</title></svelte:head>

<AppListing apps={data.apps} categories={data.categories}
  activeCategory={data.activeCategory}
  {title} {icon}
  initialQuery={page.url.searchParams.get('q') ?? ''} />
