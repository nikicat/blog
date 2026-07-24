#!/usr/bin/env python3
"""Publish or update a blog post on dev.to via the API.

Usage:
  scripts/publish-devto.py <slug>                 # create as dev.to DRAFT
  scripts/publish-devto.py <slug> --update <id>   # update existing article

Reads posts/<slug>.md, sends it with canonical_url pointing at the blog and
main_image set from the `image` front matter (as an absolute URL). Articles are
created unpublished — review and publish them in the dev.to dashboard.

API key: ~/.config/devto/api_key or DEVTO_API_KEY env
(generate at https://dev.to/settings/extensions).
"""
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

BLOG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIGIN = "https://zxczxc.dev"


def api_key():
    key = os.environ.get("DEVTO_API_KEY")
    if not key:
        path = os.path.expanduser("~/.config/devto/api_key")
        if os.path.exists(path):
            key = open(path).read().strip()
    if not key:
        sys.exit("no API key: set DEVTO_API_KEY or write ~/.config/devto/api_key")
    return key


def parse_post(slug):
    src = open(f"{BLOG}/posts/{slug}.md").read()
    m = re.match(r"^---\n(.*?)\n---\n", src, re.S)
    if not m:
        sys.exit("post has no front matter")
    fm, body = m.group(1), src[m.end():].strip()

    def field(name):
        fmatch = re.search(rf'^{name}:\s*"?(.*?)"?\s*$', fm, re.M)
        return fmatch.group(1) if fmatch else None

    tags = re.findall(r"^  - (\S+)$", fm, re.M)
    body = body.replace("<!--more-->\n\n", "").replace("<!--more-->", "")

    # dev.to's image proxy can't serve SVG — swap in a PNG sibling,
    # generating it with rsvg-convert when missing or stale
    def png_sibling(path):
        png = path[:-4] + ".png"
        src, dst = BLOG + path, BLOG + png
        if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(src):
            subprocess.run(
                ["rsvg-convert", "--zoom", "2", "--background-color", "white", src, "-o", dst],
                check=True,
            )
            print(f"rasterized {png} — commit and push it before the article goes live")
        return png

    # dev.to needs absolute image URLs
    def img_ref(m):
        alt, path = m.group(1), m.group(2)
        if path.endswith(".svg"):
            path = png_sibling(path)
        return f"{alt}({ORIGIN}{path})"

    body = re.sub(r"(!\[[^\]]*\])\((/[^)\s]+)\)", img_ref, body)

    article = {
        "title": field("title"),
        "body_markdown": body,
        "published": False,
        "canonical_url": f"{ORIGIN}/posts/{slug}/",
        # dev.to allows max 4 tags, lowercase alphanumeric
        "tags": [re.sub(r"[^a-z0-9]", "", t.lower()) for t in tags][:4],
    }
    description = field("description")
    if description:
        article["description"] = description
    image = field("image")
    if image:
        article["main_image"] = ORIGIN + image
    return article


def main():
    args = sys.argv[1:]
    if not args or len(args) not in (1, 3):
        sys.exit((__doc__ or "").strip())
    slug = args[0]
    update_id = args[2] if len(args) == 3 and args[1] == "--update" else None

    article = parse_post(slug)
    if update_id:
        # never touch the published state of an existing article
        del article["published"]
    payload = json.dumps({"article": article}).encode()
    url = "https://dev.to/api/articles" + (f"/{update_id}" if update_id else "")
    req = urllib.request.Request(
        url,
        data=payload,
        method="PUT" if update_id else "POST",
        headers={
            "api-key": api_key(),
            "Content-Type": "application/json",
            # dev.to 403s the default Python-urllib user agent
            "User-Agent": "zxczxc.dev publish script",
        },
    )
    try:
        with urllib.request.urlopen(req) as r:
            a = json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"dev.to API {e.code}: {e.read().decode()[:300]}")
    state = "updated" if update_id else "created draft"
    print(f"{state}: id={a['id']} url={a['url']}")
    if not update_id:
        print("review & publish: https://dev.to/dashboard")


if __name__ == "__main__":
    main()
