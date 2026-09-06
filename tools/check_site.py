#!/usr/bin/env python3
"""Validate the static site's local URLs, fragment links, IDs and media files."""
import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

class Page(HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.path, self.ids, self.refs, self.duplicates = path, set(), [], []
        self.h1 = 0
        self.feed(path.read_text())
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        identifier = attrs.get('id')
        if identifier:
            if identifier in self.ids: self.duplicates.append(identifier)
            self.ids.add(identifier)
        if tag == 'h1': self.h1 += 1
        for key in ('src', 'href', 'poster', 'data-alt-src'):
            if attrs.get(key): self.refs.append(attrs[key])
        if attrs.get('style'):
            self.refs.extend(re.findall(r'url\([\'\"]?([^\)\'\"]+)', attrs['style']))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    paths = [root / 'index.html', *[root / 'pages' / name for name in (
        'posts.html', 'high-redshift-black-holes-agns.html',
        'high-redshift-galaxies-star-formation.html', 'artificial-intelligence-astronomy.html')]]
    pages = {p.resolve(): Page(p) for p in paths}
    issues, checked = [], 0
    def check(path, reference):
        nonlocal checked
        url = urlsplit(reference)
        if url.scheme or url.netloc: return
        local = unquote(url.path)
        target = (root / local.lstrip('/') if local.startswith('/') else path.parent / local).resolve() if local else path.resolve()
        checked += 1
        if not target.exists(): issues.append(f'{path.relative_to(root)}: missing {reference}')
        elif url.fragment and target in pages and unquote(url.fragment) not in pages[target].ids:
            issues.append(f'{path.relative_to(root)}: missing anchor {reference}')
        elif target.suffix == '.mp4' and target.stat().st_size < 1024:
            issues.append(f'{path.relative_to(root)}: invalid video {reference}')
    for path, page in pages.items():
        if page.h1 != 1: issues.append(f'{path.relative_to(root)}: expected one h1, found {page.h1}')
        issues.extend(f'{path.relative_to(root)}: duplicate ID {x}' for x in page.duplicates)
        for reference in page.refs: check(path, reference)
    for css in (root / 'assets/css').glob('*.css'):
        for reference in re.findall(r'url\([\'\"]?([^\)\'\"]+)', css.read_text()): check(css, reference)
    for issue in issues: print('ERROR', issue)
    print(f'{len(pages)} pages, {checked} local references, {len(issues)} errors')
    return bool(issues)

if __name__ == '__main__': sys.exit(main())
