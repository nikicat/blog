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
RASTER_REV = "2"  # bump to force new URLs when a platform has cached a bad fetch


def png_sibling(blog_root, path):
    """path is root-absolute (/uploads/slug/x.svg); returns the PNG's path,
    generating it with rsvg-convert and pruning stale siblings if needed."""
    svg = open(blog_root + path, "rb").read()
    digest = hashlib.sha256(svg + ZOOM.encode() + RASTER_REV.encode()).hexdigest()[:8]
    png = f"{path[:-4]}.{digest}.png"
    dst = blog_root + png
    if not os.path.exists(dst):
        dirname = os.path.dirname(dst)
        base = re.escape(os.path.basename(path)[:-4])
        for stale in os.listdir(dirname):
            if re.fullmatch(base + r"\.[0-9a-f]{8}\.png", stale):
                os.remove(os.path.join(dirname, stale))
        subprocess.run(
            ["rsvg-convert", "--zoom", ZOOM, "--background-color", "white",
             blog_root + path, "-o", dst],
            check=True,
        )
        print(f"rasterized {png} — commit and push it BEFORE the article goes live")
    return png
