<script lang="ts">
  import { fade, scale } from 'svelte/transition';
  import { flipper } from '$lib/flipper/store.svelte';

  let { onClose }: { onClose: () => void } = $props();
  let info = $derived(flipper.info ?? {});

  const SECTIONS: Array<{ title: string; keys: Record<string, string> }> = [
    { title: 'Flipper Device', keys: {
      hardware_name: 'Device Name', hardware_model: 'Hardware Model',
      hardware_region: 'Hardware Region', hardware_region_provisioned: 'Hardware Region Provisioned',
      hardware_ver: 'Hardware Version', hardware_otp_ver: 'Hardware OTP Version',
      hardware_uid: 'Serial Number'
    }},
    { title: 'Firmware', keys: {
      firmware_commit: 'Software Revision', firmware_build_date: 'Build Date',
      firmware_target: 'Target', protobuf_version_minor: 'Protobuf Version'
    }},
    { title: 'Radio Stack', keys: { radio_stack_major: 'Software Revision' }}
  ];

  const pretty = (k: string) => k.split('_').map((w) => w[0]?.toUpperCase() + w.slice(1)).join(' ');
  let curated = $derived(new Set(SECTIONS.flatMap((s) => Object.keys(s.keys))));
  let otherKeys = $derived(Object.keys(info).filter((k) => !curated.has(k)).sort());

  // close on Escape
  function onKey(e: KeyboardEvent) { if (e.key === 'Escape') onClose(); }
</script>

<svelte:window onkeydown={onKey} />

<div class="modal-backdrop"
  onclick={(e) => { if (e.target === e.currentTarget) onClose(); }}
  role="presentation"
  transition:fade={{ duration: 200 }}>
  <div
    class="modal-card"
    role="dialog"
    aria-modal="true"
    tabindex="-1"
    transition:scale={{ duration: 200, start: 0.95, opacity: 0 }}>
    <button class="modal-close" onclick={onClose} aria-label="Close">✕</button>

    <h2 class="text-pixelated detail__title">Device Info</h2>

    {#each SECTIONS as section}
      <h3 class="detail__section">{section.title}</h3>
      {#each Object.entries(section.keys) as [key, label]}
        <p class="detail__row"><span>{label}:</span><span>{info[key] ?? '—'}</span></p>
      {/each}
    {/each}

    <h3 class="detail__section">Other</h3>
    {#each otherKeys as key}
      <p class="detail__row"><span>{pretty(key)}:</span><span>{info[key]}</span></p>
    {/each}
  </div>
</div>
