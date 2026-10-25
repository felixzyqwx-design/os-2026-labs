#!/usr/bin/env python3
"""Typeset two report figures from checked-in results (requires Pillow).

These are result excerpts, not terminal screenshots. Run from any directory.
Use --font to override the default Windows/Linux monospace font.
"""
import argparse
import json
from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageFont

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--font', type=Path)
args = parser.parse_args()
report = Path(__file__).resolve().parents[1]
evidence = report / 'evidence'
out = report / 'images'
out.mkdir(exist_ok=True)
fonts = [args.font] if args.font else [
    Path('C:/Windows/Fonts/consola.ttf'),
    Path('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'),
]
font_path = next((p for p in fonts if p.is_file()), None)
if font_path is None:
    parser.error('No monospace font found; provide --font PATH')
body = ImageFont.truetype(str(font_path), 29)
heading = ImageFont.truetype(str(font_path), 33)
small = ImageFont.truetype(str(font_path), 24)
width = 1400
margin = 42


def text(draw, xy, value, font=body, right=width - margin):
    if draw.textbbox(xy, value, font=font)[2] > right:
        raise ValueError('Text exceeds figure width: ' + value)
    draw.text(xy, value, font=font, fill='#171717')


def read(name):
    return (evidence / name).read_text(encoding='utf-8')


rows = json.loads(read('2026-10-25-mmu-host-summary.json'))
assert len(rows) == 8
guest = read('2026-10-25-mmu-guest-gdb.txt')
canvas = Image.new('RGB', (width, 910), 'white')
d = ImageDraw.Draw(canvas)
text(d, (margin, 28), 'QEMU 8.2.2 / TCI / dual GDB / 2026-10-25', heading)
col_width = 642
for col, mode in enumerate(('Bare', 'Sv39')):
    x = margin + col * 674
    edge = x + col_width
    group = [r for r in rows if r['mode'] == mode]
    first, translation, fill, second = group
    assert first['kind'] == second['kind'] == 'lookup'
    assert first['hit'] is False and second['hit'] is True
    assert translation['pa'] == fill['pa'] == '0x81004000'
    assert fill['size'] == 4096
    assert mode + ' LOADS VERIFIED: t0=t2=0x1122334455667788' in guest
    d.rectangle((x - 10, 96, edge, 782), outline='#777777', width=1)
    d.rectangle((x - 10, 96, edge, 156), fill='#eeeeee', outline='#777777')
    text(d, (x + 8, 109), mode, heading, edge - 8)
    lines = [
        'VA   ' + translation['va'],
        'PA   ' + translation['pa'],
        'satp ' + translation['satp'],
        '',
        '1. lookup: MISS',
        'tag ' + first['tag'],
    ]
    if translation['page_walk']:
        assert translation['walked_entries'] == 1
        assert translation['leaf_size'] == 1 << 30
        lines += [
            '2. root ' + translation['root_pa'],
            'PTE @ ' + translation['pte_pa'],
            'PTE = ' + translation['pte'],
            '1 GiB leaf; 1 PTE read',
        ]
    else:
        lines += ['2. PA = VA; no page walk', '', '', '']
    lines += ['', '3. fill: ' + str(fill['size']) + ' bytes',
              '4. lookup: HIT', 'tag ' + second['tag']]
    for line_no, line in enumerate(lines):
        text(d, (x + 8, 174 + line_no * 37), line, body, edge - 8)
text(d, (margin, 810), 'Both loads: t0 = t2 = 0x1122334455667788')
text(d, (margin, 860), 'Source: mmu-host-summary.json + mmu-guest-gdb.txt', small)
canvas.save(out / '01-mmu-tlb.png')

default = read('2026-10-25-regression-boot-default.txt')
buddy = read('2026-10-25-regression-boot-buddy.txt')
grade = read('2026-10-25-regression-grade.txt')
kernel_grade = read('2026-10-25-regression-grade-kernel.txt')
for marker in ('[Test 1] Page Init: PASS', '[Test 2] Best-Fit: PASS'):
    assert marker in kernel_grade
assert 'Total Score: 20/20' in grade
canvas = Image.new('RGB', (width, 910), 'white')
d = ImageDraw.Draw(canvas)
text(d, (margin, 28), 'WSL / system QEMU 8.2.2 / 2026-10-25', heading)
y = 103
for title, content in [('Default Best-Fit / 128 MiB', default),
                       ('Buddy / 128 MiB', buddy)]:
    manager = re.search(r'^memory management: .*$', content, re.M)[0]
    mapping = re.search(r'physical memory map: (.*), free: (.*)', content)
    assert mapping and 'check_alloc_page() succeeded!' in content
    d.rectangle((margin - 10, y - 8, width - margin, y + 39), fill='#eeeeee')
    text(d, (margin, y), title, heading)
    y += 58
    lines = [manager, 'RAM  ' + mapping[1], 'free ' + mapping[2]]
    if 'buddy checks:' in content:
        lines.append(re.search(r'^buddy checks: .*$', content, re.M)[0])
    lines.append('check_alloc_page() succeeded!')
    for line in lines:
        text(d, (margin, y), line)
        y += 39
    y += 31
d.rectangle((margin - 10, y - 8, width - margin, y + 39), fill='#eeeeee')
text(d, (margin, y), 'Course tests / Page Init + Best-Fit', heading)
y += 60
for marker in ('[Test 1] Page Init: PASS', '[Test 2] Best-Fit: PASS',
               'Total Score: 20/20'):
    text(d, (margin, y), marker)
    y += 41
text(d, (margin, 860), 'Source: regression boot logs + grade + raw kernel output', small)
assert y < 840
canvas.save(out / '02-allocator-checks.png')
print('Rendered 2 figures from evidence; all source/value and text-width checks passed.')
