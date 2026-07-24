---
name: medium-publish
description: >-
  Publish (cross-post) a blog post to Medium by driving the user's real Brave
  browser through the Playwright MCP extension bridge. Builds the site, prepares
  paste-ready HTML with scripts/medium-paste.py (rasterizing SVG diagrams to
  hosted PNGs), imports the post so Medium sets the canonical link + backdate,
  wipes the imported body and pastes the clean version, sets topics from the
  post's front matter, and publishes. Use when asked to publish, cross-post, or
  "put on Medium" a post in this blog.
---

# Publish a post to Medium (via Playwright + Brave)

Cross-post `posts/<slug>.md` to Medium. Two-stage flow: **import** (only Medium's
importer can set the canonical link back to the blog and backdate the story) then
**paste** (the importer mangles images, code, and diagrams; a prepared HTML paste
does not). The post stays the SEO original on `zxczxc.dev`.

## Prerequisites

- The **`playwright-brave`** MCP server is connected and its `mcp__playwright-brave__*`
  tools are loaded (extension mode → the user's real Brave, already logged into
  Medium). If missing, see "playwright-brave setup" at the bottom.
- CLI tools present: `wl-copy`, `wl-paste`, `rsvg-convert` (all used by the prep script).
- The post exists at `posts/<slug>.md` with `title`, `date`, `image`, and `tags` front matter.

## Procedure

1. **Build** so the prep script reads current HTML:
   `deno task build` (regenerates `_site/posts/<slug>/index.html`).

2. **Prepare the clipboard + rasters:** `python3 scripts/medium-paste.py <slug>`.
   It rasterizes every diagram (inline `<svg>` and `![](x.svg)`) to a content-hashed
   PNG under `uploads/<slug>/`, rewrites images to absolute `https://zxczxc.dev/...`
   URLs, and copies title + cover + body to the clipboard as `text/html`.

3. **If it (re)generated a PNG** (it prints `rasterized … — commit and push it
   BEFORE the article goes live`), the image MUST be live before pasting — Medium
   fetches remote image URLs on paste and **rejects data-URIs and clipboard images**.
   - Commit the new raster (+ any script changes) and `git push origin main`.
   - Wait for the GitHub Pages deploy: poll the raster URL until HTTP 200 (run the
     poll `run_in_background`, ~10s interval; deploy is usually <1 min).
   - Re-run `scripts/medium-paste.py <slug>` to refresh the clipboard once images are live.

4. **Import** (canonical + date): navigate Brave to `https://medium.com/p/import`.
   Snapshot, then **type** `https://zxczxc.dev/posts/<slug>/` into the URL field
   char-by-char (`browser_type` slowly / pressSequentially) — a plain `fill()` does
   not register with Medium's React form and the Import button won't advance. Click
   **Import**; it lands on `/p/<id>/edit`.

5. **Replace the imported body with the prepared paste:**
   - Dismiss the import onboarding overlay (click **"See your story"**) — it
     intercepts clicks otherwise.
   - Click into the body, then `ControlOrMeta+a`, `Delete`, `ControlOrMeta+v`.
   - Wait ~5s for Medium to fetch the remote images.
   - Verify with `browser_find`: cover, screenshot(s), and each diagram appear as
     `figure` nodes at the right spots. If an **"Uh oh! Something went wrong
     uploading the image"** dialog shows, click **OK** (it comes from a bad
     data-URI/clipboard paste — never paste those).

6. **Topics + publish:**
   - Click **Publish** (top-right) → the submission page.
   - For each tag in the post's `tags:` front matter: type it into the topic
     combobox, then `ArrowDown` + `Enter` to select the suggested topic (verify a
     "Remove <Topic>" chip appears).
   - ⚠️ **A stray Enter in the topic field can trigger the page's default Publish
     button and publish immediately.** After the last topic, do not press extra Enters.
   - **STOP. Get explicit user confirmation before clicking the final "Publish"** —
     it is public and hard to undo. On yes, click **Publish**. To keep it a draft,
     click the **close (X)** to return to the editor (draft auto-saves).

## Gotchas (learned the hard way)

- **Only remote http(s) image URLs survive the paste.** Medium re-hosts them;
  data-URI `<img>` and `image/png` clipboard pastes are dropped. So diagrams must be
  deployed to `zxczxc.dev` first (step 3).
- **librsvg (rsvg-convert) ignores CSS `var()`** → theme-driven SVGs rasterize to
  solid black boxes. `rasterize.py` flattens `var()` to each property's first
  (light-theme) value. It also sources inline SVG from the **markdown**, because
  Lume's HTML build lowercases `viewBox`/`markerWidth`, which rsvg (case-sensitive)
  then ignores. If a raster looks wrong, bump `RASTER_REV` in `rasterize.py` to force
  a fresh URL (platforms negatively-cache a bad fetch).
- **Import URL field:** type it, don't `fill()` it.
- **Callouts** (`> [!NOTE]`) paste as plain paragraphs with a stray "Note" line, not
  boxed — cosmetic; leave unless asked.
- Write any screenshots to a temp/scratch dir, not the repo root (`.playwright-mcp/`
  is gitignored; ad-hoc PNGs are not).

## playwright-brave setup (one-time, already done on this machine)

Extension mode bridges to the user's real Brave (Brave installs the "Playwright MCP
Bridge" extension from the Chrome Web Store). Registered at user scope as:

```
claude mcp add playwright-brave -s user \
  -e PWTEST_EXTENSION_USER_DATA_DIR=/home/nb/.config/BraveSoftware/Brave-Browser \
  -- npx @playwright/mcp@latest --extension --executable-path /opt/brave-bin/brave
```

`--executable-path` (Brave binary) both skips the Chrome-profile preflight and is
the browser the relay spawns to open its `connect.html`; the env var points the
extension check at Brave's profile. The first tool call after a (re)start reopens
the connect handshake in Brave.
