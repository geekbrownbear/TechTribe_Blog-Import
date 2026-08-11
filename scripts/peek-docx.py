# Dump readable text from a .docx (paragraph-per-line) plus any hyperlink
# targets, so you can inspect a Tech Tribe blog file and find its canonical URL.
#
# Usage: python3 scripts/peek-docx.py "path/to/blog post.docx"
import sys, re, zipfile, io

# Some consoles are cp1252; force UTF-8 so emoji/smart quotes don't crash.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf8', errors='replace')

path = sys.argv[1]
with zipfile.ZipFile(path) as z:
    xml = z.read('word/document.xml').decode('utf8')
    rels = ''
    try:
        rels = z.read('word/_rels/document.xml.rels').decode('utf8')
    except KeyError:
        pass
    media = [n for n in z.namelist() if n.startswith('word/media/')]

text = re.sub(r'</w:p>', '\n', xml)
text = re.sub(r'<[^>]+>', '', text)
for a, b in [('&amp;', '&'), ('&#8217;', "'"), ('&quot;', '"'), ('&#8216;', "'"),
             ('&#8220;', '"'), ('&#8221;', '"'), ('&lt;', '<'), ('&gt;', '>')]:
    text = text.replace(a, b)

lines = [l.strip() for l in text.split('\n') if l.strip()]
print(f'--- {path} ---')
print(f'[paragraphs: {len(lines)}]  [embedded media: {len(media)}]')
for m in media:
    print('  media:', m)
print()
for i, l in enumerate(lines):
    print(f'{i:3} | {l}')
print()
print('--- external link targets ---')
for t in sorted(set(re.findall(r'Target="(https?://[^"]+)"', rels))):
    print('  ', t)
