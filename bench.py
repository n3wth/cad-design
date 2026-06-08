"""
Parametric garage workbench -> isometric SVG (labeled) + cut DXFs, from ONE model.

Frame bench, beginner joinery: 2x4 frame + 4x4 (doubled-2x4) legs, 18 mm ply top
and lower shelf. Every joint is a screwed/bolted BUTT joint -- no table saw, no
dado, no router, no pocket jig. The iso render and the DXF come from the SAME
build123d model, so the picture can't disagree with the cut files.

Verified pipeline: build123d 0.10 on Python 3.12.
    ./venv/bin/python bench.py [out_dir]
    rsvg-convert <out_dir>/bench-iso.svg -o <out_dir>/bench-iso.png   # then LOOK

All dimensions in mm. "2x4" here = its REAL dressed size 38 x 89 mm (nominal 2x4).
"""
import sys, re
from build123d import *

# ---- Parameters (the knobs that change the build) -------------------------
L      = 1800      # bench length (long axis)
DEPTH  = 600       # bench depth (front-to-back); 600 lets top+shelf nest on ONE 8x4 sheet
HEIGHT = 910       # work-surface height (top of ply)
TOP_T  = 18        # plywood top thickness
SH_T   = 18        # plywood lower-shelf thickness
LUM_W  = 89        # dressed 2x4 wide face (nominal 2x4 = 38 x 89 mm)
LUM_T  = 38        # dressed 2x4 thick face
LEG    = 76        # leg = doubled 2x4 -> 76 x 89; treat post as 76 x 89
SHELF_H = 150      # height of lower-shelf top off the floor
OVER   = 25        # top overhang past frame, each long side & each end
OUT    = sys.argv[1] if len(sys.argv) > 1 else "."

# Derived frame footprint (sits under the top, inset by overhang)
FRM_L = L - 2*OVER          # frame length between outer leg faces
FRM_D = DEPTH - 2*OVER      # frame depth between outer leg faces
post_h = HEIGHT - TOP_T     # legs run from floor to underside of top
# centers of the four legs (X = length, Y = depth, Z = height; origin = bench center, floor at Z=0 base)
lx = FRM_L/2 - LEG/2
ly = FRM_D/2 - LUM_T/2      # legs flush to front/back rail outer face

# ---- Model the bench ------------------------------------------------------
# We center the part in X/Y and run Z from 0 (floor) to HEIGHT.
with BuildPart() as bench:
    # 4 legs (posts), floor (Z=0) up to underside of top
    with Locations(
        (-lx, -ly, post_h/2), ( lx, -ly, post_h/2),
        (-lx,  ly, post_h/2), ( lx,  ly, post_h/2),
    ):
        Box(LEG, LUM_T, post_h)

    # Long rails (front + back), one set just under the top, one set at shelf height.
    rail_len_x = FRM_L - 2*LEG          # rails butt between the legs
    for z in (post_h - LUM_W/2, SHELF_H + LUM_W/2):
        with Locations((0, -ly, z), (0, ly, z)):
            Box(rail_len_x, LUM_T, LUM_W)

    # End rails (left + right), between the front/back legs on each end.
    rail_len_y = FRM_D - 2*LUM_T
    for z in (post_h - LUM_W/2, SHELF_H + LUM_W/2):
        with Locations((-lx, 0, z), (lx, 0, z)):
            Box(LUM_T, rail_len_y, LUM_W)

    # Plywood top (full bench footprint, with overhang), sits on the frame.
    with Locations((0, 0, post_h + TOP_T/2)):
        Box(L, DEPTH, TOP_T)

    # Plywood lower shelf, resting on the lower rails, inset to clear the legs.
    with Locations((0, 0, SHELF_H + LUM_W + SH_T/2)):
        Box(FRM_L - 2*LEG + 2*LUM_T, FRM_D - 2*LUM_T, SH_T)

part = bench.part

# ---- Isometric hidden-line projection (same viewport math as shelf.py) ----
VP = dict(viewport_origin=(2600, -2600, 2000), viewport_up=(0, 0, 1),
          look_at=(0, 0, HEIGHT/2))
visible, hidden = part.project_to_viewport(**VP)

def edges_to_lines(edges):
    out = []
    for e in edges:
        vs = e.vertices()
        if len(vs) >= 2:
            out.append(((vs[0].X, vs[0].Y), (vs[-1].X, vs[-1].Y)))
    return out

vis_l = edges_to_lines(visible)
hid_l = edges_to_lines(hidden)

# ---- Dimension geometry, projected through the SAME viewport ---------------
def proj_seg(p0, p1):
    e = Edge.make_line(p0, p1)
    v, _ = e.project_to_viewport(**VP)
    vs = v.vertices()
    return ((vs[0].X, vs[0].Y), (vs[-1].X, vs[-1].Y))

