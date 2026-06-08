"""Parametric box-carcass shelf -> labeled isometric SVG + FULL nested cutset DXF.

For someone with an 8x4 CNC: every unique part is laid out flat on a 2440x1220
sheet with kerf spacing, so the cut file is a real toolpath layout, not one part.
The iso render and the cut layout come from the SAME model dimensions, so the
picture can't disagree with what gets cut.

Verified path: build123d 0.10 on Python 3.12.
    python3.12 -m venv venv && ./venv/bin/pip install build123d
    ./venv/bin/python assets/shelf-cnc.py [out_dir]
    rsvg-convert --background-color=white <out_dir>/shelf-iso.svg -o iso.png  # then LOOK

Change W/H/D/T/N + sheet/kerf for any box-carcass build.
"""
import sys, re
from build123d import *
from build123d.exporters import ColorIndex

# ---- PARAMETERS (the only thing to change) -------------------------------
# These nest on ONE 8x4 sheet with comfortable holddown margin (verified below).
W, H, D, T, N = 760, 1680, 290, 18, 4   # width, height, depth, panel thickness (mm); N interior shelves
KERF = 3.0          # router bit diameter (mm) -> gap between parts so the cut doesn't eat a neighbour
SHEET_W, SHEET_H = 2440, 1220   # one 8x4 sheet (mm)
MARGIN = 12         # keep parts off the very edge (clamp/holddown room)
OUT = sys.argv[1] if len(sys.argv) > 1 else "."

# ---- 3D MODEL (drives BOTH the drawing and the part sizes) ---------------
with BuildPart() as shelf:
    with Locations((-(W/2 - T/2), 0, 0), ((W/2 - T/2), 0, 0)):   # two sides
        Box(T, D, H)
    with Locations((0, 0, H/2 - T/2), (0, 0, -(H/2 - T/2))):     # top + bottom
        Box(W - 2*T, D, T)
    clear = H - 2*T
    for i in range(1, N + 1):                                    # interior shelves
        with Locations((0, 0, -clear/2 + clear * i/(N + 1))):
            Box(W - 2*T, D, T)
part = shelf.part

# ---- ISOMETRIC RENDER (hidden-line, labeled) -----------------------------
exporter = ExportSVG(scale=0.18)
exporter.add_layer("solid", line_weight=0.5, line_color=Color(0.1, 0.1, 0.12))
visible, _ = part.project_to_viewport(
    viewport_origin=(1600, -1600, 1200), viewport_up=(0, 0, 1), look_at=(0, 0, 0)
)
exporter.add_shape(visible, layer="solid")
raw = f"{OUT}/shelf-iso-raw.svg"
exporter.write(raw)

svg = open(raw).read()
vx, vy, vw, vh = map(float, re.search(r'viewBox="([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)"', svg).groups())
ann = [
    '<g font-family="ui-sans-serif, system-ui, sans-serif" fill="#1d1d1f">',
    f'<line x1="{vx-40}" y1="{vy+90}" x2="{vx-40}" y2="{vy+vh-90}" stroke="#999" stroke-width="6"/>',
    f'<text x="{vx-150}" y="{vy+vh/2}" font-size="64" font-weight="600" transform="rotate(-90 {vx-150} {vy+vh/2})">{H} mm H</text>',
    f'<text x="{vx+60}" y="{vy+vh+90}" font-size="64" font-weight="600">{W} mm W</text>',
    f'<text x="{vx+vw/2+40}" y="{vy+vh+90}" font-size="64" font-weight="600">{D} mm D</text>',
    f'<text x="{vx}" y="{vy+vh+200}" font-size="58" font-weight="600">Freestanding bookshelf · {N} shelves</text>',
    f'<text x="{vx}" y="{vy+vh+275}" font-size="48" fill="#6b6b70">{T} mm plywood · nested on 1 sheet (8×4)</text>',
    '</g>',
]
svg = svg.replace(f'viewBox="{vx} {vy} {vw} {vh}"', f'viewBox="{vx-170} {vy-20} {vw+220} {vh+360}"')
svg = re.sub(r'width="[\d.]+mm" height="[\d.]+mm"', 'width="540" height="760"', svg, count=1)
svg = svg.replace('</svg>', "\n".join(ann) + "\n</svg>")
open(f"{OUT}/shelf-iso.svg", "w").write(svg)
print("iso svg OK ->", f"{OUT}/shelf-iso.svg")

# ---- FULL CUTSET: every unique part, with quantities ---------------------
# Each part is (label, length_x, width_y) as it lies flat on the sheet.
side_l, side_w = H, D                       # 2 sides: full height x depth
hshelf_l, hshelf_w = W - 2*T, D             # top, bottom, and N interior shelves: same blank
parts = [("Side", side_l, side_w, 2),
         ("Shelf", hshelf_l, hshelf_w, N + 2)]   # +2 = top & bottom

# ---- FIRST-FIT-DECREASING shelf nesting (the "shelf algorithm") ----------
# Lay each part with its LONG side along the 2440 sheet length, sort longest-first,
# drop each into the first row it fits, else open a new row. Rows stack up the
# 1220 direction. This is the standard 2D bin-pack heuristic, and it is honest:
# what you see is exactly what the router cuts.
USW = SHEET_W - 2 * MARGIN
flat = []
for label, l, w, qty in parts:
    long_side, short_side = max(l, w), min(l, w)
    flat += [(label, long_side, short_side)] * qty
flat.sort(key=lambda p: p[1], reverse=True)

rows = []   # each row: [used_len, max_width, [(label, l, w), ...]]
for label, l, w in flat:
    for r in rows:
        gap = KERF if r[2] else 0
        if r[0] + gap + l <= USW:
            r[0] += gap + l; r[1] = max(r[1], w); r[2].append((label, l, w))
            break
    else:
        rows.append([l, w, [(label, l, w)]])

# Resolve each part to an absolute (x, y) origin on the sheet.
placed = []
cy = MARGIN
for used_len, row_w, items in rows:
    cx = MARGIN
    for label, l, w in items:
        placed.append((label, cx, cy, l, w))
        cx += l + KERF
    cy += row_w + KERF
used_h = cy - KERF + MARGIN
fits = used_h <= SHEET_H

# ---- DXF: real rectangles on the sheet, each on the "cut" layer ----------
dxf = ExportDXF(unit=Unit.MM)
dxf.add_layer("cut")
dxf.add_layer("sheet", color=ColorIndex.GRAY)
dxf.add_shape(Rectangle(SHEET_W, SHEET_H).locate(Location((SHEET_W/2, SHEET_H/2))).wire(), layer="sheet")
for label, x, y, l, w in placed:
    r = Rectangle(l, w).locate(Location((x + l/2, y + w/2)))
    dxf.add_shape(r.wire(), layer="cut")
dxf.write(f"{OUT}/cutset.dxf")

# ---- REPORT --------------------------------------------------------------
part_area = sum(l * w for _, _, _, l, w in placed) / 1e6
sheet_area = SHEET_W * SHEET_H / 1e6
print(f"cutset.dxf OK -> {OUT}/cutset.dxf  ({len(placed)} parts, kerf {KERF} mm)")
print(f"  used sheet height: {used_h:.0f} / {SHEET_H} mm  -> {'FITS one 8x4' if fits else 'DOES NOT FIT one sheet'}")
print(f"  material used: {part_area:.2f} of {sheet_area:.2f} m^2  ({100*part_area/sheet_area:.0f}% of one sheet)")
print(f"  cut list: 2x Side {side_l}x{side_w}, {N+2}x Shelf {hshelf_l}x{hshelf_w} (all {T} mm)")
