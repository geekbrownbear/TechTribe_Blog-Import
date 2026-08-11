/**
 * Downscale + recompress the featured images.
 *
 * The syndicate ships originals up to 5616x3744 / ~4MB, which would be a real
 * page-weight problem if served as-is. Cap the long edge at 1600px and
 * re-encode; skip anything already small enough. Idempotent: re-running does
 * nothing. Requires `sharp` (npm i sharp).
 *
 * Set IMG_DIR to the folder your images were written to (default ./images).
 */
import sharp from 'sharp';
import fs from 'node:fs';
import path from 'node:path';

const DIR = process.env.IMG_DIR || './images';
const MAX_W = 1600;
const MAX_KB = 260;

if (!fs.existsSync(DIR)) {
  console.log(`no image directory at ${DIR}; nothing to do`);
  process.exit(0);
}

let touched = 0;
let savedKb = 0;
const before = [];

for (const name of fs.readdirSync(DIR)) {
  const p = path.join(DIR, name);
  const ext = path.extname(name).toLowerCase();
  if (!['.jpg', '.jpeg', '.png', '.webp'].includes(ext)) continue;

  const bytes = fs.statSync(p).size;
  if (bytes < 1024) {
    // 0-byte / truncated leftovers from a failed download: remove so the
    // fetcher retries them instead of silently shipping a broken image.
    fs.unlinkSync(p);
    console.log(`  removed empty file: ${name}`);
    continue;
  }
  const kb = Math.round(bytes / 1024);
  let meta;
  try {
    meta = await sharp(p).metadata();
  } catch {
    console.log(`  SKIP (not a readable image): ${name}`);
    continue;
  }
  if (meta.width <= MAX_W && kb <= MAX_KB) continue;

  before.push({ name, w: meta.width, h: meta.height, kb });

  const pipeline = sharp(p).resize({ width: Math.min(meta.width, MAX_W), withoutEnlargement: true });
  const out =
    ext === '.png'
      ? await pipeline.png({ quality: 82, compressionLevel: 9 }).toBuffer()
      : await pipeline.jpeg({ quality: 82, mozjpeg: true }).toBuffer();

  // only write if we actually improved things
  if (out.length < fs.statSync(p).size) {
    fs.writeFileSync(p, out);
    const after = Math.round(out.length / 1024);
    savedKb += kb - after;
    touched++;
    console.log(`  ${name.slice(0, 52).padEnd(52)} ${meta.width}x${meta.height} ${kb}KB -> ${Math.min(meta.width, MAX_W)}px ${after}KB`);
  }
}

const total = fs
  .readdirSync(DIR)
  .filter((n) => /\.(jpe?g|png|webp)$/i.test(n))
  .reduce((s, n) => s + fs.statSync(path.join(DIR, n)).size, 0);

console.log(`\noptimized: ${touched} images, saved ${(savedKb / 1024).toFixed(1)} MB`);
console.log(`image total now: ${(total / 1024 / 1024).toFixed(1)} MB`);
