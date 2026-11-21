#!/usr/bin/env python3
"""
Passport of Velmora — entry program.

The Republic of Velmora is a small lighthouse-keeping archipelago state.
Its passport spread (data page on the left, visa page on the right) is a
finished piece of artwork, rendered once and committed beside this file
as ``entry.png``; the renderer lives in ``draw.py`` for provenance and is
never imported here.

This program is the graded deliverable, so it depends on nothing but the
Python standard library: it validates the committed PNG against the
competition gate (signature, 1024x728 IHDR dimensions, at most 1 MiB),
copies it byte for byte to the output location, and reads the copy back
to prove the bytes on disk are the bytes that were validated.
"""

import os
import struct
import sys

# ---------------------------------------------------------------------------
# The gate, as numbers. The spread is one fixed image: if the committed
# file ever drifts from these values the entry is invalid, so fail loudly
# here rather than hand the grader a bad file.
# ---------------------------------------------------------------------------
EXPECTED_WIDTH = 1024
EXPECTED_HEIGHT = 728
MAX_BYTES = 1_048_576
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
IMAGE_NAME = "entry.png"


def output_dir(argv):
    """Where the grader wants the file: explicit argument first, then the
    MAKEFUN_OUTPUT_DIR environment variable, then the /output default."""
    if len(argv) > 1:
        return argv[1]
    return os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")


def check_png(blob):
    """Raise ValueError unless blob is the exact spread the gate expects."""
    if len(blob) > MAX_BYTES:
        raise ValueError(f"entry.png is {len(blob)} bytes, over the 1 MiB cap")
    if not blob.startswith(PNG_SIGNATURE):
        raise ValueError("entry.png does not start with the PNG signature")
    # The IHDR chunk follows the 8-byte signature: 4 bytes of length, the
    # four letters IHDR, then width and height as big-endian uint32.
    if blob[12:16] != b"IHDR":
        raise ValueError("first PNG chunk is not IHDR")
    width, height = struct.unpack(">II", blob[16:24])
    if (width, height) != (EXPECTED_WIDTH, EXPECTED_HEIGHT):
        raise ValueError(
            f"entry.png is {width}x{height}, expected "
            f"{EXPECTED_WIDTH}x{EXPECTED_HEIGHT}"
        )
    # A complete PNG ends with the IEND chunk: zero length, the letters
    # IEND, and its CRC. Header checks alone would wave a truncated file
    # through, so insist on the trailer too.
    if blob[-12:-8] != b"\x00\x00\x00\x00" or blob[-8:-4] != b"IEND":
        raise ValueError("entry.png does not end with the IEND chunk")


def main(argv):
    here = os.path.dirname(os.path.abspath(__file__))
    source = os.path.join(here, IMAGE_NAME)
    with open(source, "rb") as fh:
        blob = fh.read()
    check_png(blob)

    target_dir = output_dir(argv)
    os.makedirs(target_dir, exist_ok=True)
    target = os.path.join(target_dir, IMAGE_NAME)
    with open(target, "wb") as fh:
        fh.write(blob)

    # Read-back: the file the grader scores must be the file we validated,
    # not whatever the filesystem felt like keeping.
    with open(target, "rb") as fh:
        written = fh.read()
    if written != blob:
        raise ValueError("read-back of the copied entry.png differs")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
