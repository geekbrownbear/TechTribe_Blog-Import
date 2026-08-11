# Index EVERY Tech Tribe blog docx (current packs + Archive) and pair each with
# its featured image. Keyed by canonical URL, which is the one field that
# reliably links a source doc to a post already on the site.
#
# Output: ./manifest.json (override with TECHTRIBE_MANIFEST)
#
# Configure with environment variables (all optional):
#   TECHTRIBE_PACKS    folder that holds the TTT_Tribal-Marketing-Pack-YYYY-MM
#                      pack folders (and an optional Archive/ subfolder).
#                      Default: ./packs
#   TECHTRIBE_MANIFEST where to write the index.  Default: ./manifest.json
#   BLOG_OUT           your site's Markdown posts folder, used only to report
#                      which source posts you already have.  Default: ./posts
import io, os, sys, re, json, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from syndicate_lib import parse_tech_tribe

TT_ROOT = os.environ.get('TECHTRIBE_PACKS', './packs')
MANIFEST = os.environ.get('TECHTRIBE_MANIFEST', './manifest.json')
BLOG_OUT = os.environ.get('BLOG_OUT', './posts')

entries = []


def tt_packs():
    for p in sorted(glob.glob(f'{TT_ROOT}/TTT_Tribal-Marketing-Pack-*')):
        yield p
    for p in sorted(glob.glob(f'{TT_ROOT}/Archive/TTT_Tribal-Marketing-Pack-*')):
        yield p


for pack in tt_packs():
    month = re.search(r'(\d{4})-(\d{2})$', pack)
    if not month:
        continue
    ym = f'{month.group(1)}-{month.group(2)}'
    # Folder numbering drifts between months ("6. Blog Posts" vs "5. Blog
    # Posts"), so glob on the name SUFFIX, not the number.
    blog_dirs = [d for d in glob.glob(f'{pack}/*') if os.path.isdir(d) and re.search(r'Blog Posts$', d)]
    img_dirs = [d for d in glob.glob(f'{pack}/*') if os.path.isdir(d) and 'Social Media Post Image' in d]
    img_dir = img_dirs[0] if img_dirs else None

    for docx in sorted(glob.glob(f'{blog_dirs[0]}/*.docx')) if blog_dirs else []:
        if os.path.basename(docx).startswith('~$'):     # Word lock file, not a zip
            continue
        try:
            d = parse_tech_tribe(docx)
        except Exception as e:
            print(f'  PARSE FAIL {os.path.basename(docx)}: {e}')
            continue
        if not d['canonical'] or not d['title']:
            print(f'  INCOMPLETE {os.path.basename(docx)}: title={bool(d["title"])} canonical={bool(d["canonical"])}')
            continue
        # Image, in order of preference:
        #  1. sibling file with the same basename as the docx
        #  2. the separate Social Media Post Images folder, "-V1"
        #  (a pack that ships neither is filled later by fetch-canonical-images)
        key = re.sub(r'^TTT_\d{4}-\d{2}-Blog-', '', os.path.basename(docx)[:-5])
        img = None
        stem = docx[:-5]
        for ext in ('.jpg', '.jpeg', '.png'):
            if os.path.exists(stem + ext):
                img = stem + ext
                break
        if not img and img_dir:
            cands = glob.glob(f'{img_dir}/*{key}-V1.png')
            if cands:
                img = cands[0]
        entries.append({
            'provider': 'tech-tribe',
            'month': ym,
            'docx': docx,
            'title': d['title'],
            'canonical': d['canonical'],
            'image': img,
            'words': len(d['body'].split()),
        })

manifest_dir = os.path.dirname(MANIFEST)
if manifest_dir:
    os.makedirs(manifest_dir, exist_ok=True)
with io.open(MANIFEST, 'w', encoding='utf8', newline='\n') as f:
    json.dump(entries, f, indent=1, ensure_ascii=False)

print(f'\nindexed: {len(entries)} posts')
print(f'with image: {sum(1 for e in entries if e["image"])}   missing image: {sum(1 for e in entries if not e["image"])}')

# coverage vs posts already on the site
existing = {}
for p in glob.glob(f'{BLOG_OUT}/*.md'):
    s = io.open(p, encoding='utf8').read()
    m = re.search(r'^canonical:\s*"([^"]+)"', s, re.M)
    if m:
        existing[m.group(1).rstrip('/')] = os.path.basename(p)[:-3]

have = {e['canonical'].rstrip('/') for e in entries}
matched = [c for c in existing if c in have]
print(f'\nexisting site posts with canonical: {len(existing)}')
print(f'  matched to a source doc (image backfill possible): {len(matched)}')
print(f'  NOT matched: {len(existing) - len(matched)}')

new = [e for e in entries if e['canonical'].rstrip('/') not in existing]
print(f'\nsource posts NOT yet on the site (import candidates): {len(new)}')
by_month = {}
for e in new:
    by_month.setdefault(e['month'], []).append(e)
for m in sorted(by_month):
    row = by_month[m]
    print(f'  {m}: {len(row):2}  (imgs {sum(1 for x in row if x["image"])})')
