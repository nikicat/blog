#!/usr/bin/env python3
"""Build Medium paste-ready HTML for a post and put it on the clipboard.

Usage: scripts/medium-paste.py <slug>

Medium flow (its importer mangles images and code, but only it can set the
canonical link and backdate):
  1. Import the post at https://medium.com/p/import with its blog URL.
  2. Run this script, open the imported draft, Ctrl+A, Delete, Ctrl+V.
     Title lands in the title slot, the cover becomes the lead/featured
     image, diagrams arrive as PNGs, code blocks stay code blocks.
  3. Review, add topics, publish.
"""
import os
import re
import subprocess
import sys

BLOG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIGIN = "https://zxczxc.dev"
sys.path.insert(0, os.path.join(BLOG, "scripts"))
from rasterize import png_sibling  # type: ignore  # noqa: E402


def main(slug):
    fm = open(f"{BLOG}/posts/{slug}.md").read()
    tmatch = re.search(r'^title:\s*"?(.*?)"?\s*$', fm, re.M)
    if not tmatch:
        sys.exit("post has no title front matter")
    imatch = re.search(r"^image:\s*(\S+)", fm, re.M)

    built = f"{BLOG}/_site/posts/{slug}/index.html"
    if not os.path.exists(built):
        sys.exit(f"{built} missing — run `deno task build` first")
    html = open(built).read()
    start = html.index('<div class="post-body body">')
    body = html[start + len('<div class="post-body body">'):html.index("</article>", start)]
    body = body.rsplit("</div>", 1)[0]

    body = re.sub(
        r'src="(/[^"]+\.svg)"',
        lambda m: f'src="{ORIGIN}{png_sibling(BLOG, m.group(1))}"',
        body,
    )
    body = re.sub(r'src="/', f'src="{ORIGIN}/', body)
    body = re.sub(r'<a href="[^"]*" class="header-anchor">(.*?)</a>', r"\1", body, flags=re.S)

    cover = f'<img src="{ORIGIN}{imatch.group(1)}">\n' if imatch else ""
    payload = f"<h1>{tmatch.group(1)}</h1>\n{cover}{body}"

    env = dict(os.environ)
    env.setdefault("WAYLAND_DISPLAY", "wayland-1")
    subprocess.run(["wl-copy", "--type", "text/html"],
                   input=payload.encode(), env=env, check=True)
    print(f"copied {len(payload)} bytes to clipboard")
    print(f"1. import first (canonical+date): https://medium.com/p/import ← {ORIGIN}/posts/{slug}/")
    print("2. open the imported draft, Ctrl+A, Delete, Ctrl+V")
    print("3. review images/code blocks, add topics, publish")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit((__doc__ or "").strip())
    main(sys.argv[1])
