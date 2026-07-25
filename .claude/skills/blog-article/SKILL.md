---
name: blog-article
description: >-
  Write a new article for this blog end to end — angle and title, front matter,
  cover image (ppq:image) and in-text images (imgflip memes, dataviz charts,
  hand-authored SVG diagrams that survive the dark/light toggle), both-theme
  verification, then publish and syndicate. Use when asked to write, draft, or
  add a post/article to the zxczxc.dev blog (~/src/blog).
argument-hint: "[slug or topic, or path to raw material]"
---

# Write an article for zxczxc.dev

Blog repo: `~/src/blog` (Lume + Deno → GitHub Pages). Every path below is
relative to it — `cd` there first if the cwd is elsewhere.

This skill lives in the blog repo (`.claude/skills/blog-article/`) and is
symlinked from `~/.claude-personal/skills/` so every session sees it. Edit it
here and commit it with the post that taught you something.

Read `README.md` first — "Publishing a new article", "Diagrams and article
styling", "Cover images". It is the source of truth for the pipeline; this
skill is the writing/illustration workflow on top of it.

## 1. Angle and title before prose

`notes/hn-playbook.md` is the measured version of this (59k HN stories). The
short form:

- **Concrete number in the title (1.42×), short ≤6 words (1.24×), first-person
  (1.17×). Never end with "?" (0.67×).** Specifics read as substance.
- **Lead with the non-AI angle if one exists** — "How I made X 10× faster"
  beats "How AI helped me…" (AI framing costs ~1/3 of the odds).
- Winning shapes: David-vs-Goliath economics, technical detective story,
  contrarian essay, retro/preservation. `It wasn't thermal throttling` and
  `Mouse over WiFi` are the house examples.
- Blockchain/crypto content: frame the engineering, not the coin.

For a story-shaped post with real raw material (logs, transcripts, dead ends),
run the **`good-article`** skill instead of freehanding — it does material
interview → plan checkpoint → draft → critic passes → fact audit. Come back
here for front matter, images, diagrams, and publishing. For short notes
(`posts/lnd-node.md`, `posts/tucana.md` scale), just write it.

## 2. The file

`posts/<slug>.md` — the slug is the permanent URL, pick it once.

```markdown
---
title: "It wasn't thermal throttling"
date: 2026-07-25
author: Nikolay Bryskin
description: "One sentence — feed description, meta description, and the dev.to/Medium blurb."
image: /uploads/<slug>/cover.png
tags:
  - linux
---

Opening paragraph — the hook, no throat-clearing.

<!--more-->

Rest of the article.
```

- Everything above `<!--more-->` is the excerpt on the home page. Put the
  anomaly there, not the setup.
- `tags:` double as Medium topics (`medium-publish` types them into the topic
  picker), so use real dev.to/Medium topic names — lowercase, no spaces.
- Callouts: GitHub alert syntax (`> [!NOTE]`, `[!WARNING]`, …), styled in both
  themes. Use these, not bold-prefixed blockquotes. The house pattern for
  background is a `[!NOTE]` "Excursus: …" — see `posts/fpsdoctor.md`.
- Raw-HTML/interactive posts go in a `.vto` file — README, "Interactive /
  raw-HTML posts".

## 3. Images

All assets live in `uploads/<slug>/`, referenced root-absolute
(`![alt](/uploads/<slug>/x.png)`). Never hotlink, never hardcode
`https://zxczxc.dev/…` — syndicated copies outlive both.

**Cover** (`image:` front matter → hero, list thumbnail, og:image, feed image,
dev.to `main_image`, Medium featured image). 1200×630. **No text in it** —
generators mangle lettering and it's illegible at thumbnail size anyway. Must
read as one shape at 10rem wide.

- If the article has data, *render the cover from the real data* — the
  `hn-what-rises-what-drowns` cover is the article's actual day×hour hit-rate
  grid, one cell glowing. Beats any generated image and costs nothing. Load
  the **`dataviz`** skill before writing chart code.
- Otherwise generate it with the **`ppq:image`** skill: iterate the prompt on
  `imagen4-fast` (~$0.02), render the final on `nano-banana-2` (~$0.09, honors
  `--ar 16:9`). Prompt for flat vector / graphic-poster style, high contrast,
  one focal object, "no text anywhere". Relay the printed cost to the user.
  Pitch 2–4 concepts in prose before spending anything.
- Covers sit on both a light and a dark page — avoid near-white and near-black
  backgrounds that dissolve into one of them.
- **The cover must be a raster, even when you drew it as vector.** That field
  is `og:image`, and social crawlers (X, Facebook, LinkedIn, Slack, Discord)
  render nothing at all for an SVG; dev.to's proxy won't serve one either.
  Author it as SVG if that's easier — `battery-over-wifi` is a hand-drawn
  `cover.svg` — but commit the raster next to it as the referenced file.
  Render it at **2× (2400×1260)**: 1200×630 is the canonical og:image size,
  but the hero displays ~720 CSS px wide and upscales on HiDPI.

