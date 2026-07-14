<script lang="ts">
  import { goto } from '$app/navigation';
  let { data } = $props();
  let app = $derived(data.app);
  let query = $state('');

  function search(e: KeyboardEvent) {
    if (e.key === 'Enter' && query.trim()) goto(`/apps?q=${encodeURIComponent(query.trim())}`);
  }
</script>

<svelte:head><title>{app.name} - Flipper Lab</title></svelte:head>

<div class="top-banner">
  <a href="/apps" class="btn btn-flat" style="padding-left:0;">Back to Apps</a>
  <div class="search-wrapper">
    <svg class="search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4-4"/></svg>
    <input type="text" placeholder="Search" bind:value={query} onkeydown={search} />
  </div>
  <div class="nav-links">
    <a href="https://github.com/flipperdevices/flipper-application-catalog" target="_blank" rel="noopener">Contribute</a>
  </div>
</div>

<div class="app-detail">
  {#if app.screenshots?.length}
    <div class="app-detail-section">
      <div class="app-detail-screenshots">
        {#each app.screenshots as screenshot, i}
          <img src={screenshot} alt="{app.name} screenshot {i + 1}" loading="lazy" />
        {/each}
      </div>
    </div>
  {/if}

  <div class="app-detail-header">
    <div class="app-detail-info">
      <h1>{app.name}</h1>
      <div class="app-detail-meta">
        <span class="meta-item"><span class="meta-label">Version:</span> {app.version}</span>
        <span class="meta-item"><span class="meta-label">Author:</span> {app.author}</span>
        <span class="meta-item">
          <span class="meta-label">Category:</span>
          <a href="/categories/{app.category_id}" style="color:var(--q-primary);">{app.category}</a>
        </span>
      </div>
      <p style="font-size:15px;color:var(--text-secondary);line-height:1.5;">{app.short_description}</p>
      <div class="app-detail-actions">
        <button class="btn btn-primary" onclick={() => {/* WebSerial install hook */}}>INSTALL</button>
      </div>
    </div>
  </div>

  {#if app.description}
    <div class="app-detail-section">
      <h2>Description</h2>
      <p style="white-space:pre-wrap;">{app.description}</p>
    </div>
  {/if}

  {#if app.changelog}
    <div class="app-detail-section">
      <h2>Changelog</h2>
      <p style="white-space:pre-wrap;">{app.changelog}</p>
    </div>
  {/if}
</div>
