# Shared docx -> markdown conversion for the Tech Tribe blog packs.
#   Tech Tribe -> canonical at thetechnologypress.com, <H2>/<H3> markers in body
# Preserves inline hyperlinks and bold, which a naive tag-strip would lose.
import re
import zipfile
import xml.etree.ElementTree as ET

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'

DASHES = {'—': '-', '–': '-', '―': '-', ' ': ' '}


def clean(s: str) -> str:
    for a, b in DASHES.items():
        s = s.replace(a, b)
    return re.sub(r'[ \t]+', ' ', s).strip()


def load(path):
    """Return (paragraphs, rels, media) where each paragraph is markdown-ish text."""
    with zipfile.ZipFile(path) as z:
        doc = z.read('word/document.xml')
        try:
            rels_xml = z.read('word/_rels/document.xml.rels').decode('utf8')
        except KeyError:
            rels_xml = ''
        media = {n: z.read(n) for n in z.namelist() if n.startswith('word/media/')}

    rels = dict(re.findall(r'Id="([^"]+)"[^>]*Target="([^"]+)"', rels_xml))
    root = ET.fromstring(doc)
    paras = []

    for p in root.iter(f'{W}p'):
        # Collect (text, bold, link) segments first, then MERGE adjacent
        # segments with identical formatting. Word splits a bold phrase across
        # several runs; emitting markers per-run produces '**a****b**' and
        # stray '** **', so merging before emitting is what keeps it clean.
        segs = []

        def add_run(run, link=None):
            txt = ''.join(t.text or '' for t in run.iter(f'{W}t'))
            if not txt:
                return
            rpr = run.find(f'{W}rPr')
            bold = rpr is not None and rpr.find(f'{W}b') is not None
            segs.append([txt, bold, link])

        for child in p:
            if child.tag == f'{W}hyperlink':
                target = rels.get(child.get(f'{R}id', ''), '').replace('&amp;', '&')
                for run in child.iter(f'{W}r'):
                    add_run(run, target if target.startswith('http') else None)
            elif child.tag == f'{W}r':
                add_run(child)

        merged = []
        for txt, bold, link in segs:
            if merged and merged[-1][1] == bold and merged[-1][2] == link:
                merged[-1][0] += txt
            else:
                merged.append([txt, bold, link])

        parts = []
        for txt, bold, link in merged:
            if not txt.strip():
                parts.append(txt)  # whitespace never carries markers
            elif link:
                parts.append(f'[{txt.strip()}]({link}) ' if txt.endswith(' ') else f'[{txt.strip()}]({link})')
            elif bold:
                parts.append(f'**{txt.strip()}**' + (' ' if txt.endswith(' ') else ''))
            else:
                parts.append(txt)

        text = clean(''.join(parts))
        text = re.sub(r'(?<=[a-z])([?!.])(?=[A-Z])', r'\1 ', text)  # 'together?Microsoft'
        if text:
            paras.append(text)

    return paras, rels, media


def plain(s: str) -> str:
    """Strip markdown emphasis/link syntax; titles must be plain text."""
    s = re.sub(r'\[([^\]]+)\]\([^)]*\)', lambda mm: mm.group(1), s)
    return re.sub(r'\*+', '', s).strip()


def slugify(s: str) -> str:
    s = re.sub('[‘’ʼ\']', '', s.lower())
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-')


def body_to_markdown(lines):
    """Convert body paragraphs to markdown, honouring <H2>/<H3> markers."""
    out = []
    for l in lines:
        m = re.match(r'^<H([23])>(.*?)</H\1>$', l, re.I)
        if m:
            out.append(('##' if m.group(1) == '2' else '###') + ' ' + clean(m.group(2)))
        else:
            out.append(l)
    return '\n\n'.join(out)


def parse_tech_tribe(path):
    paras, rels, media = load(path)

    title = None
    canonical = None
    for i, l in enumerate(paras):
        if title is None and re.match(r'^THE SUGGESTED blog title$', l, re.I) and i + 1 < len(paras):
            title = plain(paras[i + 1])
        if canonical is None:
            # stop at markdown punctuation: the URL sits inside a [text](url)
            m = re.search(r'https://thetechnologypress\.com/[a-z0-9\-/]+', l, re.I)
            if m:
                canonical = m.group(0).rstrip('/') + '/'

    start = end = None
    for i, l in enumerate(paras):
        if start is None and 'update the H2 & H3 heading tags' in l:
            start = i + 1
        if start is not None and 'used with permission from The Technology Press' in l.lower() \
           or (start is not None and 'Article used with permission' in l):
            end = i
            break
    body = paras[start:end] if start is not None and end is not None else []
    # drop stray artefacts (Word text-box numeric noise)
    body = [b for b in body if not re.match(r'^[\d\-]{6,}$', b)]

    return {
        'title': title,
        'canonical': canonical,
        'body': body_to_markdown(body),
        'media': media,
        'provider': 'The Technology Press',
    }