**Memes** — the **`imgflip`** skill, for a beat that's genuinely funny (a dead
end, an absurd yak-shave). One per article, max. Download with `-o` into
`uploads/<slug>/` immediately; imgflip's URLs are not permanent assets. JPEG
memes are theme-agnostic, so nothing else to worry about.

**Evidence images** (screenshots, terminal captures, oscilloscope traces) come
from the material — never generate them. Crop to the interesting part.

## 4. Diagrams — mermaid and graphviz are traps

**Don't ship either.** A ```` ```mermaid ```` fence renders as a literal code
block (no plugin is installed). And a mermaid-cli / `dot -Tsvg` render is
wrong for this site regardless of how it's embedded: near-black strokes that
vanish on the dark background, `foreignObject` labels, bundled fonts, opaque
white backgrounds, and no notion of the theme toggle. Fighting the themes back
into a generated SVG is more work than drawing it.

Use mermaid/dot as a *thinking* tool if it helps you settle the layout, then
**hand-author the SVG in the house style**. Copy the `<style>` block from a
reference implementation and edit geometry:

- `uploads/mouse-over-wifi/architecture.svg` — standalone file, `<img>`-embedded,
  themed with `@media (prefers-color-scheme: dark)`.
- the inline `<svg id="memwall">` in `posts/fpsdoctor.md` — CSS-variable themed,
  follows the manual toggle.

Palette (slate surfaces, indigo accent, rose "hot path"), light → dark:
surface `#f8fafc/#e2e8f0` → `#16202e/#2c3a4f`, node `#ffffff/#cbd5e1` →
`#0b1220/#3b4a61`, text `#1e293b` → `#e2e8f0`, muted `#64748b` → `#8fa3bb`,
flow `#94a3b8` → `#64748b`, accent `#6366f1` → `#818cf8`, hot `#e11d48` →
`#fb7185`. Fonts: `ui-sans-serif, system-ui` for labels, `ui-monospace` for
identifiers.

**Which embed to pick** (real trade-off, README has the full version):

| | `<img>` file in `uploads/` | inline `<svg>` in the `.md` |
|---|---|---|
| theme source | OS `prefers-color-scheme` only | follows the ◐ toggle correctly |
| wrong when | reader's toggle disagrees with their OS | — |
| syndication | automatic (scripts swap in PNG siblings) | passes through raw; dev.to/Medium strip it |

Default to the **file** for anything you plan to syndicate. Use **inline** when
theme correctness matters more (a diagram the article argues from).

Inline rules, all learned by breaking them:

- the opening `<svg …>` tag on **one line**, and **no blank lines** anywhere
  inside the element — markdown-it ends the raw-HTML block at the first blank
  line and markdown-parses the remainder into garbage;
- scope every rule under the svg's unique `#id` (a bare `.title {…}` leaks onto
  the page) and prefix `defs`/marker ids (`#mw-a`) — collisions are silent;
- three rule sets for colors: light defaults on `#id`; dark under
  `@media (prefers-color-scheme: dark) { :root:not([data-theme=light]) #id }`;
  dark again under `:root[data-theme=dark] #id`. The explicit toggle must win
  in both directions;
- `role="img"` + `aria-label` — inline SVG has no alt text.

**Size the type for the width it will be shown at.** A diagram authored at
880 wide and displayed in the 720px column shrinks every label by 0.82; 13px
becomes 10.6px and message labels stop fitting between sequence lifelines.
Author wide (~1120 viewBox), keep labels at 11–12px, and check the gap
between lifelines exceeds the longest label that spans it.

**Let diagrams break out past the text column** — 720px is cramped for
anything with lanes:

```css
.post-body img[src$=".svg"] { --w: min(1120px, calc(100% + 20rem), 96vw);
  display: block; width: var(--w); max-width: none;
  margin-inline: calc((100% - var(--w)) / 2); }
@media (max-width: 760px) {
  .post-body p:has(> img[src$=".svg"]) { overflow-x: auto; }
  .post-body img[src$=".svg"] { width: auto; min-width: 900px; margin-inline: 0; } }
```

Two things that recipe is deliberately avoiding. `margin-left: 50%` +
`transform: translateX(-50%)` is the usual breakout trick and it is **wrong
here**: the untransformed box still counts toward scroll width, so the page
gets a horizontal scrollbar with no element visibly overflowing. And the
column is not always centred in the viewport, so bound the width by the
column's own side room (`calc(100% + 20rem)`), not by `vw` alone. Below
760px a full-bleed diagram shrinks 11px text to under 4px — scroll it inside
its paragraph instead.

