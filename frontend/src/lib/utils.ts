// Small formatting helpers shared across components

// Capitalize the first letter: "dev" → "Dev"
export const capitalize = (s: string): string =>
  s ? s[0].toUpperCase() + s.slice(1) : '';

// Human-readable binary size: 1536 → "1.5 KiB"
export function bytesToSize(bytes: number): string {
  if (!bytes) return '0 B';
  const units = ['B', 'KiB', 'MiB', 'GiB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}
