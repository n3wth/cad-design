"""
Parametric freestanding bookshelf -> isometric SVG (labeled) + CNC DXF.

Verified: build123d 0.10 on Python 3.12.
    python3.12 -m venv venv && ./venv/bin/pip install build123d
    ./venv/bin/python shelf.py [out_dir]
    rsvg-convert <out_dir>/shelf-iso.svg -o shelf-iso.png   # then LOOK

Change W/H/D/T/N for any box-carcass build. The iso render and the DXF
come from the SAME model, so the picture can't disagree with the cut file.
"""
import sys, re
from build123d import *

W, H, D, T, N = 800, 1800, 300, 18, 4   # width, height, depth, panel thickness (mm); N interior shelves
OUT = sys.argv[1] if len(sys.argv) > 1 else "."

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

# --- Isometric hidden-line render ---
exporter = ExportSVG(scale=0.18)
exporter.add_layer("solid", line_weight=0.5, line_color=Color(0.1, 0.1, 0.12))
visible, _ = part.project_to_viewport(
    viewport_origin=(1600, -1600, 1200), viewport_up=(0, 0, 1), look_at=(0, 0, 0)
)
exporter.add_shape(visible, layer="solid")
raw = f"{OUT}/shelf-iso-raw.svg"
exporter.write(raw)

# --- Add W/H/D dimension labels + caption (build123d draws geometry only) ---
svg = open(raw).read()
vx, vy, vw, vh = map(float, re.search(r'viewBox="([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)"', svg).groups())
ann = [
    '<g font-family="ui-sans-serif, system-ui, sans-serif" fill="#1d1d1f">',
    f'<line x1="{vx-40}" y1="{vy+90}" x2="{vx-40}" y2="{vy+vh-90}" stroke="#999" stroke-width="6"/>',
    f'<text x="{vx-150}" y="{vy+vh/2}" font-size="64" font-weight="600" transform="rotate(-90 {vx-150} {vy+vh/2})">{H} mm H</text>',
    f'<text x="{vx+60}" y="{vy+vh+90}" font-size="64" font-weight="600">{W} mm W</text>',
    f'<text x="{vx+vw/2+40}" y="{vy+vh+90}" font-size="64" font-weight="600">{D} mm D</text>',
    f'<text x="{vx}" y="{vy+vh+200}" font-size="58" font-weight="600">Freestanding bookshelf · {N} shelves</text>',
    f'<text x="{vx}" y="{vy+vh+275}" font-size="48" fill="#6b6b70">{T} mm plywood · 1 of 1 sheet (8×4)</text>',
    '</g>',
]
svg = svg.replace(f'viewBox="{vx} {vy} {vw} {vh}"', f'viewBox="{vx-170} {vy-20} {vw+220} {vh+360}"')
svg = re.sub(r'width="[\d.]+mm" height="[\d.]+mm"', 'width="540" height="760"', svg, count=1)
svg = svg.replace('</svg>', "\n".join(ann) + "\n</svg>")
open(f"{OUT}/shelf-iso.svg", "w").write(svg)
print("iso svg OK ->", f"{OUT}/shelf-iso.svg")

# --- CNC DXF of the side panel, derived FROM the model (not a fresh box) ---
# Pull the actual panel face out of the carcass so any future dado/shelf-pin holes
# carry through to the cut file. The largest face in the part is a side panel's
# outer face (D x H); flatten it to XY for a clean 2D cut profile.
side_face = sorted(part.faces(), key=lambda f: f.area, reverse=True)[0]
profile = Plane(side_face).to_local_coords(side_face)   # bring the cut face onto XY
dxf = ExportDXF(unit=Unit.MM); dxf.add_layer("cut")
dxf.add_shape(profile.outer_wire(), layer="cut")
dxf.write(f"{OUT}/side-panel.dxf")
print("dxf OK ->", f"{OUT}/side-panel.dxf  (side panel {D}x{H} mm, from model)")
