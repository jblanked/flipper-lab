#!/usr/bin/env node
/**
 * Generates frontend/src/lib/flipper/protobufCompiled.js from Flipper's
 * .proto definitions. Run automatically via `npm run gen:protobuf` (and on postinstall)
 * clones/updates the proto repo into a cache dir, compiles, and only rewrites the output if it changed.
 */
import { execSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync, rmSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..');                     // frontend/
const CACHE = join(ROOT, '.protobuf-cache');            // gitignored working dir
const PROTO_DIR = join(CACHE, 'flipperzero-protobuf');
const OUT = join(ROOT, 'src', 'lib', 'flipper', 'protobufCompiled.js');
const REPO = 'https://github.com/flipperdevices/flipperzero-protobuf.git';

const PROTOS = [
  'flipper.proto', 'storage.proto', 'system.proto', 'application.proto',
  'gui.proto', 'gpio.proto', 'property.proto', 'desktop.proto'
];

function run(cmd, cwd) {
  execSync(cmd, { cwd, stdio: 'inherit' });
}

function main() {
  mkdirSync(CACHE, { recursive: true });

  // clone or update the proto repo
  if (existsSync(PROTO_DIR)) {
    try { run('git pull --ff-only', PROTO_DIR); }
    catch { rmSync(PROTO_DIR, { recursive: true, force: true }); }
  }
  if (!existsSync(PROTO_DIR)) {
    run(`git clone --depth 1 ${REPO} flipperzero-protobuf`, CACHE);
  }

  // compile via locally-installed pbjs (protobufjs-cli must be a devDependency)
  const pbjs = join(ROOT, 'node_modules', '.bin', 'pbjs');
  const tmpOut = join(CACHE, 'protobufCompiled.js');
  const files = PROTOS.map(f => join(PROTO_DIR, f)).join(' ');
  run(`"${pbjs}" -t static-module -w es6 -o "${tmpOut}" ${files}`, ROOT);

  // only rewrite if changed (keeps git diffs clean, skips needless writes)
  const next = readFileSync(tmpOut, 'utf8');
  const prev = existsSync(OUT) ? readFileSync(OUT, 'utf8') : '';
  if (next !== prev) {
    mkdirSync(dirname(OUT), { recursive: true });
    writeFileSync(OUT, next);
    console.log('✓ protobufCompiled.js updated');
  } else {
    console.log('✓ protobufCompiled.js already up to date');
  }
}

main();