hl, hd = L/2, DEPTH/2
ztop = HEIGHT
# Height dim: vertical line pushed to world -X/-Y (screen-left), measured floor->top.
OH = 360
dim_H   = proj_seg((-hl-OH, -hd-OH, 0), (-hl-OH, -hd-OH, ztop))
dim_Hw1 = proj_seg((-hl, -hd, 0),     (-hl-OH, -hd-OH, 0))
dim_Hw2 = proj_seg((-hl, -hd, ztop),  (-hl-OH, -hd-OH, ztop))
# Length dim: front-bottom X edge, dropped straight down (-Z).
OW = 420
dim_W   = proj_seg((-hl, -hd, -OW), (hl, -hd, -OW))
dim_Ww1 = proj_seg((-hl, -hd, 0),   (-hl, -hd, -OW))
dim_Ww2 = proj_seg((hl, -hd, 0),    (hl, -hd, -OW))
# Depth dim: right-bottom Y edge, dropped straight down (-Z).
OD = 420
dim_D   = proj_seg((hl, -hd, -OD), (hl, hd, -OD))
dim_Dw1 = proj_seg((hl, -hd, 0),   (hl, -hd, -OD))
dim_Dw2 = proj_seg((hl, hd, 0),    (hl, hd, -OD))

dim_all = [dim_H, dim_Hw1, dim_Hw2, dim_W, dim_Ww1, dim_Ww2, dim_D, dim_Dw1, dim_Dw2]
allpts = ([p for L_ in (vis_l, hid_l) for seg in L_ for p in seg] +
          [p for seg in dim_all for p in seg])
xs = [p[0] for p in allpts]; ys = [p[1] for p in allpts]
minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
cw = maxx - minx; ch = maxy - miny
scale = 0.14
PAD, PAD_B = 40, 104
CAPTION = ("%d x %d mm top - %d mm high - 2x4 frame, %d mm ply top + shelf"
           % (L, DEPTH, HEIGHT, TOP_T))
content_w = cw*scale + PAD*2
min_caption_w = len(CAPTION)*6.6 + 48
Wpx = round(max(content_w, min_caption_w))
Hpx = round(ch*scale + PAD*2 + PAD_B)
x_shift = (Wpx - content_w)/2
def X(x): return round((x-minx)*scale + PAD + x_shift, 1)
def Yt(y): return round((maxy-y)*scale + PAD, 1)

INK = "#1d1d1f"; MED = "#1d1d1f"; THIN = "#9a9aa0"
S = []
def Ln(seg, stroke, w, dash=None):
    (a, b) = seg
    d = f' stroke-dasharray="{dash}"' if dash else ''
    S.append(f'<line x1="{X(a[0])}" y1="{Yt(a[1])}" x2="{X(b[0])}" y2="{Yt(b[1])}" '
             f'stroke="{stroke}" stroke-width="{w}"{d} stroke-linecap="round"/>')
def mid(seg): a, b = seg; return ((a[0]+b[0])/2, (a[1]+b[1])/2)

S.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {Wpx} {Hpx}" '
         f'width="{Wpx}" height="{Hpx}" '
         f'font-family="ui-sans-serif,-apple-system,system-ui,sans-serif">')
S.append(f'<rect width="{Wpx}" height="{Hpx}" fill="white"/>')
for seg in hid_l: Ln(seg, THIN, 0.7, dash="3 3")
for seg in vis_l: Ln(seg, MED, 1.4)
for w in (dim_Hw1, dim_Hw2, dim_Ww1, dim_Ww2, dim_Dw1, dim_Dw2): Ln(w, THIN, 0.9, dash="1 3")
for d in (dim_H, dim_W, dim_D): Ln(d, THIN, 1.1, dash="1 3")

def dim_label(seg, txt, dx=0, dy=0, rot=None):
    mx, my = mid(seg); sx, sy = X(mx)+dx, Yt(my)+dy
    tr = f' transform="rotate({rot} {sx} {sy})"' if rot is not None else ''
    S.append(f'<text x="{sx}" y="{sy}" font-size="15" font-weight="600" fill="{INK}" '
             f'text-anchor="middle" dominant-baseline="middle"{tr}>{txt}</text>')
dim_label(dim_H, f"{HEIGHT} mm", dx=-12, rot=-90)
dim_label(dim_W, f"{L} mm", dx=-14, dy=16)
dim_label(dim_D, f"{DEPTH} mm", dx=14, dy=16)

cap_cx = Wpx/2; capy = Hpx-54
S.append(f'<text x="{cap_cx}" y="{capy}" font-size="17" font-weight="700" fill="{INK}" '
         f'text-anchor="middle">Garage workbench</text>')
S.append(f'<text x="{cap_cx}" y="{capy+22}" font-size="13" fill="#6b6b70" '
         f'text-anchor="middle">{CAPTION}</text>')
S.append('</svg>')
open(f"{OUT}/bench-iso.svg", "w").write("\n".join(S))
print("iso svg OK ->", f"{OUT}/bench-iso.svg", f"({Wpx}x{Hpx})")

# ---- Cut DXFs derived FROM the model (not fresh boxes) --------------------
# Plywood top: largest horizontal face. Pull its outer wire to XY.
ply_faces = [f for f in part.faces() if abs(f.normal_at().Z) > 0.99]
top_face = max(ply_faces, key=lambda f: f.area)
top_profile = Plane(top_face).to_local_coords(top_face)
dxf = ExportDXF(unit=Unit.MM); dxf.add_layer("cut")
dxf.add_shape(top_profile.outer_wire(), layer="cut")
dxf.write(f"{OUT}/top-panel.dxf")
print("dxf OK ->", f"{OUT}/top-panel.dxf  (ply top {L}x{DEPTH} mm, from model)")

# Leg: take one leg post's largest face for a fabrication reference profile.
# (Legs are simple rip cuts; DXF mainly proves length/section against the model.)
leg_solid = min(part.solids(), key=lambda s: s.volume)  # a leg or rail is smallest; guard below
print("part solids:", len(part.solids()))
