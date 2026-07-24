"""Shared SVG-to-PNG rasterization with content-hashed filenames.

dev.to and Medium can't host SVG, and both snapshot/re-host remote images,
so rasters get a name derived from the SVG content: any change produces a
new URL, forcing the platforms to re-fetch.
"""
import hashlib
import os
import re
import subprocess

ZOOM = "4"
RASTER_REV = "3"  # bump to force new URLs when a platform has cached a bad fetch


def _flatten_css_vars(text):
    """librsvg (through 2.62) doesn't resolve CSS `var()`, so themed SVGs that
    drive every fill through custom properties render as black fallbacks. Inline
    each property's first-declared (light-theme) value and drop var() usage."""
    values = {}
    for name, val in re.findall(r"(--[A-Za-z0-9-]+)\s*:\s*([^;}]+)", text):
        values.setdefault(name, val.strip())  # first (light) declaration wins
    return re.sub(
        r"var\(\s*(--[A-Za-z0-9-]+)\s*(?:,\s*([^)]+))?\)",
        lambda m: values.get(m.group(1), m.group(2).strip() if m.group(2) else "transparent"),
        text,
    )


def _rasterize(blog_root, svg, base):
    """svg is the raw SVG bytes; base is a root-absolute path without extension
    (/uploads/slug/name). Writes a content-hashed PNG at base.<digest>.png,
    prunes stale-hash siblings, and returns the PNG's root-absolute path."""
    digest = hashlib.sha256(svg + ZOOM.encode() + RASTER_REV.encode()).hexdigest()[:8]
    png = f"{base}.{digest}.png"
    dst = blog_root + png
    if not os.path.exists(dst):
        dirname = os.path.dirname(dst)
        os.makedirs(dirname, exist_ok=True)
        name = re.escape(os.path.basename(base))
        for stale in os.listdir(dirname):
            if re.fullmatch(name + r"\.[0-9a-f]{8}\.png", stale):
                os.remove(os.path.join(dirname, stale))
        flat = _flatten_css_vars(svg.decode("utf-8", "replace")).encode()
        subprocess.run(
            ["rsvg-convert", "--zoom", ZOOM, "--background-color", "white", "-o", dst, "-"],
            input=flat, check=True,
        )
        print(f"rasterized {png} — commit and push it BEFORE the article goes live")
    return png


def png_sibling(blog_root, path):
    """path is root-absolute (/uploads/slug/x.svg); returns the PNG's path,
    generating it with rsvg-convert and pruning stale siblings if needed."""
    return _rasterize(blog_root, open(blog_root + path, "rb").read(), path[:-4])


def png_from_svg(blog_root, base, markup):
    """Rasterize inline SVG `markup` (str or bytes) to a content-hashed PNG at
    root-absolute `base` (no extension); returns the PNG's root-absolute path."""
    return _rasterize(blog_root, markup.encode() if isinstance(markup, str) else markup, base)
