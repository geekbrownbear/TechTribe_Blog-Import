# TechTribe_Blog-Import

A small toolkit that turns the monthly **Tech Tribe** marketing packs into
ready-to-publish Markdown blog posts for a static site (Astro, Eleventy, Hugo,
or anything that reads Markdown with YAML frontmatter). It reads the `.docx`
files straight from your pack folders, pairs each post with its featured image,
sets a cross-domain canonical back to the original publisher, spreads publish
dates across the pack month, and assigns categories.

It works either as a plain set of scripts or as an agent **skill** (`SKILL.md`)
you can drop into an assistant that supports them.

## What you need

- **Python 3** (standard library only)
- **curl** on your PATH (used to fetch fallback images)
- **Node.js + `sharp`** (`npm install`) for the optional image optimiser

## Quick start

```bash
# 1. Tell the scripts where your packs are and where your site wants files.
export TECHTRIBE_PACKS="/path/to/Tech Tribe/Marketing Packs"
export BLOG_OUT="./posts"        # your generator's posts folder
export IMG_DIR="./images"        # where images are written on disk
export IMG_URL_BASE="/images"    # the URL that maps to IMG_DIR

# 2. Run the pipeline.
python3 scripts/build-syndicate-manifest.py
python3 scripts/import-syndicate.py
python3 scripts/fetch-canonical-images.py
node   scripts/optimize-media.mjs
python3 scripts/assign-categories.py
```

Every step is idempotent: posts whose canonical URL already exists are skipped,
and images already present are left alone. Re-run any step safely.

See **`SKILL.md`** for the full walkthrough, configuration table, and a
verification checklist to run before publishing.

## Configuration

All paths are environment variables with sensible defaults, so you can run from
any folder. Set the ones that differ from the defaults:

| Variable | What | Default |
|---|---|---|
| `TECHTRIBE_PACKS` | folder holding the `TTT_Tribal-Marketing-Pack-*` folders | `./packs` |
| `BLOG_OUT` | where post `.md` files are written | `./posts` |
| `IMG_DIR` | where image files are written | `./images` |
| `IMG_URL_BASE` | URL path your site serves `IMG_DIR` from (used in `heroImage`) | `/images` |
| `TECHTRIBE_MANIFEST` | the generated index file | `./manifest.json` |

## Files

| File | Role |
|---|---|
| `scripts/syndicate_lib.py` | docx to Markdown: preserves links and bold, extracts title/canonical |
| `scripts/build-syndicate-manifest.py` | indexes all packs, pairs posts with images |
| `scripts/import-syndicate.py` | writes post Markdown, copies images, backfills existing posts |
| `scripts/fetch-canonical-images.py` | fills image gaps from the canonical page (CC0) |
| `scripts/optimize-media.mjs` | downscales/recompresses featured images |
| `scripts/assign-categories.py` | keyword categorisation from an editable vocabulary |
| `scripts/peek-docx.py` | debug helper: dumps a docx as numbered paragraphs + links |

## Canonicals and credit

Tech Tribe content is syndicated to many businesses. These scripts set each
post's `canonical` to the original publisher (`thetechnologypress.com`), which
tells search engines to credit the source rather than treat every copy as
competing content. If you rewrite a post into genuinely original writing, delete
its `canonical:` line so it earns its own ranking.

## License / use

Shared with the Tech Tribe community. Use and adapt freely for your own site.
