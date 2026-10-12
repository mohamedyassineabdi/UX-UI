# Promo video (FR, 30 s): design

Date: 2026-10-08 · Branch: feat/quick-audit · Status: approved in brainstorming, awaiting spec review

## Goal
A 30-second French video that presents the UX/UI audit tool to a prospective client. It is shown on screen during a meeting or call and can also be sent on its own.

It is inspired by the pacing and structure of the source video (`op7418-2103148288400924827.mp4`, 50 s, dark, no voiceover): pain hook → brand reveal → "headline + live product proof" beats → one stat → end card. The visuals, script and structure are original, and the look follows the light Antigravity language already used by the landing page and the client report cover.

## Success criteria
- The client understands the problem, the solution, the proof and the next step (a call with an expert) in 30 s, even with the sound muted.
- Every on-screen fact matches the product: 7 axes, 67 criteria, the real W3C capture and its findings, and the real expert CTA.
- It looks like a Big 4 / EY Studio+ deliverable. The copy says "agent IA" and never names a model or "VLM".

## Fixed decisions
| Topic | Decision |
|---|---|
| Format | 16:9, 1920×1080, 30 fps, 30.0 s |
| Language | French only |
| Problem | Silent loss: users don't complain, they leave, and the business doesn't know why |
| Sound | Royalty-free music bed + soft tick SFX (one per finding, and on the counter). No voiceover. Works muted |
| Screens | Rebuilt as HTML from the real assets (no screen recording) |
| Expert | Real person: Sofiene Mhadheb, « Expert en innovation client et design d'expérience, EY Studio+ », with the photo supplied by the user |
| Out of scope | 9:16 version, voiceover, English version |

## Script and timeline
| Time | Beat (sub-composition) | On-screen copy | Visual |
|---|---|---|---|
| 0–4.5 s | `hook` | « Vos utilisateurs ne se plaignent pas. » → « Ils partent. » → « Et vous ne savez pas pourquoi. » | Dot field drifting. On « Ils partent », some dots fall away and fade |
| 4.5–6.5 s | `logo` | — | The dots gather into the EY Studio+ logo |
| 6.5–9 s | `solution` | Giant word « Audit UX/UI », subtitle « mené par un agent IA » | Giant thin-weight word (source's « Switch » frame) over the light horizon arc |
| 9–12 s | `input` | « Un lien. Une app. Une maquette Figma. » | `https://exemple.fr` (a neutral example, never a real client) is typed into an input, then three source cards (site, app, Figma) rise in with a stagger, one per phrase |
| 12–17 s | `evidence` | « Chaque constat, sa preuve. » | The W3C capture rises in with a 3D tilt that settles flat. The 5 findings draw in one by one as framed boxes with FR labels and a tick each |
| 17–20 s | `stat` | « 7 axes. 67 critères. » | A counter goes 0 → 67 while the 7 axis chips orbit |
| 20–22.5 s | `report-expert` (a) | « Un rapport prêt pour le comité. » | The client report cover (light style) slides in with scores out of 100 |
| 22.5–26 s | `report-expert` (b) | « Puis un expert UX/UI, pour les recommandations et la refonte. » | Expert card (photo, name, title). The cursor clicks « Réserver un appel avec un expert » |
| 26–28 s | `end` (a) | « L'agent IA audite. L'expert transforme. » | Centred headline |
| 28–30 s | `end` (b) | Logo + « Audit UX/UI par agent IA · EY Studio+ » | Logo above the light horizon arc, faint dot field behind (mirrors the source's end card) |

## Visual language
- **Tokens** (copied from `src/ui/frontend/styles/landing.css`): ink `#1F2430`, ink-2 `#3D4456`, muted `#5B6275`, line `#E4E7EF`, canvas `#F7F8FC`, accent `#5B3FD9`, accent-soft `#EFEBFF`, EY yellow `#FFE600` (used sparingly), ease `cubic-bezier(.2,.8,.2,1)`.
- **Light only.** The source's dark planet horizon becomes a **light horizon arc**: a pale arc filling the bottom third of the frame, with a thin violet→yellow rim light and a soft glow above it, on white. It is used in `solution` and `end` (b), as the source uses it for its brand moments. Reference: the user's « Switch » frame from the source at 0:24.
- **Giant-word treatment:** one or two words in a very thin weight (≥ 220 px), with a small, bold subtitle under them that reveals letter by letter, as in the reference frame. Used once, in `solution`.
- **Type:** the landing font, large and tightly tracked. Feature beats put the headline on the left and the screen on the right. The hook, stat and end beats are centred.
- **Motion:** screens rise in with a slight 3D tilt that settles flat. Text uses a staggered blur-to-sharp reveal. Transitions between beats are quick zoom-throughs with no fades to black. Main cuts align with the music's beat.

## Real assets reused (copied into the project, not linked)
- Logo: `src/ui/frontend/assets/ey-studio-plus.png`
- Capture: `src/ui/frontend/landing/assets/w3c-bad-citylights.jpg`, plus the 5 findings (boxes and FR text) from `DEMO_FINDINGS` in `src/ui/frontend/landing/Landing.jsx`. The contrast finding is labelled « Mesuré · axe-core » and the others « Revue d'expert ».
- Axis names (FR `short`) and the criteria counts 10+9+10+8+12+9+9 = 67 from `AXES` in `Landing.jsx`.
- Expert copy from `src/report/roadmap_teaser.py` (FR title, CTA « Réserver un appel avec un expert »). The photo is supplied by the user and cropped round.

## Build
- HyperFrames project in `video/promo-fr/`: a root `index.html` and one sub-composition per beat (`hook`, `logo`, `solution`, `input`, `evidence`, `stat`, `report-expert`, `end`). Shared `tokens.css`. GSAP on a single paused, seekable timeline.
- Audio goes on its own tracks: the music bed, and SFX clips placed on the finding and counter beats.
- Renders go to `video/promo-fr/renders/` (git-ignored).

## Review loop
1. Storyboard: one still frame per beat. The user approves it.
2. Low-res preview MP4 to check timing. The user approves it.
3. Music track chosen. The user approves it.
4. Final 1080p render, plus a 4×5 contact sheet compared against the source for pacing.

## Risks
- **Beat 4 is dense** (two ideas in 6 s). The report shot is kept to 2.5 s and the expert card gets 3.5 s.
- **Readability:** headlines are at least 56 px at 1080p, and every text beat stays on screen for at least 2 s.
- **Personal photo:** used only with the user's consent (given here). The project's `assets/` copy is committed only if the user agrees.
