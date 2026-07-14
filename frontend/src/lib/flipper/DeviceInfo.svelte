<script lang="ts">
  import { flipper } from '$lib/flipper/store.svelte';
  import { capitalize, bytesToSize } from '$lib/utils';
  import FlipperBody from './FlipperBody.svelte';
  import FlipperInfo from './FlipperInfo.svelte';
  import DeviceInfoExpanded from './DeviceInfoExpanded.svelte';

  let showDetails = $state(false);
  let info = $derived(flipper.info);

  // radio stack type number -> human name (WB55 BLE stack variants)
  const RADIO_STACK_TYPES: Record<string, string> = {
    '0': 'Unknown', '1': 'Full', '2': 'HCI', '3': 'Light',
    '4': 'BLE Beacon', '5': 'BLE Basic', '6': 'BLE Full',
    '7': 'Thread', '8': 'Zigbee', '9': 'Mac', '10': 'BLE Thread',
    '11': 'Static', '12': 'BLE HCI'
  };

  // the summary panel's fields, formatted from the raw device-info map
  let firmwareVersion = $derived(info ? `${capitalize(info.firmware_branch)} ${info.firmware_commit}` : '—');
  let hardwareVersion = $derived(
    info ? `${info.hardware_ver}.F${info.hardware_target}B${info.hardware_body}C${info.hardware_connect}` : '—'
  );
  let radioVersion = $derived(
    info ? `${info.radio_stack_major}.${info.radio_stack_minor}.${info.radio_stack_sub}` : '—'
  );
  let radioStackType = $derived(
    info ? (RADIO_STACK_TYPES[info.radio_stack_type] ?? info.radio_stack_type) : '—'
  );
  let databaseStatus = $derived(info?.storage_databases_status ?? '—');
  let sdCardUsage = $derived.by(() => {
    const total = Number(info?.storage_sdcard_total_space);
    const free = Number(info?.storage_sdcard_free_space);
    if (!total) return 'No SD card';
    return `${bytesToSize(total - free)} / ${bytesToSize(total)}`;
  });
</script>

{#if info}
  <div class="device-info column items-center">
    <FlipperBody flipperName={info.hardware_name} flipperColor={info.hardware_color} />

    <button class="device-info__details-btn" onclick={() => (showDetails = true)}>
      <span>Device Info</span>
      <span class="chevron">›</span>
    </button>

    <div class="device-info__panels">
      <FlipperInfo
        {firmwareVersion}
        buildDate={info.firmware_build_date}
        {sdCardUsage} {databaseStatus}
        {hardwareVersion} {radioVersion} {radioStackType} />
    </div>
  </div>

  {#if showDetails}
    <DeviceInfoExpanded onClose={() => (showDetails = false)} />
  {/if}
{:else if flipper.connected}
  <p>Loading device info…</p>
{/if}
