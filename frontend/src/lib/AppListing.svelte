<script lang="ts">
  import type { App, Category } from '$lib/types';
  import AppCard from '$lib/AppCard.svelte';
  import FilterPills from '$lib/FilterPills.svelte';
  import { flipper, refreshInstalled } from '$lib/flipper/store.svelte';

  let { apps, categories, activeCategory = null, title, icon = null, initialQuery = '' }:
    { apps: App[]; categories: Category[]; activeCategory?: Category | null; title: string; icon?: string | null; initialQuery?: string } = $props();
  let query = $state('');

  // seed/re-seed from the prop whenever it changes (e.g. ?q= changes on same route)
  $effect(() => { query = initialQuery; });

  // when connected (and apps loaded), detect which are already on the Flipper
  $effect(() => {
    if (flipper.connected && apps.length) {
      refreshInstalled(apps);
    }
  });

  let filtered = $derived(
    query.trim()
      ? apps.filter((a: App) => a.name.toLowerCase().includes(query.toLowerCase().trim()))
      : apps
  );
</script>

<div class="top-banner" style="view-transition-name: banner;">
  <h1 class="page-title">
    {#if icon}
      <img
        class="title-icon"
        class:title-icon-category={icon.includes('category-icons')}
        src="/{icon}" alt=""
      />
    {/if}
    {title}
  </h1>
  <div class="search-wrapper">
    <svg class="search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4-4"/></svg>
    <input type="text" placeholder="Search" bind:value={query} />
  </div>
</div>

<div style="view-transition-name: filter-pills;">
  <FilterPills {categories} activeCategoryId={activeCategory?.id ?? null} />
</div>

<div class="content-area">
  <div class="app-grid-section">
    {#if filtered.length}
      <div class="app-grid">
        {#each filtered as app (app.id)}
          <AppCard {app} />
        {/each}
      </div>
    {:else}
      <div style="padding: 40px; text-align: center; color: var(--text-secondary);">
        <p style="font-size: 18px;">No apps found</p>
        {#if activeCategory}
          <p style="margin-top: 8px;">There are no apps in the "{activeCategory.name}" category yet.</p>
        {/if}
      </div>
    {/if}
  </div>
</div>
