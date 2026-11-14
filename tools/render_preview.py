#!/usr/bin/env python3
"""Render a 64×32 firmware layout using CircuitPython's Terminus BDF font."""

import argparse
import re
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from device.board_layout import LABEL_LAYOUT, ROW_LAYOUT, draw_small, follow_x
from device.muni_logic import arrival_pair_texts

WIDTH = 64
HEIGHT = 32


class Bitmap:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.pixels = set()

    def fill(self, color):
        self.pixels.clear()

    def __setitem__(self, pixel, value):
        if value:
            self.pixels.add(pixel)


def terminal_glyphs(path):
    glyphs = {}
    for block in path.read_text(encoding="ascii").split("STARTCHAR ")[1:]:
        encoding = re.search(r"^ENCODING (\d+)$", block, re.MULTILINE)
        if not encoding or not 32 <= int(encoding[1]) < 127:
            continue
        rows = block.split("BITMAP\n", 1)[1].split("ENDCHAR", 1)[0].splitlines()
        glyphs[chr(int(encoding[1]))] = [
            (x, y) for y, row in enumerate(rows) for x in range(6) if int(row, 16) & (128 >> x)
        ]
    return glyphs


def render(glyphs, badge, title, row_labels, arrivals):
    first, follow_first = arrival_pair_texts(arrivals[0])
    second, follow_second = arrival_pair_texts(arrivals[1])
    values = {
        "route": badge,
        "title": title,
        "in_next": first,
        "in_follow": follow_first,
        "out_next": second,
        "out_follow": follow_second,
    }
    pixels = {}
    for key, (x, y, color) in LABEL_LAYOUT.items():
        if key.endswith("_follow"):
            x = follow_x(values[key])
        for char in values[key]:
            compressed_colon = key.endswith("_next") and char == ":"
            left = x - 2 if compressed_colon else x
            for gx, gy in glyphs[char]:
                pixels[left + gx, y - 7 + gy] = color
            x += 2 if compressed_colon else 6

    for text, (x, y, color) in zip(row_labels, ROW_LAYOUT):
        bitmap = Bitmap(15, 7)
        draw_small(bitmap, text)
        for gx, gy in bitmap.pixels:
            pixels[x + gx, y + gy] = color
    return pixels


def png_chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def save_png(path, pixels, scale=16):
    # Leave a one-pixel gap around each LED and a two-LED margin outside the matrix.
    margin = 2 * scale
    gap = 2
    width = WIDTH * scale + 2 * margin
    height = HEIGHT * scale + 2 * margin
    scanlines = bytearray()
    for y in range(height):
        scanlines.append(0)
        row, dy = divmod(y - margin, scale)
        for x in range(width):
            col, dx = divmod(x - margin, scale)
            color = 0x090B0D
            if (
                0 <= row < HEIGHT
                and 0 <= col < WIDTH
                and gap <= dx < scale - gap
                and gap <= dy < scale - gap
            ):
                color = pixels.get((col, row), 0x131719)
            scanlines.extend(color.to_bytes(3, "big"))
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + png_chunk(b"IDAT", zlib.compress(scanlines, 9))
        + png_chunk(b"IEND", b"")
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("font", type=Path, help="CircuitPython tools/fonts/ter-u12n.bdf")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    glyphs = terminal_glyphs(args.font)
    pixels = render(glyphs, "38", "BUS", ("EAST", "WEST"), ([252, 960], [685, 1320]))
    save_png(args.output, pixels)


if __name__ == "__main__":
    main()
