---
name: blog-import
description: Import the monthly Tech Tribe marketing packs into a static site as Markdown posts with featured images, cross-domain canonicals, categories, and correct publish dates. Use when a new Tech Tribe pack lands, when asked to add blog posts / import blog content / publish the monthly content, or when the blog needs fresh posts.
---

# Monthly Tech Tribe blog import

Turns the Tech Tribe marketing packs into published Markdown posts. A normal
month is ~6 posts and takes one command run plus a review.

## Source layout

Point `TECHTRIBE_PACKS` at the folder that holds your downloaded packs. Each
month is a `TTT_Tribal-Marketing-Pack-YYYY-MM` folder, and older months can sit
in an `Archive/` subfolder:

```
<TECHTRIBE_PACKS>/
  TTT_Tribal-Marketing-Pack-2026-08/
    6. Blog Posts/*.docx            (6 per month)
    Social Media Post Images/*-V1.png   (1200x628)
  Archive/
    TTT_Tribal-Marketing-Pack-2026-01/ ...
```

**Folder numbering and image layout drift between months.** Blog posts have
appeared as both `6. Blog Posts` and `5. Blog Posts`, so the scripts glob on the
folder *name suffix*, not the number. Images have appeared three ways, and the
manifest builder tries them in order:

1. a sibling file with the same basename as the docx
2. the separate `Social Media Post Images` folder, `-V1`
3. nothing in the pack at all - see the canonical fallback below

**Canonical fallback.** When a pack ships no image, `fetch-canonical-images.py`
pulls the featured image straight from the post's own canonical page (Tech
Tribe's source site marks it `class="wp-post-image"`). Those images are
Pexels/Pixabay CC0, so no attribution is required. It only touches posts whose
`heroImage` is missing or points at a file under 1KB, so it is safe to re-run.

## Configure

All paths are environment variables with sensible defaults, so you can run from
any folder. Set the ones that differ from the defaults:

| Variable | What | Default |
|---|---|---|
| `TECHTRIBE_PACKS` | folder holding the pack folders | `./packs` |
| `BLOG_OUT` | where post `.md` files are written | `./posts` |
| `IMG_DIR` | where image files are written | `./images` |
| `IMG_URL_BASE` | URL path your site serves `IMG_DIR` from (goes in `heroImage`) | `/images` |
| `TECHTRIBE_MANIFEST` | the generated index file | `./manifest.json` |

Example (bash):

```bash
export TECHTRIBE_PACKS="/path/to/Tech Tribe/Marketing Packs"
export BLOG_OUT="src/content/blog"     # your generator's posts folder
export IMG_DIR="public/images/blog"    # where those images live on disk
export IMG_URL_BASE="/images/blog"     # the URL that maps to IMG_DIR
```

## Run it

```bash
# 1. Index every pack and pair each post with its image (writes the manifest).
#    Safe to re-run any time.
python3 scripts/build-syndicate-manifest.py

# 2. Import anything not already on the site + backfill missing images.
#    Idempotent: skips posts whose canonical already exists.
python3 scripts/import-syndicate.py

# 3. Fill any image gaps from the canonical pages (CC0). No-op if the pack
#    supplied images for everything. Needs `curl` on PATH.
python3 scripts/fetch-canonical-images.py

# 4. Downscale/recompress. The packs ship originals up to 5616x3744 and ~4MB;
#    served as static files, this matters. Needs `npm i sharp`.
node scripts/optimize-media.mjs

# 5. Categorise the new posts from the vocabulary in the script.
#    Only touches posts that have no categories yet.
python3 scripts/assign-categories.py
```

Then run the **verification checklist** below before publishing.

## How each piece works

**Canonical URLs are the primary key.** Every Tech Tribe docx states the source
URL it wants credited (`thetechnologypress.com/...`), and that is what links a
source file to a post already on the site. Matching on titles or filenames is
unreliable; matching on canonical is exact.

