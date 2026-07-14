<script lang="ts">
  import type { App } from '$lib/types';
  import { categoryIcon, categoryColor } from '$lib/categories';
  import { flipper, install } from '$lib/flipper/store.svelte';
  import { scale } from 'svelte/transition';

  let { app }: { app: App } = $props();

  let installing = $derived(flipper.installing === app.id);
  let failed = $derived(flipper.failed[app.id]);        // "Unavailable" | "Failed" | undefined
  let installed = $derived(flipper.installed[app.id]);
  let updatable = $derived(flipper.updatable[app.id]);

  // the button's label reflects the install lifecycle for this app
  let label = $derived.by(() => {
    if (installing) return flipper.phase === 'building' ? 'BUILDING' : `${flipper.progress}%`;
    if (updatable) return 'UPDATE';
    if (installed) return 'INSTALLED';
    if (failed) return failed;
    return 'INSTALL';
  });

  // disabled when: no device, another install is running, or this app failed
  let disabled = $derived(!flipper.connected || flipper.installing !== null || !!failed || (installed && !updatable));

  function onInstall(e: MouseEvent) {
    e.preventDefault(); // the card is a link; don't navigate
    e.stopPropagation();
    install(app).catch((err) => alert(err.message));
  }
</script>

<a href="/apps/{app.id}" class="app-card" in:scale|global={{ duration: 200, start: 0.85, opacity: 0 }}>
  <div class="card-screenshot">
    {#if app.screenshots?.[0]}
      <img src={app.screenshots[0]} alt="{app.name} screenshot" loading="lazy" />
    {:else}
      <div style="color:#999;font-size:40px;">[IMG]</div>
    {/if}
  </div>
  <div class="card-body">
    <div class="card-title">{app.name}</div>
    <div class="card-category" style="background-color:{categoryColor(app.category)}">
      {#if categoryIcon(app.category)}
        <img class="cat-icon" src="/category-icons/{categoryIcon(app.category)}" alt="" />
      {/if}
      {app.category}
    </div>
    <div class="card-description">{app.short_description}</div>
    <div class="card-actions">
      <button class="btn btn-primary"
        class:btn-failed={failed}
        class:btn-installed={installed && !updatable}
        class:btn-update={updatable}
        {disabled}
        onclick={onInstall}>
        {label}
      </button>
    </div>
  </div>
</a>
