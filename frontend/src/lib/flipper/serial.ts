export class FlipperSerial {
  port: SerialPort | null = null;
  reader: ReadableStreamDefaultReader<Uint8Array> | null = null;
  writer: WritableStreamDefaultWriter<Uint8Array> | null = null;
  log: (msg: string) => void = console.log;

  async connect(): Promise<void> {
    this.log('requesting port…');
    this.port = await navigator.serial.requestPort({
      filters: [{ usbVendorId: 0x0483 }]   // STM (Flipper). Remove filter if it doesn't show up.
    });
    await this.port.open({ baudRate: 115200 });
    this.log('port opened');
    this.reader = this.port.readable!.getReader();
    this.writer = this.port.writable!.getWriter();
  }

  async writeRaw(data: Uint8Array): Promise<void> {
    if (!this.writer) throw new Error('not connected');
    await this.writer.write(data);
  }

  async readRaw(): Promise<Uint8Array | null> {
    if (!this.reader) return null;
    const { value, done } = await this.reader.read();
    return done ? null : value ?? null;
  }

  async disconnect(): Promise<void> {
    try { await this.reader?.cancel(); this.reader?.releaseLock(); } catch {}
    try { await this.writer?.close(); this.writer?.releaseLock(); } catch {}
    try { await this.port?.close(); } catch {}
    this.port = this.reader = this.writer = null;
    this.log('disconnected');
  }
}
