# Assign categories to posts that have none, using a fixed vocabulary so
# category pages stay consistent. Title matches are weighted heavier than body.
#
# Only touches posts with no real categories; posts that already have them keep
# them. "Uncategorized" (a common default bucket) counts as "none" here, so a
# post sitting in that junk bucket gets a real category instead.
#
# Set BLOG_OUT to your posts folder (default ./posts). Edit VOCAB below to your
# own category names and keywords.
import io, os, re, sys, glob, json, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf8', errors='replace')

BLOG_OUT = os.environ.get('BLOG_OUT', './posts')

# name -> keywords. Multi-word phrases are matched as substrings; single words
# on word boundaries so 'ai' does not match 'said'.
VOCAB = {
    'Cybersecurity': ['security', 'cyber', 'phishing', 'ransomware', 'malware', 'hacker',
                      'breach', 'password', 'passkey', 'mfa', 'multi-factor', 'authentication',
                      'threat', 'attack', 'scam', 'encryption', 'firewall', 'vulnerability',
                      'zero trust', 'spoofing', 'captcha', 'fraud', 'antivirus', 'dark web',
                      'compromise', 'exploit'],
    'Microsoft': ['microsoft', 'windows', 'office 365', 'microsoft 365', 'outlook', 'teams',
                  'copilot', 'onedrive', 'sharepoint', 'excel', 'powerpoint', 'edge', 'entra'],
    'AI': ['ai', 'artificial intelligence', 'copilot', 'chatgpt', 'machine learning',
           'generative', 'chatbot', 'llm'],
    'Cloud': ['cloud', 'azure', 'aws', 'saas', 'virtual machine', 'hosted'],
    'Business Continuity': ['backup', 'disaster', 'recovery', 'continuity', 'downtime',
                            'outage', 'immutable', 'restore'],
    'IT Management': ['patch', 'update management', 'device', 'hardware', 'infrastructure',
                      'network', 'monitoring', 'helpdesk', 'help desk', 'vendor', 'asset',
                      'onboarding', 'offboarding', 'it team', 'managed service', 'server',
                      'wi-fi', 'wifi', 'router', 'lifecycle'],
    'Productivity': ['productivity', 'efficiency', 'automate', 'automation', 'workflow',
                     'shortcut', 'time-saving', 'save time', 'focus', 'collaborate'],
    'Working From Home': ['remote work', 'work from home', 'working from home', 'hybrid work',
                          'home office', 'remote team'],
    'Online Presence': ['website', 'seo', 'social media', 'browser', 'domain', 'online presence',
                        'search engine'],
    'Business': ['budget', 'cost', 'roi', 'growth', 'strategy', 'insurance', 'compliance',
                 'regulation', 'contract', 'invoice', 'customer'],
    'New Technology': ['new feature', 'launch', 'rolling out', 'released', 'preview',
                       'coming soon', 'innovation', 'next generation'],
}

FALLBACK = 'Tech Update'

# A common default bucket. Never a real category, and never written back.
PLACEHOLDER = re.compile(r'^categories:\s*\["Uncategorized"\]\s*$', re.M)


def score(text_title, text_body):
    out = collections.Counter()
    for cat, kws in VOCAB.items():
        for kw in kws:
            if ' ' in kw or '-' in kw:
                t = text_title.count(kw)
                b = text_body.count(kw)
            else:
                t = len(re.findall(rf'\b{re.escape(kw)}\b', text_title))
                b = len(re.findall(rf'\b{re.escape(kw)}\b', text_body))
            out[cat] += t * 5 + b          # title carries 5x weight
    return out


assigned = collections.Counter()
touched = 0
for path in sorted(glob.glob(f'{BLOG_OUT}/*.md')):
    src = io.open(path, encoding='utf8').read()
    head, sep, body = src.partition('\n---\n')
    if not sep:
        continue
    placeholder = bool(PLACEHOLDER.search(head))
    if re.search(r'^categories:', head, re.M) and not placeholder:
        continue                            # already categorised

    title = re.search(r'^title: "(.*)"$', head, re.M)
    title = title.group(1).lower() if title else ''
    s = score(title, body.lower())

    picks = [c for c, n in s.most_common() if n >= 3][:2]
    if not picks:
        picks = [FALLBACK]

    line = 'categories: ' + json.dumps(picks, ensure_ascii=False)
    if placeholder:
        head = PLACEHOLDER.sub(line, head)
    else:
        head = head.rstrip('\n') + '\n' + line
    io.open(path, 'w', encoding='utf8', newline='\n').write(head + sep + body)
    for p in picks:
        assigned[p] += 1
    touched += 1

print(f'posts categorised: {touched}\n')
for cat, n in assigned.most_common():
    print(f'  {cat:22} {n}')
