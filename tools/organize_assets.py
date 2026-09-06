#!/usr/bin/env python3
"""One-time, non-destructive asset migration for the September 2026 redesign.

Makes compressed delivery images; original media is retained under archive/.
Run without --apply to inspect the plan before changing files.
"""
import argparse
import html
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PAGES = [ROOT / 'index.html', *[ROOT / 'pages' / name for name in (
    'high-redshift-black-holes-agns.html', 'high-redshift-galaxies-star-formation.html',
    'artificial-intelligence-astronomy.html', 'posts.html')]]
RESEARCH = {'bg01.jpeg', 'JWST.png', 'LRD.png', 'SHAPE1.png', 'SFE.png', 'clumps.png',
            'bias_cover.png', 'BHE_cover.png', 'bh-star-evolution-continuous-envelope-poster-v8.png', 'Zoom_frame_80.jpg'}
JOURNAL = {'Godard.jpg', 'Bergman_reviews.png', 'Bergman.jpeg', 'solaris.jpeg',
           'frankocean.png', 'sza.jpeg', 'loveletter.jpg', 'nanjing0.jpeg', 'button.png'}

def slug(name):
    return re.sub(r'[^a-z0-9.-]+', '-', name.lower()).strip('-')

def delivery_path(source):
    if source.name == 'ppl.png':
        return ROOT / 'assets/images/portrait/zihao-wang.png'
    if source.suffix.lower() == '.mp4':
        names = {'Zoom_m_9_7_first80s.mp4': 'thesan-zoom-80s.mp4',
                 'bh-star-to-normal-agn-45s-continuous-envelope-no-seam-60fps-v8.mp4': 'bh-star-to-agn-45s.mp4'}
        return ROOT / 'assets/videos' / names.get(source.name, slug(source.name))
    group = 'research' if source.name in RESEARCH else 'journal' if source.name in JOURNAL else 'portrait' if source.name.startswith('ppl') else 'collage'
    return ROOT / 'assets/images' / group / (slug(source.stem) + '.webp')

def compress_image(source, target, limit):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists(): return
    sizes = subprocess.check_output(['sips', '-g', 'pixelWidth', '-g', 'pixelHeight', str(source)], text=True)
    width, height = [int(re.search(key + r': (\d+)', sizes).group(1)) for key in ('pixelWidth', 'pixelHeight')]
    scale = min(1, limit / max(width, height))
    subprocess.run(['cwebp', '-quiet', '-q', '88', '-alpha_q', '100', '-m', '6',
                    '-resize', str(max(1, round(width * scale))), str(max(1, round(height * scale))),
                    str(source), '-o', str(target)], check=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    sources = ROOT / 'source materials'
    if not sources.is_dir():
        print('No legacy source materials directory. The asset migration has already been applied.')
        return
    active = PAGES + list((ROOT / 'assets/css').glob('*.css')) + list((ROOT / 'assets/js').glob('*.js'))
    texts = {path: path.read_text() for path in active}
    mapping = {}
    for source in sources.iterdir():
        if source.suffix.lower() not in {'.png', '.jpg', '.jpeg', '.mp4', '.gif'}: continue
        patterns = ['source materials/' + source.name, 'source%20materials/' + source.name]
        if any(pattern in text for text in texts.values() for pattern in patterns):
            mapping[source] = delivery_path(source)
    print('Active media:', len(mapping))
    for source, target in mapping.items(): print(source.relative_to(ROOT), '->', target.relative_to(ROOT))
    if not args.apply: return
    for source, target in mapping.items():
        if source.suffix.lower() == '.mp4' or source.name == 'ppl.png':
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        else:
            compress_image(source, target, 1600 if source.name in RESEARCH else 1400)

    for path, text in texts.items():
        for source, target in mapping.items():
            new_relative = Path(os.path.relpath(target, path.parent)).as_posix()
            new_root = target.relative_to(ROOT).as_posix()
            # Absolute social/structured-data URLs must retain the public origin.
            for old_root in ('source materials/', 'source%20materials/'):
                text = text.replace('https://zihaowang-kiaa.github.io/personal-homepage/' + old_root + source.name,
                                    'https://zihaowang-kiaa.github.io/personal-homepage/' + new_root)
                for prefix in ('../../', '../', ''):
                    text = text.replace(prefix + old_root + source.name, new_relative)
        text = text.replace('href="Zihao_2026.pdf"', 'href="docs/cv/Zihao_2026.pdf"')
        path.write_text(text)

    # Grid/cover derivatives retain original download links and viewer sources.
    posts = ROOT / 'pages/posts.html'
    text = posts.read_text()
    thumbnail_map = {}
    def thumbnail(match):
        source_value = match.group(2)
        source = (posts.parent / html.unescape(source_value)).resolve()
        if not source.is_file(): return match.group(0)
        album_relative = source.relative_to(ROOT / 'albums')
        target = ROOT / 'assets/images/albums' / album_relative.parent / (slug(source.stem) + '.webp')
        compress_image(source, target, 1200)
        new_relative = Path(os.path.relpath(target, posts.parent)).as_posix()
        thumbnail_map[source.relative_to(ROOT).as_posix()] = target.relative_to(ROOT).as_posix()
        return match.group(1) + html.escape(new_relative, quote=True) + match.group(3)
    text = re.sub(r'(<img\b[^>]*\bsrc=")(\.\./albums/[^\"]+)(")', thumbnail, text)
    posts.write_text(text)
    cv = ROOT / 'docs/cv/Zihao_2026.pdf'
    cv.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / 'Zihao_2026.pdf', cv)
    # Keep root CV as a compatibility URL for previously shared links.
    archive = ROOT / 'archive'
    archive.mkdir(exist_ok=True)
    for name in ('home.md', 'posts.md', 'project1.md', 'project2.md', 'project3.md'):
        origin = ROOT / name
        target = ROOT / 'content' / name
        if origin.exists(): shutil.move(str(origin), str(target))
    for origin, target in (
        (sources, archive / 'original-assets'),
        (ROOT / 'tmp', archive / 'render-previews'),
        (ROOT / 'edited-assets', archive / 'image-edits'),
        (ROOT / 'Zihao_2023(Eng).pdf', archive / 'Zihao_2023(Eng).pdf'),
        (ROOT / 'Zihao_s_CV', ROOT / 'docs/cv/source'),
        (ROOT / 'display', archive / 'legacy/display'),
        (ROOT / 'pages/demo.key', archive / 'legacy/demo.key'),
    ):
        if origin.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(origin), str(target))
    for origin in (ROOT / 'scripts').glob('*'):
        folder = ROOT / 'tools/video' if origin.suffix == '.py' else archive / 'legacy/scripts'
        folder.mkdir(parents=True, exist_ok=True)
        shutil.move(str(origin), str(folder / origin.name))
    if (ROOT / 'scripts').exists(): (ROOT / 'scripts').rmdir()
    for name in ('2.html', '3.html', '4.html', 'parallex.html', '1.txt'):
        origin = ROOT / 'pages' / name
        if origin.exists():
            folder = archive / 'legacy/pages'
            folder.mkdir(parents=True, exist_ok=True)
            shutil.move(str(origin), str(folder / name))
    manifest = {'media': {source.relative_to(ROOT).as_posix(): target.relative_to(ROOT).as_posix() for source, target in mapping.items()}, 'album_previews': thumbnail_map}
    (ROOT / 'docs/asset-map.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    print('Migration complete. Original files retained under archive/.')

if __name__ == '__main__': main()
