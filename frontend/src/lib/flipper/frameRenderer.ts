const WIDTH = 128;
const HEIGHT = 64;

/** Flipper framebuffer: 1024 bytes, each byte = 8 vertical pixels of one column.
 *  Byte index i covers x = i % 128, and the 8 bits are y = (i / 128) * 8 + bit. */
export function renderFrame(canvas: HTMLCanvasElement, data: Uint8Array, scale = 1) {
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  ctx.fillStyle = '#ff8200';        // Flipper orange background
  ctx.fillRect(0, 0, WIDTH * scale, HEIGHT * scale);
  ctx.fillStyle = '#000';           // black pixels

  for (let i = 0; i < data.length; i++) {
    const x = i % WIDTH;
    const yByte = Math.floor(i / WIDTH) * 8;
    const byte = data[i];
    for (let bit = 0; bit < 8; bit++) {
      if (byte & (1 << bit)) {
        ctx.fillRect(x * scale, (yByte + bit) * scale, scale, scale);
      }
    }
  }
}
