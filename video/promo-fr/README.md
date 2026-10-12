# Promo video (FR, 30 s)

A 30-second French presentation of the UX/UI audit tool for prospective clients, built with [HyperFrames](https://hyperframes.heygen.com).
Design: `docs/superpowers/specs/2026-10-08-promo-video-fr-design.md` · Plan: `docs/superpowers/plans/2026-10-08-promo-video-fr.md`.

## Before you render
Two local files are git-ignored and must be present:
- `assets/expert.jpg`: the expert's photo, square 600×600, head and shoulders.
- `assets/audio/music-test.mp3`: the music bed. The current file is a **personal-use test track**, so replace it with a licensed one before any render is shown to a client (see `assets/audio/CREDITS.md`).

## Commands (run in this folder)
- Preview in the browser studio: `npm run dev`
- Validate: `npm run check`
- Draft render: `npx --yes hyperframes@0.8.141 render --quality draft -o renders/preview.mp4`
- Final render: `npx --yes hyperframes@0.8.141 render --quality delivery -o renders/promo-fr-30s.mp4`
- Structure tests (from the repo root): `.venv/Scripts/python.exe -m pytest -q tests/test_promo_video.py`

## Layout
- `index.html`: root timeline, with the 8 beats and the audio tracks.
- `compositions/`: one file per beat (`hook`, `logo`, `solution`, `input`, `evidence`, `stat`, `report-expert`, `end`).
- `lib/`: dot field (seeded, seek-safe), word reveal, horizon arc, logo points, vendored GSAP.
- `copy.json`, `assets/findings.json`, `assets/axes.json`: copy and facts, pinned by the tests against `src/ui/frontend/landing/Landing.jsx`.
- `lib/logo-points.js` is generated from `assets/ey-studio-plus.png`. Regenerate it if the logo changes.
