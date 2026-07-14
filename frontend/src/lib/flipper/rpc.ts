/**
 * Flipper RPC over WebSerial.
 *
 * The Flipper speaks a length-delimited Protobuf protocol once you switch its
 * serial CLI into "RPC mode". Every message is a `PB.Main` envelope carrying a
 * `commandId` (to match responses to requests), an optional `hasNext` flag (for
 * responses split across several frames), and a `oneof` payload selecting the
 * actual command.
 *
 * Two kinds of traffic share one serial port:
 *   1. Request/response commands (ping, mkdir, device info, file write, ...).
 *      Each sends a frame and reads until a frame with the same commandId returns.
 *   2. The screen stream: after startScreenStream, the Flipper pushes
 *      unsolicited guiScreenFrame messages continuously until stopped.
 *
 * Because both read from the same port, they cannot run at once — the caller
 * must pause the stream (`stopScreenStream`) before issuing commands, then
 * resume it. See the store's install flow.
 */
import { PB } from './protobufCompiled.js';
import Protobuf from 'protobufjs/minimal.js';
import type { FlipperSerial } from './serial';

const enc = new TextEncoder();
const dec = new TextDecoder();

/**
 * Reassembles the raw serial byte stream into decoded `PB.Main` messages.
 *
 * Frames are length-delimited (a varint length prefix, then that many bytes).
 * Bytes arrive in arbitrary chunks, so this buffers them and emits whole frames
 * as they complete. It is deliberately tolerant: if the buffer starts with
 * junk that isn't a valid frame (e.g. the echoed CLI text during handshake), it
 * drops one byte and resyncs rather than throwing.
 */
class FrameDecoder {
  private buffer = new Uint8Array(0);

  // Feed a chunk of bytes; returns any complete messages that are now decodable
  push(chunk: Uint8Array): any[] {
    // append the new chunk to whatever partial data we're holding
    const merged = new Uint8Array(this.buffer.length + chunk.length);
    merged.set(this.buffer);
    merged.set(chunk, this.buffer.length);
    this.buffer = merged;

    const messages: any[] = [];
    while (this.buffer.length > 0) {
      // peek the length prefix to see if a whole frame has arrived yet
      let haveWholeFrame = false;
      try {
        const reader = Protobuf.Reader.create(this.buffer);
        const len = reader.uint32();
        haveWholeFrame = reader.pos + len <= this.buffer.length;
      } catch {
        break; // not even a full length prefix yet - wait for more bytes
      }
      if (!haveWholeFrame) break; // partial frame - wait for the rest

      try {
        const reader = Protobuf.Reader.create(this.buffer);
        const msg = PB.Main.decodeDelimited(reader);
        this.buffer = this.buffer.slice(reader.pos); // consume the frame
        messages.push(msg);
      } catch {
        // a full-length span that isn't a valid Main - junk. Drop a byte, resync.
        this.buffer = this.buffer.slice(1);
      }
    }
    return messages;
  }
}

/**
 * Wakes the Flipper CLI and switches it into RPC mode.
 *
 * The CLI greets with a banner ending in a `>: ` prompt. We send
 * `start_rpc_session`, then drain the command echo the Flipper mirrors back -
 * after that echo, the byte stream is pure Protobuf.
 */
export async function enterRpcMode(serial: FlipperSerial, log: (s: string) => void): Promise<void> {
  // wake the CLI and wait for its prompt
  await serial.writeRaw(enc.encode('\r\n'));
  if (!(await readTextUntil(serial, '>: ', 3000))) {
    throw new Error('never saw CLI prompt');
  }
  log('✓ CLI prompt');

  // request RPC mode, then swallow the echoed command text so the decoder
  // only ever sees real Protobuf frames afterward
  await serial.writeRaw(enc.encode('start_rpc_session\r'));
  let echo = '';
  const deadline = Date.now() + 1000;
  while (Date.now() < deadline) {
    const chunk = await serial.readRaw();
    if (!chunk) continue;
    echo += dec.decode(chunk, { stream: true });
    if (echo.includes('start_rpc_session') && /\n/.test(echo)) break;
  }
  log('✓ RPC mode');
}

// Read decoded text until `marker` appears (or timeout). Used only during handshake
async function readTextUntil(serial: FlipperSerial, marker: string, timeoutMs: number): Promise<boolean> {
  let text = '';
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const chunk = await serial.readRaw();
    if (!chunk) continue;
    text += dec.decode(chunk, { stream: true });
    // for the echo case we just need the command name followed by a newline
    if (text.includes(marker)) return true;
  }
  return false;
}

