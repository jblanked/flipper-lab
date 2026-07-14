/**
 * Shared Flipper connection state + actions.
 *
 * One Flipper connection is shared across the whole app via the `flipper`
 * rune-store. The connection owns a serial port and an RPC session; the screen
 * stream runs continuously while connected and is paused as needed
 * (commands use the same serial port, so they can't run at once).
 */
import { FlipperSerial } from './serial';
import { enterRpcMode, FlipperRPC } from './rpc';
import { renderFrame } from './frameRenderer';
import type { App } from '$lib/types';

export const flipper = $state({
  connected: false,
  info: null as Record<string, string> | null,
  updatable: {} as Record<number, boolean>,   // app id -> update available

  // install progress (only one install runs at a time)
  installing: null as number | null, // app id currently installing
  phase: '' as '' | 'building' | 'writing',
  progress: 0, // 0–100 for the current phase
  buildMessage: '',

  // per-app outcomes
  failed: {} as Record<number, string>, // app id -> "Unavailable" | "Failed"
  installed: {} as Record<number, boolean>,

  log: [] as string[]
});

// live connection handles (not part of the reactive store)
let serial: FlipperSerial | null = null;
let rpc: FlipperRPC | null = null;
let screenCanvas: HTMLCanvasElement | null = null;

function log(s: string) {
  flipper.log = [...flipper.log, s];
}

// The DeviceInfo component calls this to hand us its <canvas> to render into
export function bindScreenCanvas(c: HTMLCanvasElement) {
  screenCanvas = c;
}

export async function connect() {
  serial = new FlipperSerial();
  serial.log = log;
  await serial.connect(); // must be called from a user gesture
  await enterRpcMode(serial, log);
  rpc = new FlipperRPC(serial, log);

  flipper.connected = true;
  flipper.info = await rpc.getDeviceInfo();
  await enrichWithStorage(); // add SD-card + database status
  beginScreenStream();
}

export async function disconnect() {
  await rpc?.stopScreenStream().catch(() => {});
  await serial?.disconnect().catch(() => {});
  resetConnection();
}

/** Fired by the browser when the device is physically unplugged. The port is
 *  already gone, so we don't touch it — just stop the loop and reset state. */
if (typeof navigator !== 'undefined' && 'serial' in navigator) {
  navigator.serial.addEventListener('disconnect', () => {
    rpc?.stopStreamingFlag();          // flag-only stop; no port I/O
    resetConnection();
    log('⚠ Flipper disconnected');
  });
}

function resetConnection() {
  serial = null;
  rpc = null;
  flipper.connected = false;
  flipper.info = null;
  flipper.installed = {};
  flipper.failed = {};
}

// Ask the device about its SD card + databases and fold the result into info
async function enrichWithStorage() {
  if (!rpc || !flipper.info) return;
  try {
    const entries = await rpc.storageList('/ext');
    if (entries.length === 0) {
      // empty listing - no SD card
      flipper.info.storage_sdcard_status = 'missing';
      flipper.info.storage_databases_status = 'missing';
      return;
    }
    // databases are "installed" if the /ext listing contains a Manifest
    flipper.info.storage_databases_status =
      entries.some((e) => e.name === 'Manifest') ? 'installed' : 'missing';

    const sd = await rpc.storageInfo('/ext');
    if (sd) {
      flipper.info.storage_sdcard_status = 'installed';
      flipper.info.storage_sdcard_total_space = String(sd.total);
      flipper.info.storage_sdcard_free_space = String(sd.free);
    }
  } catch (e) {
    log('storage info failed: ' + (e as Error).message);
  }
}

// Start (or restart) the live screen mirror into the bound canvas
function beginScreenStream() {
  rpc?.startScreenStream((data) => {
    if (screenCanvas) renderFrame(screenCanvas, data, 1);
  });
}

// device firmware fork (from device info) -> the backend's Firmware row id,
// so we build each app against the SDK matching the connected device.
// I hard coded it but we could change this to query the backend for the mapping if we wanted to support new forks without a client update.
const FORK_TO_FIRMWARE_ID: Record<string, number> = {
  Official: 1,
  Momentum: 2,
  Unleashed: 3,
  RogueMaster: 4
};

function firmwareIdForDevice(): number {
  const fork = flipper.info?.firmware_origin_fork ?? 'Official';
  return FORK_TO_FIRMWARE_ID[fork] ?? 1; // default to official
}

