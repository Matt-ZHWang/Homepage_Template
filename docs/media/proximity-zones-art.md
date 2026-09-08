# Proximity zones display rendering

Created 2026-09-08 with the built-in imagegen tool, in one reference-image editing call. No CLI/API fallback was used.

- Scientific source: `assets/images/research/main_z6.pdf` (retained locally).
- Reference: the direct 1745 × 1800 PNG rasterization of that PDF.
- Scientific delivery: `assets/images/research/proximity-zones-z6-highres.png`, 5814 × 6000 pixels, unmodified numerical figure.
- Artistic delivery: `assets/images/research/proximity-zones-z6-art.png`, 1254 × 1254 pixels, the tool's native output. It was not upscaled or represented as a 6000-pixel image.
- Browsing version: `assets/images/research/proximity-zones-z6-art-preview.webp`, same dimensions, WebP quality 95.

The display version is an AI-assisted artistic interpretation, not a new simulation or a quantitatively faithful data visualization. The model changed local gas structure while broadly retaining the four source panels' appearance. Source markers, calibration bars, and labels were removed from this derivative. The website's image alternative text identifies it as an artistic rendering. At the user's request, the visible caption and original-figure download link were subsequently removed; the untouched scientific figure remains in the repository. The original source, its colors, numerical labels, and scale bars are preserved. No website palette, portrait, or background-interaction changes were made.

## Exact generation prompt

```text
Use case: style-transfer
Asset type: artistic display image for an academic astrophysics website, project “Proximity zones”; this is an explicitly captioned artistic interpretation, not a quantitative scientific plot.
Input images: Image 1 is the edit target, the actual four-panel simulation figure. Preserve its recognizable morphology and same orthographic view.
Primary request: Create ONE high-resolution, crisp, sophisticated artistic rendering of this supplied 2×2 figure, preserving the positions, topology, relative shapes and scale of the source filaments and ionized cavities as closely as possible. Retain the same near-square aspect ratio as the input (1745:1800) and four equal panels in precisely the same arrangement.
Top-left: dense interconnected cosmic gas web with the source's warm orange/gold filament threads and magenta-violet low-density regions; preserve the dense central junction and the exact recognizable branches and void pattern.
Top-right: heated gas structure in deep violet with muted rose/copper warmth, tiny gas clumps and the compact warm central junction at the same position. Preserve the source's cool/dark void boundary near the lower edge. Those clumps are simulated gas, not stars.
Bottom-left: hydrogen-ionized structure with the source's pale cool cyan and muted pink regions, delicate dark green branching web and irregular black boundary along the bottom. Preserve those visible contours and source color distinctions; refine dimension and shading without converting it to a generic dark cosmic web.
Bottom-right: helium-ionized structure with the same irregular multi-lobed pale cream central cavity and its source contours, warm amber transition against plum/violet surrounding gas, with cool blue/cyan structure near the lower edge. Preserve its shape, footprint and relative location; it is a diffuse ionized gas volume, not a galaxy, starburst or explosion.
Style/medium: restrained elegant volumetric scientific art. Add subtle depth to the existing gas filaments and cavities, dark-space voids, fine layered gas texture and delicate glow only at the source's dense junctions. Sophisticated dark academic art direction, detailed but quiet, with controlled tonal contrast and preserved distinct panel palettes.
Composition/framing: Edge-to-edge four-panel grid with only very fine dark vertical and horizontal dividing lines. No white outside border. Keep the existing framing, orientation and shared spatial relationships; do not crop, rotate or rearrange panels.
Edits: Remove ALL plot labels, redshift label, color calibration bars, ticks, units, scale bars and ALL circular overlaid data markers (black, outlined and colored). Reconstruct the local underlying gas texture cleanly at their locations. Markers are annotations to erase, never astronomical objects to render.
Constraints: No written text, titles, logos, legends or watermark. No added stars, galaxies, accretion disks, jets, planets or invented astronomical objects. No new major branches or cavities. No garish bloom, lens flares, oversaturation, generic space wallpaper, poster styling or extra panels. Preserve existing morphology over artistic novelty. Output the largest practical crisp PNG in the near-square source aspect ratio.
```
