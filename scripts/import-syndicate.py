# Import Tech Tribe posts into a static site as Markdown, and backfill featured
# images onto posts already present.
#
# Behaviour:
#   - Each post is dated inside its OWN pack month, spread across weekdays.
#   - Posts in the current (or a future) month import as `draft: true`, so
#     nothing is future-dated; they become a ready-to-publish queue instead.
#   - The featured image is written as the frontmatter heroImage.
#   - Existing posts get an image backfilled from the pack, matched by CANONICAL
#     URL (the only field that reliably links a source doc to a post).
#   - Idempotent: a post whose canonical already exists is skipped.
#
# Configure with environment variables (all optional):
#   TECHTRIBE_MANIFEST  the index from build-syndicate-manifest.py  (./manifest.json)
#   BLOG_OUT            folder to write post .md files into          (./posts)
#   IMG_DIR            folder to write image files into              (./images)
#   IMG_URL_BASE       URL path your site serves IMG_DIR from, used
#                      in the heroImage frontmatter                  (/images)
#
# The frontmatter fields (title, description, pubDate, heroImage, canonical,
# draft) are the common set for Astro / Eleventy / Hugo Markdown collections.
# If your generator uses different names, adjust the `fm` block below.
import io, os, re, sys, json, glob, shutil, calendar, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from syndicate_lib import parse_tech_tribe, slugify

MANIFEST = json.load(io.open(os.environ.get('TECHTRIBE_MANIFEST', './manifest.json'), encoding='utf8'))
BLOG_OUT = os.environ.get('BLOG_OUT', './posts')
IMG_DIR = os.environ.get('IMG_DIR', './images')
IMG_URL_BASE = os.environ.get('IMG_URL_BASE', '/images').rstrip('/')
os.makedirs(BLOG_OUT, exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True)

TODAY = datetime.date.today()


def jq(s):
    return json.dumps(s, ensure_ascii=False)


def existing_by_canonical():
    """Canonical -> file, for posts already in BLOG_OUT."""
    out = {}
    for p in glob.glob(f'{BLOG_OUT}/*.md'):
        s = io.open(p, encoding='utf8').read()
        m = re.search(r'^canonical:\s*"([^"]+)"', s, re.M)
        if m:
            out[m.group(1).rstrip('/')] = p
    return out


def copy_image(src, slug):
    if not src or not os.path.exists(src):
        return None
    ext = os.path.splitext(src)[1].lower()
    dest = os.path.join(IMG_DIR, f'{slug}{ext}')
    if not os.path.exists(dest):
        shutil.copyfile(src, dest)
    return f'{IMG_URL_BASE}/{slug}{ext}'


def spread_dates(n, year, month):
    """n evenly spread weekday dates inside the given month."""
    days = calendar.monthrange(year, month)[1]
    out = []
    for i in range(n):
        day = max(1, min(days, round((i + 0.5) * days / n)))
        d = datetime.date(year, month, day)
        while d.weekday() >= 5:                 # nudge weekends to Monday
            d += datetime.timedelta(days=1)
            if d.month != month:
                d = datetime.date(year, month, day) - datetime.timedelta(days=1)
                while d.weekday() >= 5:
                    d -= datetime.timedelta(days=1)
                break
        out.append(d)
    out.sort()
    return out


# ---------------------------------------------------------------- import posts
existing = existing_by_canonical()
new_entries = [e for e in MANIFEST if e['canonical'].rstrip('/') not in existing]
by_month = {}
for e in new_entries:
    by_month.setdefault(e['month'], []).append(e)

imported = drafted = 0
for ym in sorted(by_month):
    rows = sorted(by_month[ym], key=lambda r: r['docx'])
    year, month = int(ym[:4]), int(ym[5:7])
    dates = spread_dates(len(rows), year, month)
    is_future_month = (year, month) >= (TODAY.year, TODAY.month)

    for row, date in zip(rows, dates):
        d = parse_tech_tribe(row['docx'])
        title = d['title']
        slug = slugify(title)
        body = d['body'].rstrip()
        body = re.sub(r'\*\*\s*$', '', body).rstrip()      # stray trailing bold marker

        first = next((p for p in body.split('\n\n') if not p.startswith('#')), '')
        desc = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', first)
        desc = re.sub(r'\*+', '', desc)
        if len(desc) > 290:
            desc = desc[:287].rsplit(' ', 1)[0] + '...'

        hero = copy_image(row['image'], slug)

        fm = ['---', f'title: {jq(title)}', f'description: {jq(desc)}',
              f'pubDate: {jq(date.isoformat() + "T09:30:00")}']
        if hero:
            fm.append(f'heroImage: {jq(hero)}')
        fm.append(f'canonical: {jq(row["canonical"])}')
        if is_future_month:
            fm.append('draft: true')
        fm.append('---')

        io.open(f'{BLOG_OUT}/{slug}.md', 'w', encoding='utf8', newline='\n').write(
            '\n'.join(fm) + '\n\n' + body + '\n')
        if is_future_month:
            drafted += 1
        else:
            imported += 1

print(f'posts imported live : {imported}')
print(f'posts held as draft : {drafted}  (current month, ready to publish)')

# ------------------------------------------------- backfill existing post art
back = skipped = 0
for e in MANIFEST:
    path = existing.get(e['canonical'].rstrip('/'))
    if not path or not e['image']:
        continue
    s = io.open(path, encoding='utf8').read()
    if re.search(r'^heroImage:', s, re.M):
        continue
    slug = os.path.basename(path)[:-3]
    hero = copy_image(e['image'], slug)
    if not hero:
        skipped += 1
        continue
    s = re.sub(r'^(canonical: .*)$', lambda m: f'heroImage: {jq(hero)}\n' + m.group(1), s, count=1, flags=re.M)
    io.open(path, 'w', encoding='utf8', newline='\n').write(s)
    back += 1

print(f'existing posts given a featured image: {back}')
files = glob.glob(f'{BLOG_OUT}/*.md')
withhero = sum(1 for p in files
               if re.search(r'^heroImage:', io.open(p, encoding='utf8').read(), re.M))
print(f'{"posts":20} {len(files):4}   with featured image: {withhero}   without: {len(files) - withhero}')
