"""Crop the twelve 1344x768 grid scenes down to tile-left strips.

The featured crops were a pure 2:1 downscale because source and target
shared an aspect ratio. The grid strips do not: sources are 1344x768
(7:4, landscape) and the tile-left strip is nearly square, so we take a
full-height vertical slice out of the middle of each scene and downscale.

Saved at 2x the draw-time size (152x118) so draw.py can do the final
LANCZOS step from a little more data than it needs.
"""

from PIL import Image

SRC_H = 768
STRIP_W = 152          # 2x the 76px draw-time width
STRIP_H = 118          # 2x the 59px draw-time height

for n in range(4, 16):
    src = "assets/g%02d.png" % n
    dst = "assets/s%02d.jpg" % n
    im = Image.open(src).convert("RGB")
    w, h = im.size

    # Slice width that keeps the strip's aspect at full source height.
    slice_w = int(round(h * (STRIP_W / STRIP_H)))
    if slice_w > w:
        slice_w = w
    left = (w - slice_w) // 2
    im = im.crop((left, 0, left + slice_w, h))

    # Trim to the exact strip aspect before the downscale.
    tw, th = STRIP_W, STRIP_H
    tgt = tw / th
    w2, h2 = im.size
    if w2 / h2 > tgt:
        nw = int(round(h2 * tgt))
        x = (w2 - nw) // 2
        im = im.crop((x, 0, x + nw, h2))
    else:
        nh = int(round(w2 / tgt))
        y = (h2 - nh) // 2
        im = im.crop((0, y, w2, y + nh))

    im = im.resize((tw, th), Image.LANCZOS)
    im.save(dst, "JPEG", quality=92, optimize=True, progressive=False)
    print("%s -> %s  slice=%dpx  %d bytes" % (src, dst, slice_w, __import__("os").path.getsize(dst)))
