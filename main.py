#!/usr/bin/env python3
"""Deploy the bundled entry.png into the grader's output directory.

Standard library only; runs on Python 3.13.

The image is not re-rendered here. The bytes committed as entry.png beside
this file are the entry, and this script's only job is to put them where the
grader looks for them, intact, with the mode the grader needs to read them.

Deployment rules
----------------
* Destination directory is $MAKEFUN_OUTPUT_DIR, default /output. Created if
  missing.
* Writes go to a temp file created *in the destination directory* (same
  filesystem, so the final rename is atomic) and are renamed into place with
  os.replace, so no reader ever sees a half-written PNG.
* mkstemp creates the file 0600. The grader reads as another user, so the
  staged file is chmodded 0644 before the rename: the mode travels with the
  inode across os.replace.
* The PNG magic bytes and the byte size (<= 1,048,576) are checked on the
  source before the copy and on the staged file after it. A mismatch aborts
  with a non-zero exit rather than deploying bad bytes.
"""

import os
import sys
import shutil
import tempfile

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
MAX_BYTES = 1_048_576
OUTPUT_NAME = "entry.png"
DEFAULT_OUTPUT_DIR = "/output"
FILE_MODE = 0o644

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, "entry.png")


class DeployError(Exception):
    """Any condition that must stop the deploy."""


def fail(msg, code=1):
    print("main.py: %s" % msg, file=sys.stderr)
    return code


def check_png(path, label):
    """Return the file size after confirming it is a whole, small PNG.

    `whole` here means: starts with the 8-byte PNG signature and ends with a
    complete IEND chunk. That catches truncation and a stray prefix, which a
    magic-byte test alone would let through.
    """
    try:
        size = os.path.getsize(path)
    except OSError as e:
        raise DeployError("cannot stat %s %s: %s" % (label, path, e))

    if size > MAX_BYTES:
        raise DeployError(
            "%s %s is %d bytes, over the %d-byte limit"
            % (label, path, size, MAX_BYTES))
    if size < len(PNG_MAGIC) + 12:
        raise DeployError(
            "%s %s is only %d bytes, too short to be a PNG"
            % (label, path, size))

    try:
        with open(path, "rb") as f:
            head = f.read(len(PNG_MAGIC))
            if head != PNG_MAGIC:
                raise DeployError(
                    "%s %s does not start with the PNG signature (got %r)"
                    % (label, path, head))
            f.seek(-12, os.SEEK_END)
            tail = f.read(12)
    except OSError as e:
        raise DeployError("cannot read %s %s: %s" % (label, path, e))

    # last 12 bytes of a PNG: length(0) + "IEND" + CRC
    if tail[4:8] != b"IEND":
        raise DeployError(
            "%s %s does not end with a complete IEND chunk (got %r)"
            % (label, path, tail))

    return size


def deploy():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or DEFAULT_OUTPUT_DIR

    if not os.path.isfile(SOURCE):
        raise DeployError("bundled image is missing: %s" % SOURCE)

    src_size = check_png(SOURCE, "source")

    try:
        os.makedirs(out_dir, exist_ok=True)
    except OSError as e:
        raise DeployError("cannot create output directory %s: %s" % (out_dir, e))

    if not os.path.isdir(out_dir):
        raise DeployError("output path %s is not a directory" % out_dir)

    dest = os.path.join(out_dir, OUTPUT_NAME)

    fd = None
    staged = None
    try:
        fd, staged = tempfile.mkstemp(
            prefix=".entry-", suffix=".png.tmp", dir=out_dir)
        with os.fdopen(fd, "wb") as out:
            fd = None
            with open(SOURCE, "rb") as src:
                shutil.copyfileobj(src, out, 1 << 16)
            out.flush()
            os.fsync(out.fileno())

        # mkstemp made it 0600; the grader reads as another user.
        os.chmod(staged, FILE_MODE)

        dst_size = check_png(staged, "staged copy")
        if dst_size != src_size:
            raise DeployError(
                "size changed during copy: source %d bytes, staged %d bytes"
                % (src_size, dst_size))

        os.replace(staged, dest)
        staged = None
    finally:
        if fd is not None:
            os.close(fd)
        if staged is not None:
            try:
                os.unlink(staged)
            except OSError:
                pass

    # The rename is atomic, but the destination is what the grader reads, so
    # check it once more rather than trusting the intermediate state.
    final_size = check_png(dest, "deployed image")
    mode = os.stat(dest).st_mode & 0o777
    if mode != FILE_MODE:
        raise DeployError(
            "deployed image has mode %04o, expected %04o" % (mode, FILE_MODE))
    if final_size != src_size:
        raise DeployError(
            "deployed image is %d bytes, source was %d" % (final_size, src_size))

    print("main.py: deployed %s -> %s (%d bytes, mode %04o)"
          % (SOURCE, dest, final_size, mode))
    return 0


def main():
    try:
        return deploy()
    except DeployError as e:
        return fail(str(e))
    except OSError as e:
        return fail("deploy failed: %s" % e)


if __name__ == "__main__":
    sys.exit(main())
