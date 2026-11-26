import re
import sys
from pathlib import Path

def peek_vdnh_lektorij(path):
    """Try to extract event cards from vdnh.ru/lektorij page."""
    s = Path(path).read_text(encoding='utf-8', errors='ignore')
    # Look for event links like /events/12345/ or full urls
    links = set()
    for m in re.finditer(r'href="(https?://vdnh\.ru/events/\d+/[^"]*)"', s):
        links.add(m.group(1).split('?')[0].rstrip('/'))
    for m in re.finditer(r'href="(/events/\d+/[^"]*)"', s):
        links.add('https://vdnh.ru' + m.group(1).split('?')[0].rstrip('/'))
    return sorted(links)

def peek_timepad_list(path):
    """Extract event links from Timepad list page HTML (rough)."""
    s = Path(path).read_text(encoding='utf-8', errors='ignore')
    links = set()
    for m in re.finditer(r'href="(https?://[a-z0-9-]+\.timepad\.ru/event/\d+/[^"]*)"', s, re.I):
        links.add(m.group(1).split('?')[0].rstrip('/'))
    for m in re.finditer(r'href="(/event/\d+/[^"]*)"', s):
        # relative
        base = ''
        if 'atom-lab' in path.lower():
            base = 'https://atom-lab.timepad.ru'
        elif 'muzey' in path.lower() or 'biotech' in path.lower():
            base = 'https://muzey-biotekh.timepad.ru'
        if base:
            links.add(base + m.group(1).split('?')[0].rstrip('/'))
    return sorted(links)

if __name__ == '__main__':
    # check files
    print('=== vdnh_lektorij ===')
    p = Path('data/raw/cdp/vdnh_lektorij.html')
    if p.exists():
        for u in peek_vdnh_lektorij(p)[:50]:
            print(u)
    print('\n=== vdnh_kosmos ===')
    p = Path('data/raw/cdp/vdnh_kosmos.html')
    if p.exists():
        for u in peek_vdnh_lektorij(p)[:50]:
            print(u)
    print('\n=== vdnh_slovo ===')
    p = Path('data/raw/cdp/vdnh_slovo.html')
    if p.exists():
        for u in peek_vdnh_lektorij(p)[:50]:
            print(u)
    print('\n=== vdnh_atomlab (timepad) ===')
    p = Path('data/raw/cdp/vdnh_atomlab.html')
    if p.exists():
        for u in peek_timepad_list(str(p))[:50]:
            print(u)
    print('\n=== vdnh_muzeybio (timepad) ===')
    p = Path('data/raw/cdp/vdnh_muzeybio.html')
    if p.exists():
        for u in peek_timepad_list(str(p))[:50]:
            print(u)
