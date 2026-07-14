<script lang="ts">
  // the device-info summary readout. All values are pre-formatted strings.
  let {
    firmwareVersion = '—',
    buildDate = '—',
    sdCardUsage = '—',
    databaseStatus = '—',
    hardwareVersion = '—',
    radioVersion = '—',
    radioStackType = '—'
  }: {
    firmwareVersion?: string;
    buildDate?: string;
    sdCardUsage?: string;
    databaseStatus?: string;
    hardwareVersion?: string;
    radioVersion?: string;
    radioStackType?: string;
  } = $props();
</script>

<div class="info">
  <p><span>Firmware:</span><span>{firmwareVersion}</span></p>
  <p><span>Build date:</span><span>{buildDate}</span></p>
  <p><span>SD card:</span><span>{sdCardUsage}</span></p>
  <p><span>Databases:</span><span>{databaseStatus}</span></p>
  <p><span>Hardware:</span><span>{hardwareVersion}</span></p>
  <p><span>Radio FW:</span><span>{radioVersion}</span></p>
  <p><span>Radio stack:</span><span>{radioStackType}</span></p>
</div>
