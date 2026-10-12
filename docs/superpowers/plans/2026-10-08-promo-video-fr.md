# Promo video (FR, 30 s): implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:executing-plans (Native, as set in CLAUDE.md) to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking. Before writing composition HTML, load `/hyperframes-core`, `/hyperframes-animation` and the `/general-video` workflow (`npx hyperframes skills update general-video`).

**Goal:** a 30-second, 1920×1080 French promo video of the UX/UI audit tool in the light Antigravity style, rendered with HyperFrames.

**Architecture:** a HyperFrames project in `video/promo-fr/`. Its root `index.html` places 8 beat sub-compositions on the timeline, plus audio tracks. Each beat is a standalone HTML file with its own GSAP timeline, sharing one `tokens.css`. A pytest file pins the timeline, the copy and the facts, and `npx hyperframes check` and `snapshot` act as the render gate.

**Tech stack:** HyperFrames CLI 0.8.141 (`npx hyperframes@0.8.141`), GSAP (HyperFrames default runtime), Canvas 2D for the dot field, pytest with stdlib `html.parser` for the structural tests.

**Spec:** `docs/superpowers/specs/2026-10-08-promo-video-fr-design.md`

## Global constraints
- 1920×1080, 30 fps, total duration exactly 30.0 s.
- Every on-screen string is French. The strings "Claude", "VLM", "GPT", "Gemini", "machine finding" never appear in any composition file.
- Beat windows are exactly as follows: hook 0–4.5, logo 4.5–6.5, solution 6.5–9, input 9–12, evidence 12–17, stat 17–20, report-expert 20–26, end 26–30.
- Colours come only from `tokens.css`: `#1F2430 #3D4456 #5B6275 #E4E7EF #F7F8FC #5B3FD9 #EFEBFF #FFE600` plus white. Ease: `cubic-bezier(.2,.8,.2,1)`. There are no dark backgrounds.
- Headlines are at least 56 px. Every text beat stays readable for at least 2 s.
- The facts are 7 axes and 67 criteria (10+9+10+8+12+9+9). There are 5 findings with the same boxes and FR text as `DEMO_FINDINGS` in `src/ui/frontend/landing/Landing.jsx`.
- Expert: "Sofiene Mhadheb", « Expert en innovation client et design d'expérience, EY Studio+ », CTA « Réserver un appel avec un expert ».
- `video/promo-fr/renders/` and `video/promo-fr/assets/expert.jpg` are git-ignored (the photo stays local until the user says otherwise).
- Commit only the files you changed. One commit per task.

## Review focus
1. **Text clipping or overflow at 1080p** in the longest headline (« Puis un expert UX/UI, pour les recommandations et la refonte. »). Pinned by a `snapshot` at 24.5 s plus `hyperframes check` layout inspection (Task 5).
2. **Finding boxes misaligned with the scaled capture.** Pinned by a test that recomputes each box from `Landing.jsx` coordinates multiplied by the render scale (Task 4).
3. **Seek non-determinism** (the dot field uses randomness or wall-clock time, so a frame differs between preview and render). Pinned by a test asserting a seeded PRNG and no `Date.now`/`performance.now`/`Math.random` in `dotfield.js` (Task 2).
4. **Missing assets at render time** (absolute paths or links into `src/`). Pinned by a test asserting every `src=`/`url(` resolves inside `video/promo-fr/` (Task 1).
5. **Audio clipping or music drowning the ticks.** Pinned by `normalize-audio` and a test asserting the music volume is at most 0.6 and the SFX clips start inside the evidence and stat windows (Task 7).

---

### Task 1: Scaffold, assets, tokens, contract test

