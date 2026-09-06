# Design and maintenance notes

## A house with working rooms and a garden

The homepage is the front room: an introduction, research directions, selected papers, and routes to the rest of the house. Three research pages are working rooms. The posts page is the garden, with cinema, music, essays, photography, and lecture notes. The mailbox and CV remain ordinary, directly usable links.

Use atmosphere to support navigation rather than conceal it. Drag interactions on the homepage are an additional way to explore; visitors must retain click and keyboard routes. Implementation notes, authoring commands, and unfinished placeholders belong in documentation, never in visible page copy.

## Visual direction

- Near-black `#08090a`, warm ivory `#efeae2`, restrained red `#bd342c`, and muted cyan `#a6c7ce` form the shared palette.
- Large serif titles, small navigational labels, fine rules, and generous spacing provide hierarchy. Avoid turning every section into a generic bordered card.
- Collage and architectural elements give the front room and research pages a theatrical character. Keep them clear of body text and scientific figures.
- Preserve the portrait's original colors. Do not apply grayscale, desaturation, or a color-changing overlay to the portrait.
- Scientific covers and plots need complete, legible presentation. Use contain-style fitting where cropping would remove scientific content.
- The garden is quieter and more intimate: a photographic opening, asymmetric journal layouts, and broad album rows. Expressive preview crops are appropriate for photographs because original files remain available.

## File responsibilities

`index.html` and the four documents in `pages/` contain the published semantic structure and editorial content. `content/*.md` retains the source material and research notes; there is no automatic Markdown-to-HTML conversion.

`assets/css/site.css` provides shared focus, motion-control, and accessibility rules. `home.css`, `research.css`, and `posts.css` own the visual direction of their respective pages. Load the baseline before the page stylesheet.

`assets/js/site.js` manages ambient-video motion preferences, visibility-based pausing, and explicit playback control. `home.js` owns the interactive room stage; `research.js` owns project navigation and external-link behavior; `posts.js` owns section navigation and the photograph viewer. Load shared behavior before page-specific behavior, using deferred scripts.

## Assets and preservation

Published images live under `assets/images/`, organized as `portrait/`, `collage/`, `research/`, `journal/`, and `albums/`. Published video clips live under `assets/videos/`. The previous `source materials/` paths are superseded by the entries in `docs/asset-map.json`.

The LRD hero uses `assets/videos/bh-star-to-agn-realistic-45s.mp4`, copied unchanged from the final 45-second, 1920 × 1080, 60 fps render in `output/bh_star_to_agn_realistic/`. Its matching still is `assets/images/research/bh-star-to-agn-realistic-poster.png`. The 20-second accelerated variant remains local. The movie is an illustrative 3-D rendering, not a calibrated hydrodynamic simulation.

The `album_previews` mapping pairs each original in `albums/` with its optimized WebP preview in `assets/images/albums/`. Keep the originals and the mapping: previews are for efficient browsing, while original links preserve access to the full photograph. Keep album and photograph order intact. Album order is Sri Lanka, USA, Malaysia & Singapore, Tibet, Qinhuangdao, Haikou, and Experimental.

The current CV is `docs/cv/Zihao_2026.pdf`. Sources and supporting files live under `docs/cv/source/`. The root `Zihao_2026.pdf` is a compatibility copy for existing bookmarks and must remain synchronized when the CV changes.

`archive/` preserves local historical pages, experiments, and source assets. `output/` is for local generated previews and verification artifacts. Preserve these directories locally; do not commit them. Published HTML, CSS, and JavaScript must not depend on either directory.

`tools/organize_assets.py` records the one-time asset-organization workflow (macOS `sips` and `cwebp` are required), and `tools/video/` contains local video-production scripts. Neither is required to serve the website. Review paths and outputs before rerunning media processing; do not replace original photographs with compressed derivatives. The portrait is copied without conversion or color modification.

## Interaction and verification

Use visible focus states, meaningful link labels, and native controls. Albums use `details`/`summary`, so expansion remains available without JavaScript. The photo viewer adds a native modal, previous/next controls, arrow-key navigation, Escape-to-close, an original-file link, and focus restoration. Links to original photographs remain the no-JavaScript fallback.

Honor reduced-motion preferences and keep pause controls for ambient motion. Nonhero photographs should load lazily. No remote font service or JavaScript framework is required.

From the repository root, run `python3 tools/check_site.py`. Serve the site with `python3 -m http.server 8000`, then inspect all five pages in a browser at desktop and mobile widths. Verify keyboard routes, album expansion, viewer controls, media playback, portrait color, figure legibility, and absence of horizontal overflow. The static checker validates local structure and references, not visual appearance or external content.
