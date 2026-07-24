#!/usr/bin/env python3
"""Import a dev.to article as a blog post.

Usage: scripts/import-devto.py <article-id> <slug>

Fetches the article from the public dev.to API, localizes images into
uploads/<slug>/, converts {% details %} liquid tags, and writes posts/<slug>.md.
Find the article id via https://dev.to/api/articles?username=<user>.
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request

BLOG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def fetch(url, dest=None):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as r:
        data = r.read()
    if dest:
        with open(dest, "wb") as f:
            f.write(data)
    return data


def main(art_id, slug):
    a = json.loads(fetch(f"https://dev.to/api/articles/{art_id}"))
    body = a["body_markdown"]

    # strip dev.to front matter if the body carries one (v1 editor articles)
    description = a.get("description", "")
    m = re.match(r"^---\n.*?\n---\n", body, re.S)
    if m:
        dm = re.search(r"^description:\s*(.+)$", m.group(0), re.M)
        if dm:
            description = dm.group(1).strip().strip('"')
        body = body[m.end():]
    body = body.lstrip("\n")

    body = re.sub(r"\{%\s*details\s+(.*?)\s*%\}", r"<details>\n<summary>\1</summary>\n", body)
    body = re.sub(r"\{%\s*enddetails\s*%\}", "</details>", body)

    updir = f"{BLOG}/uploads/{slug}"
    os.makedirs(updir, exist_ok=True)

    def localize(mm):
        alt, url = mm.group(1), mm.group(2)
        fname = urllib.parse.urlparse(url).path.split("/")[-1]
        fetch(url, f"{updir}/{fname}")
        return f"![{alt}](/uploads/{slug}/{fname})"

    body = re.sub(r"!\[([^\]]*)\]\((https?://[^)\s]+)\)", localize, body)

    # cover: decode the media2.dev.to dynamic-image URL back to the raw object
    image_line = ""
    cover = a.get("cover_image")
    if cover:
        raw = "http" + urllib.parse.unquote(cover.split("/http")[-1])
        fname = "cover-" + urllib.parse.urlparse(raw).path.split("/")[-1]
        fetch(raw, f"{updir}/{fname}")
        image_line = f"image: /uploads/{slug}/{fname}\n"

    # excerpt marker after the first plain paragraph
    blocks = body.split("\n\n")
    for i, b in enumerate(blocks):
        s = b.strip()
        if s and not s.startswith((">", "#", "!", "<", "```", "|")):
            blocks.insert(i + 1, "<!--more-->")
            break
    body = "\n\n".join(blocks)

    tags = a.get("tag_list") or a.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    tag_lines = "".join(f"  - {t}\n" for t in tags)

    title = a["title"].replace('"', '\\"')
    desc = description.replace('"', '\\"')
    post = (
        f'---\ntitle: "{title}"\ndate: {a["published_at"][:10]}\nauthor: Nikolay Bryskin\n'
        f'description: "{desc}"\n{image_line}tags:\n{tag_lines}---\n\n{body}'
    )
    out = f"{BLOG}/posts/{slug}.md"
    with open(out, "w") as f:
        f.write(post)
    print(f"wrote {out}\nimages: {sorted(os.listdir(updir)) or 'none'}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit((__doc__ or "").strip())
    main(sys.argv[1], sys.argv[2])
