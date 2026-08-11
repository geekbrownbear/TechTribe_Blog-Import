# Fill featured-image gaps by pulling the image from the post's own canonical
# page. Tech Tribe's syndication source (thetechnologypress.com) publishes each
# article with a WordPress featured image (class "wp-post-image"), sourced from
# Pexels/Pixabay under CC0, so no attribution is required.
#
# Only touches posts that currently have NO usable heroImage. Safe to re-run.
#
# Configure with environment variables (all optional):
#   BLOG_OUT      folder holding your post .md files          (./posts)
#   IMG_DIR      folder to write image files into             (./images)
#   IMG_URL_BASE  URL path your site serves IMG_DIR from       (/images)
import io, os, re, sys, glob, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf8', errors='replace')

BLOG_OUT = os.environ.get('BLOG_OUT', './posts')
IMG_DIR = os.environ.get('IMG_DIR', './images')
IMG_URL_BASE = os.environ.get('IMG_URL_BASE', '/images').rstrip('/')
os.makedirs(IMG_DIR, exist_ok=True)
UA = 'Mozilla/5.0 (compatible; TechTribeBlogImport/1.0)'


def get(url, binary=False):
    """Fetch via curl. Some machines' Python CA bundle rejects perfectly valid
    certs (the page verifies fine in curl and the browser), so shelling out
    avoids a false 'expired certificate' error."""
    r = subprocess.run(['curl', '-sSL', '--max-time', '40', '-A', UA, url],
                       capture_output=True)
    if r.returncode != 0 or not r.stdout:
        raise RuntimeError((r.stderr or b'').decode('utf8', 'replace').strip()[:120] or 'empty response')
    return r.stdout if binary else r.stdout.decode('utf8', 'replace')


def featured_url(page_html):
    """WordPress marks the featured image with class 'wp-post-image'."""
    m = re.search(r'<img[^>]*class="[^"]*wp-post-image[^"]*"[^>]*>', page_html)
    if not m:
        m = re.search(r'<meta property="og:image" content="([^"]+)"', page_html)
        return m.group(1) if m else None
    tag = m.group(0)
    src = re.search(r'\ssrc="([^"]+)"', tag)
    return src.group(1) if src else None


def usable(rel_path):
    """A heroImage counts only if the file exists AND has real bytes. Guards
    against a half-finished earlier run leaving 0-byte placeholders."""
    if not rel_path:
        return False
    name = os.path.basename(rel_path)
    f = os.path.join(IMG_DIR, name)
    return os.path.exists(f) and os.path.getsize(f) > 1024


targets = []
for p in sorted(glob.glob(f'{BLOG_OUT}/*.md')):
    s = io.open(p, encoding='utf8').read()
    hero = re.search(r'^heroImage: "([^"]+)"', s, re.M)
    if hero and usable(hero.group(1)):
        continue
    c = re.search(r'^canonical: "([^"]+)"', s, re.M)
    if not c:
        continue
    targets.append((p, c.group(1)))

print(f'posts missing a featured image, with a canonical to try: {len(targets)}\n')

ok = fail = 0
for path, canonical in targets:
    slug = os.path.basename(path)[:-3]
    try:
        html = get(canonical)
    except Exception as e:
        print(f'  PAGE FAIL {slug}: {e}')
        fail += 1
        continue
    url = featured_url(html)
    if not url:
        print(f'  NO IMAGE  {slug}')
        fail += 1
        continue
    url = url.replace('&amp;', '&')          # src attributes are HTML-escaped
    ext = os.path.splitext(url.split('?')[0])[1].lower() or '.jpg'
    if ext not in ('.jpg', '.jpeg', '.png', '.webp'):
        ext = '.jpg'
    dest = os.path.join(IMG_DIR, f'{slug}{ext}')
    try:
        # Download FIRST, validate, then write. Opening the file before the
        # fetch is what left 0-byte placeholders when a download failed.
        data = get(url, binary=True)
        if len(data) < 1024:
            raise RuntimeError(f'suspiciously small ({len(data)} bytes)')
        with io.open(dest, 'wb') as f:
            f.write(data)
    except Exception as e:
        if os.path.exists(dest) and os.path.getsize(dest) < 1024:
            os.remove(dest)
        print(f'  DOWNLOAD FAIL {slug}: {e}')
        fail += 1
        continue

    hero_url = f'{IMG_URL_BASE}/{slug}{ext}'
    s = io.open(path, encoding='utf8').read()
    if re.search(r'^heroImage:', s, re.M):
        s = re.sub(r'^heroImage: .*$', f'heroImage: "{hero_url}"', s, count=1, flags=re.M)
    else:
        s = re.sub(r'^(canonical: .*)$',
                   lambda m: f'heroImage: "{hero_url}"\n' + m.group(1),
                   s, count=1, flags=re.M)
    io.open(path, 'w', encoding='utf8', newline='\n').write(s)
    print(f'  ok  {slug}  <- {url.split("/")[-1][:60]}')
    ok += 1

print(f'\nfetched: {ok}   failed/none: {fail}')