// Parse a .fim manifest's "Key: Value" lines into a record
function parseManifest(text: string): Record<string, string> {
  const fields: Record<string, string> = {};
  for (const line of text.split('\n')) {
    const idx = line.indexOf(':');
    if (idx === -1) continue;
    const key = line.slice(0, idx).trim();
    const value = line.slice(idx + 1).trim();
    if (key) fields[key] = value;
  }
  return fields;
}

export class FlipperRPC {
  private commandId = 1;
  private decoder = new FrameDecoder();

  // screen-stream state
  private streaming = false;
  private onFrame: ((data: Uint8Array, orientation: number) => void) | null = null;

  constructor(private serial: FlipperSerial, private log: (s: string) => void) {}

  // Encode and send one PB.Main frame. Returns the commandId it was sent with
  private async send(fields: Record<string, unknown>): Promise<number> {
    const id = this.commandId++;
    const frame = PB.Main.create({ commandId: id, ...fields });
    await this.serial.writeRaw(PB.Main.encodeDelimited(frame).finish());
    return id;
  }

  // Read frames until one with id arrives. For single-response commands
  private async readResponse(id: number, timeoutMs = 4000): Promise<any> {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      const chunk = await this.serial.readRaw();
      if (!chunk) continue;
      for (const msg of this.decoder.push(chunk)) {
        if (msg.commandId === id) return msg;
      }
    }
    throw new Error(`RPC timeout (command ${id})`);
  }

  /**
   * Collect a multi-frame response. Some commands (device info, directory
   * listings) answer with several frames sharing one commandId, each flagged
   * `hasNext`, ending with a frame where `hasNext` is false. `handle` is called
   * per matching frame to accumulate whatever it needs.
   */
  private async collectFrames(id: number, handle: (msg: any) => void, timeoutMs = 5000): Promise<void> {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      const chunk = await this.serial.readRaw();
      if (!chunk) continue;
      for (const msg of this.decoder.push(chunk)) {
        if (msg.commandId !== id) continue;
        handle(msg);
        if (!msg.hasNext) return; // final frame
      }
    }
    throw new Error(`RPC timeout (multi-frame command ${id})`);
  }

  // True if the response carried an OK status (0), false/throw otherwise
  private checkStatus(res: any, allowStatuses: number[] = []): void {
    const status = res.commandStatus || 0;
    if (status === 0 || allowStatuses.includes(status)) return;
    throw new Error(PB.CommandStatus[status] ?? `status ${status}`);
  }

  // Round-trips a ping. Proves the RPC pipe works
  async ping(): Promise<boolean> {
    const id = await this.send({ systemPingRequest: {} });
    const res = await this.readResponse(id);
    return res.content === 'systemPingResponse';
  }

  // Fetch the flat key/value device-info map (firmware, hardware, radio, ...)
  async getDeviceInfo(): Promise<Record<string, string>> {
    const info: Record<string, string> = {};
    const id = await this.send({ systemDeviceInfoRequest: {} });
    await this.collectFrames(id, (msg) => {
      const r = msg.systemDeviceInfoResponse;
      if (r?.key) info[r.key] = r.value ?? '';
    });
    return info;
  }

  // List a directory's entries (name + size)
  async storageList(path: string): Promise<Array<{ name: string; size: number }>> {
    const files: Array<{ name: string; size: number }> = [];
    const id = await this.send({ storageListRequest: { path } });
    await this.collectFrames(id, (msg) => {
      for (const f of msg.storageListResponse?.file ?? []) {
        files.push({ name: f.name, size: Number(f.size ?? 0) });
      }
    });
    return files;
  }

  // Total/free space for a path. Returns null if unavailable (e.g. no SD card)
  async storageInfo(path: string): Promise<{ total: number; free: number } | null> {
    const id = await this.send({ storageInfoRequest: { path } });
    try {
      const r = (await this.readResponse(id)).storageInfoResponse;
      return r ? { total: Number(r.totalSpace), free: Number(r.freeSpace) } : null;
    } catch {
      return null; // an error response means the path isn't available
    }
  }

  // Create a directory. Succeeds silently if it already exists
  async mkdir(path: string): Promise<void> {
    const id = await this.send({ storageMkdirRequest: { path } });
    const res = await this.readResponse(id);
    this.checkStatus(res, [PB.CommandStatus.ERROR_STORAGE_EXIST]); // "exists" is fine
    this.log(`✓ mkdir ${path}`);
  }

  /**
   * Write a file, streamed as chunked `storage_write` frames that all share one
   * commandId. Every chunk sets `hasNext` except the last; the Flipper sends a
   * single status response after the final chunk. Writes are awaited one at a
   * time so we don't outrun the device's buffer (natural backpressure).
   */
  async writeFile(path: string, data: Uint8Array, onProgress?: (sent: number, total: number) => void): Promise<void> {
    const CHUNK = 512;
    const id = this.commandId++; // one id shared across all chunks
    let offset = 0;

    do {
      const slice = data.slice(offset, offset + CHUNK);
      offset += slice.length;
      const frame = PB.Main.create({
        commandId: id,
        hasNext: offset < data.length,
        storageWriteRequest: { path, file: { data: slice } }
      });
      await this.serial.writeRaw(PB.Main.encodeDelimited(frame).finish());
      onProgress?.(offset, data.length);
    } while (offset < data.length);

    const res = await this.readResponse(id, 15000);
    this.checkStatus(res);
    this.log(`✓ wrote ${data.length} bytes to ${path}`);
  }

  /**
  * Read a file's contents. The Flipper streams the file back as one or more
  * storage_read frames (hasNext until the last), each carrying a slice of bytes.
  */
  async readFile(path: string): Promise<Uint8Array> {
    const id = await this.send({ storageReadRequest: { path } });

    const parts: Uint8Array[] = [];
    await this.collectFrames(id, (msg) => {
      const data = msg.storageReadResponse?.file?.data;
      if (data) parts.push(data);
    });

    // concatenate the collected chunks into one buffer
    const total = parts.reduce((n, p) => n + p.length, 0);
    const out = new Uint8Array(total);
    let offset = 0;
    for (const p of parts) {
      out.set(p, offset);
      offset += p.length;
    }
    return out;
  }

  /**
  * Read and parse every installed app's manifest (/ext/apps_manifests/*.fim).
  * Returns one key/value record per installed app (fields like Full Name, UID,
  * Version Build API, Path).
  */
  async getInstalledApps(): Promise<Array<Record<string, string>>> {
    let manifestFiles: Array<{ name: string }>;
    try {
      manifestFiles = await this.storageList('/ext/apps_manifests');
    } catch {
      return []; // folder missing -> nothing installed
    }

    const apps: Array<Record<string, string>> = [];
    for (const f of manifestFiles) {
      if (!f.name.endsWith('.fim')) continue;
      try {
        const raw = await this.readFile(`/ext/apps_manifests/${f.name}`);
        apps.push(parseManifest(new TextDecoder().decode(raw)));
      } catch {
        // skip a manifest we can't read
      }
    }
    return apps;
  }

  /**
   * Start mirroring the Flipper's screen. After the start request the Flipper
   * pushes `guiScreenFrame` messages continuously; `_readFrames` runs in the
   * background and hands each to `onFrame`. Because this occupies the serial
   * port, callers must `stopScreenStream()` before issuing other commands.
   */
  async startScreenStream(onFrame: (data: Uint8Array, orientation: number) => void): Promise<void> {
    this.onFrame = onFrame;
    this.streaming = true;
    await this.send({ guiStartScreenStreamRequest: {} });
    this._readFrames(); // background loop — intentionally not awaited
  }

  // Stop the stream and tell the Flipper to stop sending frames
  async stopScreenStream(): Promise<void> {
    this.streaming = false;
    this.onFrame = null;
    await this.send({ guiStopScreenStreamRequest: {} });
  }

  /**
   * Stop the background loop without touching the port. Used on physical
   * unplug, where the device is already gone and any serial write would fail.
   */
  stopStreamingFlag(): void {
    this.streaming = false;
    this.onFrame = null;
  }

  // Background reader: dispatches screen frames until streaming stops or the port dies
  private async _readFrames(): Promise<void> {
    while (this.streaming) {
      let chunk: Uint8Array | null;
      try {
        chunk = await this.serial.readRaw();
      } catch {
        break; // port closed/errored — exit instead of busy-looping
      }
      if (chunk === null) break; // stream ended
      for (const msg of this.decoder.push(chunk)) {
        if (msg.guiScreenFrame && this.onFrame) {
          this.onFrame(msg.guiScreenFrame.data, msg.guiScreenFrame.orientation ?? 0);
        }
      }
    }
    this.streaming = false; // ensure the flag is clear on any exit path
  }
}