**A family of diagrams wants a generator, not four hand-edited files.** Put
the palette and the box/arrow helpers in one script (see `zxc-mouse`'s
`figures/gen-failure-figures.py`) so a palette change is one edit; commit the
SVGs it emits.

## 4b. Annotating jargon — use the popover API

Articles with a dozen kernel-level terms read better if the terms explain
themselves. Do **not** build hover tooltips:

- a bubble anchored to the text column can sit far from the term, and the
  pointer loses `:hover` on the way there — links inside are unreachable;
- `visibility: hidden` still occupies layout, so an off-column bubble puts a
  permanent horizontal scrollbar on the page;
- making the term itself a link fixes mouse and breaks touch — a tap
  navigates away and the reader never sees the definition.

The popover API is one mechanism for both input modes, no JavaScript:

```html
<button type="button" class="tgloss" popovertarget="g1" style="anchor-name:--g1">hidpp</button>
<span popover id="g1" class="tgloss-b" style="position-anchor:--g1">Definition… <a href="…">source</a></span>
```

```css
.tgloss { font: inherit; color: inherit; background: none; border: 0; padding: 0;
  cursor: pointer; text-decoration: underline dotted; text-underline-offset: .22em; }
.tgloss-b { position: fixed; inset: auto; bottom: 1.5rem; left: 50%; translate: -50% 0; margin: 0; }
.tgloss-b:popover-open { display: block; width: min(32rem, 92vw); /* card styling */ }
@supports (position-area: block-end span-inline-end) {
  .tgloss-b { position: absolute; position-area: block-end span-inline-end;
    position-try-fallbacks: flip-block, flip-inline;
    bottom: auto; left: auto; translate: none; margin-block: .35rem; } }
```

Click or tap pins it, click-outside and Esc dismiss it natively, links inside
are clickable, and it's a real button for keyboard and screen readers.

- **`position-area` needs both keywords from the same coordinate system.**
  `bottom span-inline-end` mixes physical with logical, so the declaration is
  dropped and the popover renders off-screen (`top: -958`) while
  `:popover-open` still reports true. Make the `@supports` test name the exact
  value you use, so an unsupporting browser gets the fixed-bottom card instead
  of a silently misplaced one.
- Popovers cannot be opened by CSS `:hover`, so this is click-only. Adding a
  hover preview on top means two mechanisms and duplicated content — ask first.
- **Syndication**: dev.to and Medium strip `<style>` and the attributes, so
  every definition spills inline as run-on prose. Decide before syndicating —
  strip the glosses from the copy, or fall back to `<abbr title>` (native
  tooltips, no links inside).

## 5. Verify both themes before pushing

`deno task serve` → <http://localhost:3000>. Check light, then flip with the ◐
button and check again. `chromium --force-dark-mode` does **not** flip
`prefers-color-scheme` — drive a real browser (playwright) for a dark
screenshot, or set `document.documentElement.dataset.theme = "dark"`.

Also check: the thumbnail on `/` (16:10 crop of the cover), alt text on every
image, and the `<!--more-->` split.

Measure, don't eyeball — screenshots miss both of these:

- **Horizontal overflow.** `document.documentElement.scrollWidth >
  clientWidth` catches the scrollbar that a hidden-but-laid-out bubble or a
  transformed breakout adds. When it trips, the offender often has *no*
  visibly overflowing box; compare `scrollWidth` against the untransformed
  layout position rather than hunting `getBoundingClientRect().right`.
- **Interactive bits.** Open the popover and hit-test what's inside:
  `document.elementFromPoint(x, y)` must return the `<a>`, not the card.
  Check every viewport you care about (1280, ~1480, 375) — the column is not
  centred at all widths.

One trap when screenshotting: Chrome does not apply `prefers-color-scheme`
emulation to SVG documents loaded in `<img>`, so an `<img>`-embedded diagram
follows the *real* OS setting while the page around it follows the emulated
one. A screenshot showing a dark diagram on a light page may be an artefact
of the tooling, not a bug in the SVG.

## 6. Publish and syndicate

1. Commit + push to `main`; GitHub Actions deploys in ~1 min. Verify live.
2. **dev.to**: `scripts/publish-devto.py <slug>` → creates a draft with the
   canonical URL. If it rasterizes an SVG, commit and push the PNG **before**
   publishing the draft.
3. **Medium**: the **`medium-publish`** skill (import for canonical+backdate,
   then paste-over). Rasters must be live on the origin before the paste.
4. **HN**: submit the blog URL — never the Medium/Substack mirror (~3× worse).
   Best window is Saturday evening US (Sun 00:00–04:00 UTC); dead zone is
   weekday 04:00–12:00 UTC. Never ask anyone for upvotes — the ring detector
   buries the post and penalizes the domain. Details in `notes/hn-playbook.md`.