**Why cross-domain canonicals matter.** This content is syndicated to many
businesses. Pointing the `canonical` at the original publisher tells Google to
credit them, so the copies do not compete with your own original pages while
remaining readable for humans. Keep the `canonical:` line unless you rewrite a
post into genuinely original content, in which case delete the line so the post
self-canonicals and earns its own ranking.

**Dates: each post publishes inside its own pack month**, spread across
weekdays. Posts in the *current* month import as `draft: true` so nothing is
future-dated; flip the flag (or delete the line) as the month progresses.

**Images** are used as the card thumbnail, the `og:image`, and the article hero.
Prefer the standalone image folder over the docx-embedded copies: Word
compresses embedded images. 1200x628 is the Open Graph spec.

## Frontmatter

Each post is written with this YAML frontmatter (the common set for Astro,
Eleventy, and Hugo Markdown collections):

```yaml
---
title: "..."
description: "..."
pubDate: "2026-08-12T09:30:00"
heroImage: "/images/blog/the-slug.jpg"
canonical: "https://thetechnologypress.com/the-slug/"
draft: true            # only for the current/future month
categories: ["Cybersecurity", "Microsoft"]   # added by step 5
---
```

If your generator expects different field names, adjust the `fm` block in
`import-syndicate.py` and the category line in `assign-categories.py`.

## Verification checklist

Run after every import. Each of these has caught a real bug. Replace `./posts`
with your `BLOG_OUT` if you changed it.

```bash
# Titles must match their canonical slug. A mismatch means the parser grabbed
# an excerpt fragment instead of the title.
python3 - <<'EOF'
import io, sys, glob, re, os
sys.path.insert(0, 'scripts')
from syndicate_lib import slugify
bad = []
for p in glob.glob('./posts/*.md'):
    s = io.open(p, encoding='utf8').read()
    t = re.search(r'^title: "(.*)"$', s, re.M)
    c = re.search(r'^canonical: "([^"]+)"', s, re.M)
    if not (t and c):
        continue
    if slugify(t.group(1)) != c.group(1).rstrip('/').split('/')[-1]:
        bad.append(os.path.basename(p))
print('title mismatches:', len(bad), bad)
EOF

# No HTML entities left in frontmatter
grep -l '&#' ./posts/*.md || echo "entities: clean"

# Every heroImage must point at a file that exists and has real bytes.
python3 -c "
import glob, io, re, os
D=os.environ.get('IMG_DIR','./images')
bad = []
for p in glob.glob('./posts/*.md'):
    m = re.search(r'^heroImage: \"([^\"]+)\"', io.open(p, encoding='utf8').read(), re.M)
    if not m: continue
    f = os.path.join(D, os.path.basename(m.group(1)))
    if not os.path.exists(f) or os.path.getsize(f) < 1024: bad.append(m.group(1))
print('broken hero images:', len(bad), bad[:5])"

# Bold markers must pair. The pack sometimes leaves a run unterminated, which
# renders a literal ** in the published article.
python3 -c "
import io, glob, os
bad = [os.path.basename(p) for p in glob.glob('./posts/*.md')
       if io.open(p, encoding='utf8').read().partition(chr(10)+'---'+chr(10))[2].count('**') % 2]
print('posts with unbalanced bold:', len(bad), bad[:5])"
```

## Gotchas

- **Word lock files** (`~$*.docx`) appear when a doc is open; they are not zips
  and are skipped automatically.
- **`curl` and `sharp` are external dependencies.** `fetch-canonical-images.py`
  shells out to `curl` (some Python installs' CA bundle rejects valid certs that
  curl accepts, so do not "fix" it back to `urllib`). `optimize-media.mjs` needs
  `npm i sharp`.
- **Image `src` attributes are HTML-escaped.** `&amp;` in a URL is decoded
  before fetching; the fetcher already handles this.
- **Do not re-run the importer over a post you have edited.** It skips existing
  canonicals, so this is only a risk if you delete the file first.

## A note on house style

The docx-to-Markdown converter normalises em and en dashes to hyphens on import.
If your publication has its own editorial rules (banned words, no client names,
etc.), apply them in review - they are not enforced by these scripts.
