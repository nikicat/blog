# blog

Personal blog — <https://zxczxc.dev/>. Built with [Lume](https://lume.land)
(Deno) + the [simple-blog theme](https://lume.land/theme/simple-blog/), deployed to
GitHub Pages, syndicated to dev.to and Medium. The blog is the **canonical origin**;
everything else is a copy pointing back here.

## Publishing a new article

1. Create `posts/<slug>.md` (the slug becomes the permanent URL `/posts/<slug>/`):

   ```markdown
   ---
   title: "Post title"
   date: 2026-07-24
   author: Nikolay Bryskin
   description: "One-sentence summary — used as the feed item description and meta description."
   image: /uploads/<slug>/cover.png   # optional cover: hero on the post, list thumbnail, og:image, feed image, dev.to main_image
   tags:
     - linux
   ---

   Opening paragraph.

   <!--more-->

   The rest of the article. Everything above the marker is the excerpt.
   ```

2. **Images** go into `uploads/<slug>/` in this repo and are referenced root-absolute:
   `![alt](/uploads/<slug>/img.png)`. Don't hotlink to external hosts (syndicated
   copies live long) and don't hardcode full `https://zxczxc.dev/...` URLs
   (breaks if the site ever moves).

3. **Preview**: `deno task serve` → <http://localhost:3000>. Build only: `deno task build`.

4. **Publish**: commit and push to `main`. GitHub Actions builds and deploys
   (~1 min). Verify at <https://zxczxc.dev/>.

5. **Syndicate** (after the post is live):
   - **dev.to** (preferred: API) — `scripts/publish-devto.py <slug>` creates a
     dev.to *draft* with canonical URL, tags, description, and the cover as
     `main_image`; review and publish in the dev.to dashboard
     (`--update <article-id>` to push changes later). Key in
     `~/.config/devto/api_key` or `DEVTO_API_KEY`. SVG images are swapped for
     auto-generated PNG siblings (dev.to's image proxy can't serve SVG;
     requires `rsvg-convert`) — commit and push the generated PNGs before
     publishing the draft. Alternative: the RSS feed
     (`https://zxczxc.dev/feed.xml`) can be registered in dev.to Settings →
     Extensions ("mark canonical" checked) — but RSS import drops covers and
     code-fence language tags.
   - **Medium** (no API; import + paste-over): first **Import a story** at
     <https://medium.com/p/import> with the blog post URL — only the importer can
     set the canonical link and backdate, but it mangles images and code. Then run
     `scripts/medium-paste.py <slug>`, open the imported draft, `Ctrl+A`,
     `Delete`, `Ctrl+V`: the clipboard payload rebuilds the whole story from the
     built HTML — title in the title slot, cover as lead/featured image, SVG
     diagrams swapped for their PNG siblings, code blocks intact (Medium re-hosts
     the images asynchronously). Review, add topics, publish.

## How the pipeline works

- **Build**: Lume 3, config in `_config.ts`, theme and Lume pinned via the import map
  in `deno.json` (no lockfile, no node_modules). Content is `posts/*.md`, output is
  `_site/` (gitignored).
- **Deploy**: `.github/workflows/deploy.yml` — setup-deno → `deno task build` →
  upload `_site` → deploy to Pages. The repo's Pages source is set to
  **GitHub Actions** (`build_type=workflow`); don't switch it back to branch builds —
  a legacy Jekyll build of this repo produces a 404 site.
- **Feeds**: the theme emits `feed.xml` (RSS) and `feed.json` with **full article
  content** — that's what the dev.to importer consumes.

### Non-obvious bits in `_config.ts`

- **Feed subpath fix**: Lume's feed plugin builds items from pre-layout HTML, which
  the theme's `base_path` plugin never processes. Root-absolute URLs (`/uploads/...`)
  would resolve against the origin and silently lose any subpath in feed items.
  The feed `content` override prefixes them — a no-op at the current root domain,
  kept so a future move under a path can't silently break feed images again.
- **`feedContent` front matter**: when a post defines it, the feed serves that HTML
  instead of the page content. Used by interactive posts (below).
- **Domain**: `location` is `https://zxczxc.dev/`, served via the Pages custom
  domain on this repo. DNS is on Cloudflare: apex + `www` CNAME to
  `nikicat.github.io`, **DNS-only** (proxying breaks GitHub's cert issuance).
  Old `nikicat.github.io/blog/*` URLs 301-redirect. If the domain ever changes,
  remember canonical URLs on dev.to/Medium **freeze at publish time** — copies
  syndicated before a move keep pointing at the old URLs.

## Cover images

The `image:` front matter drives everything: hero under the post title, floated
thumbnail on the home/archive lists, `og:image`, the feed item image, and
dev.to's `main_image` (via the publish script). Medium picks it up as the
featured image because the hero is part of the article body. Implemented by
locally-shadowed theme templates (`_includes/layouts/post.vto`,
`_includes/templates/post-list.vto`, `index.vto`) plus CSS in `_data.yml`
`extra_head` — **shadowed files freeze their copy of the theme**: after a theme
version bump in `deno.json`, re-diff them against upstream.

## Interactive / raw-HTML posts

`posts/kilobyte-utxo-set.vto` is a verbatim copy of the standalone interactive page
([nikicat/kilobyte-utxo-set](https://github.com/nikicat/kilobyte-utxo-set)) with a
front matter block on top. Recipe for this kind of post:

- Use a `.vto` file with the raw HTML as the body — plain `.html` files are **not**
  loaded as pages by Lume. Safe as long as the HTML contains no `{{`.
- `layout:` (empty value) skips the theme layout, so the page ships its own design.
  Consequences you must handle manually:
  - inject the Umami `<script>` tag into its `<head>` (no layout ⇒ no `extra_head`);
  - stub `readingInfo: { minutes: N, words: N }` — the reading-time plugin only
    processes markdown, and the post-list template requires it;
  - set `feedContent:` with a teaser so the feed doesn't ship the whole app HTML.
- The copy does not track its source repo. To resync: fetch the deployed page,
  re-prepend the front matter block (`git show` this file for the exact shape).

## Importing articles from dev.to

`scripts/import-devto.py <article-id> <slug>` converts a dev.to article into a post:
fetches `body_markdown` from the public API, strips dev.to front matter, converts
`{% details %}` liquid tags to `<details>`, downloads every referenced image (and the
cover) into `uploads/<slug>/`, rewrites the references root-absolute, and writes
`posts/<slug>.md`. Review the result — particularly the `<!--more-->` placement.

## Analytics

Self-hosted [Umami](https://umami.is): dashboard at <https://nikicat-umami.fly.dev>
(fly.io apps `nikicat-umami` + `nikicat-umami-db`, region `arn`; fly config in
`~/src/umami-fly/`, admin credentials in `~/.config/umami-fly-credentials`). The
tracker tag is injected on every themed page via `extra_head` in `_data.yml`.
A barely-visible "stats" link to the dashboard sits in the page footer
(shadowed `_includes/layouts/base.vto`, styled via `extra_head`).
The fly machine suspends when idle — the first visit after a quiet period wakes it
(~1 s), so very short cold visits may go uncounted. dev.to and Medium copies have
their own native stats; Umami only sees the origin.