**Files:**
- Create: `video/promo-fr/` via `npx hyperframes@0.8.141 init` (keep `hyperframes.json`, `package.json`, `index.html`).
- Create: `video/promo-fr/renders/reference/` (git-ignored): the source video `op7418-2103148288400924827.mp4` plus its 4×5 contact sheet and the user's « Switch » frame, kept as the visual reference for every task.
- Create: `video/promo-fr/tokens.css`, `video/promo-fr/copy.json` (all FR strings keyed by beat), `video/promo-fr/.gitignore` (`renders/`, `assets/expert.jpg`).
- Create: `video/promo-fr/assets/` containing `ey-studio-plus.png`, `w3c-bad-citylights.jpg` (copied), `findings.json` (5 findings: axis, severity, measured, box, fr text, copied from `Landing.jsx`), `axes.json` (7 × {id, fr short, criteria}), `expert.jpg` (the user's photo, cropped square on the face, 600×600).
- Create: 8 empty beat files `video/promo-fr/compositions/{hook,logo,solution,input,evidence,stat,report-expert,end}.html`, each with a root having the correct `data-duration`.
- Modify: `video/promo-fr/index.html` to place the 8 beats at the spec windows.
- Test: `tests/test_promo_video.py`

**Interfaces:**
- Produces: `copy.json` keys `hook[3]`, `solution`, `input`, `evidence`, `stat`, `report`, `expert`, `cta`, `payoff`, `tagline`. Each beat reads its strings from this file at build time. Strings are inlined in the HTML, and the test checks they are equal.
- Produces: the CSS custom properties `--ink --ink-2 --muted --line --canvas --accent --accent-soft --ey --ease` in `tokens.css`.

- [ ] Step 1: write the tests. `test_timeline_windows` (parse `index.html` and assert the 8 `(data-composition-src, data-start, data-duration)` tuples equal the spec windows, and the root duration is 30). `test_copy_is_french_and_clean` (no forbidden words in any file under `video/promo-fr/compositions` or `copy.json`). `test_facts` (sum of the criteria in `axes.json` is 67, there are 7 axes, and `findings.json` equals the `DEMO_FINDINGS` boxes and FR text parsed from `Landing.jsx`). `test_assets_are_local` (every `src=`/`href=`/`url(` in the project resolves to an existing file under `video/promo-fr/`).
- [ ] Step 2: run `.venv/Scripts/python.exe -m pytest -q tests/test_promo_video.py`. Expected: FAIL (the project doesn't exist yet).
- [ ] Step 3: scaffold, copy the assets, write the tokens, copy, the empty beats and the root timeline.
- [ ] Step 4: run the tests and expect PASS. Then run `npx hyperframes check` in `video/promo-fr/` and expect no errors.
- [ ] Step 5: commit, "Scaffold the French promo video project".

### Task 2: Hook and logo beats (dot field)

**Files:** create `video/promo-fr/lib/dotfield.js`. Fill `compositions/hook.html` and `compositions/logo.html`. Extend `tests/test_promo_video.py`.

**Interfaces:**
- Produces: `createDotField(canvas, {seed, density, colors}) → {drawAt(t), fall(ids, t0, t1), gatherTo(points, t0, t1)}`, a pure function of `t` (seek-safe). `logoPoints(imgData, step) → [{x,y}]` samples the logo's opaque pixels.

- [ ] Step 1: write the tests. `test_dotfield_is_deterministic` (no `Math.random`, `Date.now` or `performance.now` in `dotfield.js`, and it defines a seeded PRNG). `test_hook_copy` (the 3 hook strings appear in `hook.html` in order, matching `copy.json`).
- [ ] Step 2: run the tests. Expected: FAIL.
- [ ] Step 3: implement. Hook: the dot field drifts, and the 3 lines reveal blur-to-sharp at 0.2 / 1.6 / 2.8 s. On « Ils partent » about 15% of the dots fall and fade. Logo: the dots gather into the logo points by 6.0 s, then the PNG crossfades in over the dots.
- [ ] Step 4: run the tests and expect PASS. Run `npx hyperframes snapshot --at 1,2,3.5,5.2,6.2` and look at the PNGs: the text must be legible and the dots must form a recognisable logo.
- [ ] Step 5: commit, "Add the hook and logo reveal beats".

### Task 3: Solution and input beats

**Files:** fill `compositions/solution.html` and `compositions/input.html`, and add the source icons as inline SVG (site, app, Figma). Extend the tests.

**Interfaces:** produces `lib/horizon.css` (class `.horizon`: the light arc, rim and glow, sized by `--horizon-top`). `end.html` reuses it in Task 6.

- [ ] Step 1: write the tests. `test_solution_input_copy` (the strings are present and match `copy.json`). `test_input_types_example_url` (the only URL in `input.html` is `https://exemple.fr`, never a real client). `test_solution_giant_word` (the giant word « Audit UX/UI » has a computed font-weight ≤ 300 and a font-size ≥ 220 px in its inline style or class, and `.horizon` is present).
- [ ] Step 2: run the tests. Expected: FAIL.
- [ ] Step 3: implement. Solution: the horizon arc rises from below. The giant thin word « Audit UX/UI » fades in with blur-to-sharp, then the subtitle « mené par un agent IA » reveals letter by letter, as in the reference frame. Input: the headline on the left, its three phrases appearing in turn. On the right, an input box types `https://exemple.fr` character by character (seek-safe, driven by the timeline, from 9.2 to 10.2 s). Below it, three source cards (site, app, Figma, as inline SVG icons with labels) rise in with a 3D tilt, each synced to its phrase.
- [ ] Step 4: run the tests and expect PASS. Run `snapshot --at 7.5,10,11.5` and check the PNGs.
- [ ] Step 5: commit, "Add the solution and input beats".

### Task 4: Evidence beat

**Files:** fill `compositions/evidence.html` and add the SFX markers (`data-sfx` attributes at each finding time). Extend the tests.

**Interfaces:**
- Consumes: `assets/findings.json` and `assets/w3c-bad-citylights.jpg`.
- Produces: finding reveal times `[13.2, 13.9, 14.6, 15.3, 16.0]` (absolute), which Task 7 uses for the ticks.

- [ ] Step 1: write the tests. `test_evidence_boxes_scaled` (each `.finding` element's left/top/width/height equals the `findings.json` box × the render scale written on the root `data-scale`, ±1 px). `test_evidence_labels` (the contrast finding shows « Mesuré · axe-core » and the other 4 show « Revue d'expert »).
- [ ] Step 2: run the tests. Expected: FAIL.
- [ ] Step 3: implement. The headline sits left. The capture rises in with a 3D tilt that settles flat by 12.9 s. Each finding draws its frame in EY yellow and its label slides in, at the times above.
- [ ] Step 4: run the tests and expect PASS. Run `snapshot --at 13,16.5` and check the boxes sit on the right elements.
- [ ] Step 5: commit, "Add the evidence beat with the five findings".

### Task 5: Stat and report-expert beats

**Files:** fill `compositions/stat.html` and `compositions/report-expert.html`. Extend the tests.

- [ ] Step 1: write the tests. `test_stat_counter` (the counter ends at 67, and the 7 orbit chips are the FR axis names from `axes.json`). `test_expert_card` (the name, title and CTA match the global constraints, and the photo is `assets/expert.jpg` with `alt` equal to the name).
- [ ] Step 2: run the tests. Expected: FAIL.
- [ ] Step 3: implement. Stat: the counter tweens 0 → 67 (whole numbers, seek-safe) from 17.3 to 19.0 s while the axis chips orbit. Report (20–22.5 s): the light report cover with the dot motif, a score arc and 7 axis scores out of 100, sliding in. Expert (22.5–26 s): the card with the round photo, the name and the title. A cursor moves to the CTA and clicks at 25.0 s (press scale 0.97, violet ripple).
- [ ] Step 4: run the tests and expect PASS. Run `snapshot --at 19.5,21.5,24.5,25.2` and check that the longest headline does not clip (Review focus 1).
- [ ] Step 5: commit, "Add the stat and report-expert beats".

### Task 6: End card and transitions

**Files:** fill `compositions/end.html`, and add zoom-through transitions between beats in `index.html`. Extend the tests.

- [ ] Step 1: write the test `test_end_copy` (the payoff « L'agent IA audite. L'expert transforme. » and the tagline « Audit UX/UI par agent IA · EY Studio+ » are present, and the logo is shown).
- [ ] Step 2: run the test. Expected: FAIL.
- [ ] Step 3: implement. The payoff runs 26–28 s, centred. Then the logo and tagline above the light horizon arc (`lib/horizon.css`), with the faint dot field returning (reusing `createDotField`). Add the zoom-through transitions (about 0.3 s, no black frames).
- [ ] Step 4: run the tests and expect PASS. Run `npx hyperframes check` with no errors. Run `snapshot` at the midpoint of every beat and assemble a storyboard sheet with `ffmpeg … tile=4x3` into `renders/storyboard.png`.
- [ ] Step 5: commit, "Add the end card and beat transitions". **Then stop: the user approves the storyboard** (spec review loop step 1).

### Task 7: Audio

**Files:** create `video/promo-fr/assets/audio/` (music bed and tick SFX, royalty-free, with licence notes in `assets/audio/CREDITS.md`). Add the audio tracks in `index.html`. Extend the tests.

- [ ] Step 1: write the test `test_audio_tracks` (one music clip from 0 to 30 s with volume ≤ 0.6 and fade-in and fade-out. 5 tick clips start at the Task 4 times ±0.05 s. One counter tick sequence sits inside 17.3–19.0 s. `CREDITS.md` names each file's source and licence).
- [ ] Step 2: run the test. Expected: FAIL.
- [ ] Step 3: source 2–3 candidate tracks with `/media-use` and present them to the user. **Stop for the user's pick.** Then run `npx hyperframes beats` on the chosen track, nudge the main cuts by at most 0.15 s onto beats (re-run Task 1's window test with a ±0.15 s tolerance documented in the test), place the clips and `normalize-audio`.
- [ ] Step 4: run the tests and expect PASS.
- [ ] Step 5: commit, "Add the music bed and finding ticks".

### Task 8: Preview, final render, pacing check

**Files:** none committed except a `video/promo-fr/README.md` (how to preview and render, and where the photo comes from).

- [ ] Step 1: `npx hyperframes render --quality draft -o renders/preview.mp4`. Check with `ffprobe` that the duration is 30.0 s ±0.05 and the size is 1920×1080. **Stop: the user reviews the timing.**
- [ ] Step 2: after approval, `npx hyperframes render -o renders/promo-fr-30s.mp4` at final quality.
- [ ] Step 3: make a 4×5 contact sheet of the final render and compare it with the source's sheet (download the source again into `renders/reference/` if it's missing, and never commit it) (one new visual idea every 2–5 s, no frame darker than the canvas).
- [ ] Step 4: run the full `tests/test_promo_video.py`, then the full suite in the background with the tail read.
- [ ] Step 5: commit the README. Then one independent whole-branch review by a fresh subagent on the most capable model, as CLAUDE.md requires.
