<script lang="ts">
  import type { Category } from '$lib/types';
  import { categoryColor, categoryIcon } from '$lib/categories';

  let { categories, activeCategoryId = null }:
    { categories: Category[]; activeCategoryId?: number | null } = $props();

  const dimmed = (id: number | null) => activeCategoryId !== null && id !== activeCategoryId;
</script>

<div class="filter-pills">
  <a href="/apps" class="filter-pill"
     style="background-color:#EBEBEB; opacity:{activeCategoryId === null ? 1 : 0.5}">
    All apps
  </a>
  {#each categories as cat}
    <a href="/categories/{cat.id}" class="filter-pill"
       style="background-color:{categoryColor(cat.name)}; opacity:{dimmed(cat.id) ? 0.5 : 1}">
      {#if categoryIcon(cat.name)}
        <img class="pill-icon" src="/category-icons/{categoryIcon(cat.name)}" alt="" />
      {/if}
      {cat.name}
    </a>
  {/each}
</div>
