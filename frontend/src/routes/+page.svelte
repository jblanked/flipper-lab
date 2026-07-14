<script lang="ts">
  import { flipper, connect, disconnect } from '$lib/flipper/store.svelte';
  import DeviceInfo from '$lib/flipper/DeviceInfo.svelte';

  let connecting = $state(false);
  async function handleConnect() {
    if (!('serial' in navigator)) { alert('WebSerial needs Chrome or Edge'); return; }
    connecting = true;
    try {
      await connect(); // synchronous from this click = valid user gesture
    } catch (e) {
      console.error(e);
    } finally {
      connecting = false;
    }
  }
</script>

<svelte:head><title>Flipper Lab</title></svelte:head>

<div class="home">
  {#if flipper.connected}
    <DeviceInfo />
    <button class="btn btn-flat" onclick={disconnect}>Disconnect</button>
  {:else}
    <button class="btn btn-primary" onclick={handleConnect} disabled={connecting}>
      {connecting ? 'Connecting…' : 'Connect Flipper'}
    </button>
  {/if}
</div>
