#!/usr/bin/env python3
"""Verify that entry.png is a whole, valid, 1024x1024 PNG under 1 MiB.

Standard library only. This is an independent check of the committed bytes:
it does not trust draw.py or main.py, it re-derives everything from the file.

Checks, in order:
  1. size <= 1,048,576 bytes
  2. the 8-byte PNG signature
  3. a well-formed chunk stream: IHDR first, IEND last, every chunk CRC valid,
     no trailing bytes after IEND
  4. IHDR says 1024 x 1024, 8-bit, colour type 2 (truecolour RGB)
  5. the IDAT stream decompresses to exactly the byte count the header implies
     for the given filter bytes -- i.e. the pixel data is complete, not
     truncated, and every filter type is in range

On success it prints the sha256 and the byte size and exits 0; otherwise it
prints what failed and exits 1.
"""

import hashlib
import os
import struct
import sys
import zlib

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "entry.png")

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
MAX_BYTES = 1_048_576
WANT_W = WANT_H = 1024
WANT_DEPTH = 8
WANT_COLOR = 2          # truecolour RGB
CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
ALLOWED_FILTERS = set(range(5))


class BadPNG(Exception):
    pass


def check(path):
    if not os.path.isfile(path):
        raise BadPNG("%s does not exist" % path)

    size = os.path.getsize(path)
    if size > MAX_BYTES:
        raise BadPNG("%s is %d bytes, over the %d-byte limit"
                     % (path, size, MAX_BYTES))

    with open(path, "rb") as f:
        data = f.read()

    if len(data) != size:
        raise BadPNG("%s read %d bytes but stat said %d" % (path, len(data), size))
    if data[:8] != PNG_MAGIC:
        raise BadPNG("%s does not start with the PNG signature" % path)

    pos = 8
    chunks = []
    idat = []
    header = None
    while True:
        if pos + 8 > len(data):
            raise BadPNG("truncated chunk header at byte %d" % pos)
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        ctype = data[pos + 4:pos + 8]
        end = pos + 8 + length + 4
        if length > 0x7FFFFFFF:
            raise BadPNG("chunk %r at byte %d claims %d bytes"
                         % (ctype, pos, length))
        if end > len(data):
            raise BadPNG("chunk %r at byte %d overruns the file (%d > %d)"
                         % (ctype, pos, end, len(data)))

        body = data[pos + 8:pos + 8 + length]
        stored = struct.unpack(">I", data[pos + 8 + length:end])[0]
        actual = zlib.crc32(ctype + body) & 0xFFFFFFFF
        if stored != actual:
            raise BadPNG("chunk %r at byte %d has CRC %08x, computed %08x"
                         % (ctype, pos, stored, actual))

        if not chunks and ctype != b"IHDR":
            raise BadPNG("first chunk is %r, not IHDR" % ctype)
        chunks.append(ctype)
        if ctype == b"IHDR":
            if header is not None:
                raise BadPNG("more than one IHDR chunk")
            if length != 13:
                raise BadPNG("IHDR is %d bytes, expected 13" % length)
            header = struct.unpack(">IIBBBBB", body)
        elif ctype == b"IDAT":
            idat.append(body)
        elif ctype == b"IEND":
            if end != len(data):
                raise BadPNG("%d trailing bytes after IEND" % (len(data) - end))
            break
        pos = end

    if chunks[-1] != b"IEND":
        raise BadPNG("stream ends without IEND (last chunk %r)" % chunks[-1])
    if not idat:
        raise BadPNG("no IDAT chunk")

    w, h, depth, color, comp, filt, interlace = header
    if (w, h) != (WANT_W, WANT_H):
        raise BadPNG("image is %dx%d, expected %dx%d" % (w, h, WANT_W, WANT_H))
    if depth != WANT_DEPTH:
        raise BadPNG("bit depth is %d, expected %d" % (depth, WANT_DEPTH))
    if color != WANT_COLOR:
        raise BadPNG("colour type is %d, expected %d" % (color, WANT_COLOR))
    if comp != 0 or filt != 0:
        raise BadPNG("unsupported compression/filter method %d/%d" % (comp, filt))
    if interlace not in (0, 1):
        raise BadPNG("unknown interlace method %d" % interlace)

    # Decompress and confirm the pixel stream is the exact size the header
    # implies. A truncated IDAT fails here; draw.py's own save cannot produce
    # one, but the check is cheap and it is the difference between "is a PNG"
    # and "is a whole PNG".
    try:
        raw = zlib.decompress(b"".join(idat))
    except zlib.error as e:
        raise BadPNG("IDAT does not decompress: %s" % e)

    bpp = CHANNELS[color] * depth // 8
    if interlace == 0:
        stride = (w * CHANNELS[color] * depth + 7) // 8
        expected = h * (1 + stride)
        if len(raw) != expected:
            raise BadPNG("pixel stream is %d bytes, expected %d for %dx%d"
                         % (len(raw), expected, w, h))
        for row in range(h):
            ft = raw[row * (1 + stride)]
            if ft not in ALLOWED_FILTERS:
                raise BadPNG("row %d has filter type %d" % (row, ft))
    else:
        if len(raw) % h:
            raise BadPNG("interlaced stream length %d is not consistent"
                         % len(raw))

    digest = hashlib.sha256(data).hexdigest()
    return size, digest


def main():
    try:
        size, digest = check(PATH)
    except BadPNG as e:
        print("verify_png.py: FAIL: %s" % e, file=sys.stderr)
        return 1
    print("%s" % PATH)
    print("  size    %d bytes" % size)
    print("  shape   %dx%d RGB" % (WANT_W, WANT_H))
    print("  sha256  %s" % digest)
    print("  OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
