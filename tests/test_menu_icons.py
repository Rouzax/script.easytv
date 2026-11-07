"""
Tests for the menu icons shipped in resources/icons/menu/.

Skins tint these icons with colordiffuse and draw them beside their own
extras/icons set, so every file must match that set's format: 128x128 RGBA,
white only, with the glyph's longer side spanning the centred 64 pixels
(32..95). A coloured pixel shows through the tint and an off-size glyph looks
larger or smaller than its neighbours in the menu. The PNGs are decoded with
the standard library so the check needs no imaging dependency.
"""
import os
import struct
import zlib

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MENU_DIR = os.path.join(REPO_ROOT, 'resources', 'icons', 'menu')
ICONS = sorted(f for f in os.listdir(MENU_DIR) if f.endswith('.png'))


def _read_rgba(path):
    """Decode an 8-bit RGBA, non-interlaced PNG into (width, height, rows)."""
    with open(path, 'rb') as handle:
        data = handle.read()
    assert data[:8] == b'\x89PNG\r\n\x1a\n', 'not a PNG'
    pos, idat, header = 8, b'', None
    while pos < len(data):
        length, kind = struct.unpack('>I4s', data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        if kind == b'IHDR':
            header = struct.unpack('>IIBBBBB', body)
        elif kind == b'IDAT':
            idat += body
        pos += 12 + length
    width, height, depth, colour, _, _, interlace = header
    assert (depth, colour, interlace) == (8, 6, 0), 'expected 8-bit RGBA, not interlaced'

    raw, stride, bpp = zlib.decompress(idat), width * 4, 4
    rows, prev = [], bytearray(stride)
    for y in range(height):
        start = y * (stride + 1)
        kind, line = raw[start], bytearray(raw[start + 1:start + 1 + stride])
        for i in range(stride):
            a = line[i - bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i - bpp] if i >= bpp else 0
            if kind == 1:
                line[i] = (line[i] + a) & 0xFF
            elif kind == 2:
                line[i] = (line[i] + b) & 0xFF
            elif kind == 3:
                line[i] = (line[i] + (a + b) // 2) & 0xFF
            elif kind == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pred = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                line[i] = (line[i] + pred) & 0xFF
        rows.append(line)
        prev = line
    return width, height, rows


def test_menu_icons_exist():
    """Guards the parametrised tests: an empty folder would check nothing."""
    assert ICONS, f'No menu icons found in {MENU_DIR}'


def test_third_party_license_ships_with_icons():
    """The icons are built from Tabler Icons, whose MIT licence must ship with them."""
    path = os.path.join(MENU_DIR, 'LICENSE-tabler-icons.txt')
    with open(path, encoding='utf-8') as handle:
        assert 'MIT License' in handle.read()


@pytest.mark.parametrize('name', ICONS)
def test_menu_icon_matches_skin_icon_format(name):
    width, height, rows = _read_rgba(os.path.join(MENU_DIR, name))
    assert (width, height) == (128, 128)

    coloured, xs, ys = [], [], []
    for y, line in enumerate(rows):
        for x in range(width):
            r, g, b, alpha = line[x * 4:x * 4 + 4]
            if alpha == 0:
                continue
            if (r, g, b) != (255, 255, 255):
                coloured.append((x, y))
            if alpha > 8:
                xs.append(x)
                ys.append(y)
    assert not coloured, f'{len(coloured)} visible pixels are not white, first at {coloured[0]}'

    left, right, top, bottom = min(xs), max(xs), min(ys), max(ys)
    assert left >= 32 and top >= 32 and right <= 95 and bottom <= 95, (
        f'glyph spans x {left}..{right}, y {top}..{bottom}; must stay inside 32..95'
    )
    assert right - left == 63 or bottom - top == 63, (
        f'glyph spans x {left}..{right}, y {top}..{bottom}; its longer side must fill 32..95'
    )
