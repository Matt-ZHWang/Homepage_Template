# Zihao Wang Personal Homepage

This repository hosts the personal academic homepage of Zihao Wang.

Live site: [Zihao Wang](https://zihaowang-kiaa.github.io/personal-homepage/)

## Structure

- `index.html` - homepage with about, research projects, publications, posts preview, CV, and contact links.
- `pages/high-redshift-black-holes-agns.html` - project page for high-redshift black holes and AGNs.
- `pages/high-redshift-galaxies-star-formation.html` - project page for high-redshift galaxies, THESAN-ZOOM, and star formation.
- `pages/artificial-intelligence-astronomy.html` - project page for machine learning methods in observational astronomy.
- `pages/posts.html` - posts, photography albums, lecture notes, and side collections.
- `assets/css/` - shared accessibility baseline (`site.css`) and page styling (`home.css`, `research.css`, `posts.css`).
- `assets/js/` - shared video/motion preferences (`site.js`), homepage room interactions (`home.js`), research navigation (`research.js`), and the photo viewer (`posts.js`).
- `assets/images/` - images grouped into `portrait/`, `collage/`, `research/`, `journal/`, and `albums/`. Most use optimized WebP; the portrait retains its unmodified original PNG.
- `assets/videos/` - published simulation videos.
- `albums/` - original-resolution photographs; the gallery uses compressed previews from `assets/images/albums/` and retains links to these originals.
- `content/` - editorial source notes for the homepage, research pages, and garden. These are reference documents, not a build pipeline; changes must also be reflected in the relevant HTML.
- `docs/cv/Zihao_2026.pdf` - current CV linked from the homepage; editable CV sources live in `docs/cv/source/`.
- `Zihao_2026.pdf` - compatibility copy for existing root-level CV links; keep it synchronized with the published CV.
- `docs/asset-map.json` - old-to-new media paths and album-preview mapping.
- `docs/design-notes.md` - visual direction and maintenance conventions.
- `tools/` - static-site checks, asset-organization utility, and local video-rendering scripts.
- `archive/` and `output/` - preserved local originals, historical experiments, generated previews, and QA output. Both directories are ignored by Git and must not be committed or used as dependencies of the published site.

## Preview and validate

The site is plain HTML, CSS, and JavaScript, served directly by GitHub Pages. No package installation or build step is required. From the repository root:

```bash
python3 -m http.server 8000
```

Then open [the local homepage](http://127.0.0.1:8000/index.html). Run the static validation separately:

```bash
python3 tools/check_site.py
```

The checker inspects all five published pages and CSS for missing local references, broken local anchors, duplicate IDs, heading counts, and obviously invalid video files. It does not verify external URLs or replace browser testing.

Before publishing, test desktop and narrow mobile layouts, keyboard navigation, room interactions, album expansion, the photo viewer, and reduced-motion preferences. Keep research figures fully readable and preserve the portrait's original colors. Check that neither `archive/` nor `output/` appears in the proposed commit.