/**
 * Install an app: build it on the server (with progress), download the .fap,
 * then write it to the Flipper over RPC. The screen stream is paused for the
 * write (shared serial port) and resumed afterward.
 */
export async function install(app: App) {
  if (!rpc) throw new Error('connect a Flipper first');

  flipper.installing = app.id;
  flipper.phase = 'building';
  flipper.progress = 0;
  delete flipper.failed[app.id];

  try {
    const fwId = firmwareIdForDevice();

    // kick off the server-side build and poll it (unless already cached)
    const start = await (await fetch(`/api/apps/${app.id}/build/?firmware=${fwId}`, { method: 'POST' })).json();
    if (!start.cached && start.job_id) await pollBuild(start.job_id);

    // download the finished .fap
    flipper.phase = 'writing';
    const res = await fetch(`/api/apps/${app.id}/download/?firmware=${fwId}`);
    if (!res.ok) {
      flipper.failed[app.id] = res.status === 502 ? 'Unavailable' : 'Failed';
      return;
    }
    const bytes = new Uint8Array(await res.arrayBuffer());

    // write it to the device (stream paused so the write owns the port)
    await rpc.stopScreenStream().catch(() => {});
    const dir = `/ext/apps/${app.category}`;
    const fapPath = `${dir}/${app.fap_id}.fap`;
    await rpc.mkdir(dir);
    await rpc.writeFile(fapPath, bytes,
      (sent, total) => { flipper.progress = Math.round((100 * sent) / total); });

    // only after the .fap is fully written, add the manifest so detection works
    // on future connections. Written last so a failed .fap never leaves a manifest
    // pointing at a missing file.
    const api = `${flipper.info?.firmware_api_major}.${flipper.info?.firmware_api_minor}`;
const manifestText = await (await fetch(`/api/apps/${app.id}/manifest/?api=${api}&firmware=${fwId}`)).text();
    await rpc.mkdir('/ext/apps_manifests');
    await rpc.writeFile(`/ext/apps_manifests/${app.fap_id}.fim`, new TextEncoder().encode(manifestText));
    flipper.installed[app.id] = true;
  } catch (e) {
    flipper.failed[app.id] = 'Failed';
    log(`✗ ${app.name}: ${(e as Error).message}`);
  } finally {
    if (rpc && flipper.connected) beginScreenStream(); // resume the mirror
    flipper.installing = null;
    flipper.phase = '';
    flipper.progress = 0;
  }
}

/**
 * Check which catalog apps are already on the connected Flipper and mark them
 * installed. Matches by the .fap filename (from each manifest's Path), which
 * equals our fap_id - the manifest UID is the catalog ObjectId we don't store.
 */
export async function refreshInstalled(apps: App[]) {
  if (!rpc || flipper.installing !== null) return;
  try {
    await rpc.stopScreenStream().catch(() => {});
    const manifests = await rpc.getInstalledApps();

    // map installed fap_id -> its recorded Build Commit
    const installedCommits = new Map<string, string>();
    for (const m of manifests) {
      const fapId = m.Path?.split('/').pop()?.replace(/\.fap$/, '');
      if (fapId) installedCommits.set(fapId, m['Build Commit'] ?? '');
    }

    for (const app of apps) {
      if (!installedCommits.has(app.fap_id)) continue;
      flipper.installed[app.id] = true;
      const installedCommit = installedCommits.get(app.fap_id);
      console.log(`[update] ${app.fap_id}: installedCommit="${installedCommit}"`);
      if (installedCommit) {
        const res = await fetch(`/api/apps/${app.id}/commit/`);
        const data = await res.json();
        console.log(`[update]   current="${data.commit}" → updatable=${data.commit !== installedCommit}`);
        if (data.commit && data.commit !== installedCommit) {
          flipper.updatable[app.id] = true;
        }
      } else {
        console.log(`[update]   no installed commit — skipping comparison`);
      }
    }
  } finally {
    if (rpc && flipper.connected) beginScreenStream();
  }
}

// Poll a build job until it finishes, updating progress as it goes
async function pollBuild(jobId: number): Promise<void> {
  while (true) {
    await new Promise((r) => setTimeout(r, 500));
    const job = await (await fetch(`/api/builds/${jobId}/`)).json();
    flipper.progress = job.percent;
    flipper.buildMessage = job.message;
    if (job.status === 'done') return;
    if (job.status === 'failed') throw new Error(job.error || 'build failed');
  }
}
