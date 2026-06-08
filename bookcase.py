"""
CNC bookcase — parametric build123d model.

One model, two outputs (per the cad-design rule):
  1. bookcase_iso.png   — isometric drawing of the finished, assembled piece
  2. bookcase_cut.dxf    — flat, nested, cuttable parts on one 2440x1220 sheet
  3. bookcase_nest.png   — a human-readable picture of that same nest

Joinery: through slot-and-tab (no special bit, no dado stack, no edge bander).
Every interior slot corner gets a DOGBONE fillet so router-cut slots seat square.

Run:  .venv/bin/python bookcase.py
"""

import math
from build123d import (
    BuildPart, BuildSketch, BuildLine, Part, Sketch, Plane, Axis, Location,
    Box, Rectangle, RectangleRounded, Circle, Polyline, Line,
    extrude, make_face, add, fillet, Mode, Compound, Color, GeomType,
    ExportDXF, LineType, project,
)
import build123d as bd

# ---------------------------------------------------------------------------
# PARAMETERS  (a beginner edits ONLY this block to re-spec the shelf)
# ---------------------------------------------------------------------------

# --- the piece (millimetres) ---
HEIGHT   = 1800.0   # floor to top of carcass
WIDTH    = 800.0    # outside-to-outside, left side to right side
DEPTH    = 300.0    # front-to-back (book depth; 300 holds most books/binders)
N_OPENINGS = 4      # gaps between shelves -> this gives 5 horizontal boards
                    #   (top + bottom + 3 mid shelves)

# --- material ---
# NOMINAL is what the supplier calls it ("18mm ply").
# MEASURED is what your calipers actually read on the real sheet.
# Slots are cut to MEASURED so the tabs are not loose or jammed.
# 18mm birch ply commonly measures ~17.3-17.8mm. SHE MUST MEASURE AND EDIT THIS.
THICK_NOMINAL  = 18.0
THICK_MEASURED = 17.5     # <-- MEASURE YOUR SHEET, then set this exactly
T = THICK_MEASURED

# --- CNC / cut parameters ---
BIT_DIA   = 6.0     # 1/4" (6.35mm) is typical; 6.0 keeps slots tidy. Match your bit.
KERF      = BIT_DIA # router removes a full bit width along the path
SLOT_FIT  = 0.2     # extra slot width for a snug-but-assemblable fit (per slot)
SHEET_W   = 2440.0  # 8ft
SHEET_H   = 1220.0  # 4ft
SHEET_MARGIN = 12.0 # keep parts off the very edge (spoilboard screws / clamps)
PART_GAP  = BIT_DIA + 6.0   # gap between nested parts so the bit fits between cuts

# --- tab geometry ---
TAB_LEN   = T            # tab pokes through and sits flush with outer face
TAB_W     = 60.0         # width of each through-tab
N_TABS    = 3            # tabs per shelf-end (top, middle, bottom of the joint)

# derived
# CARCASS LAYOUT (corner-jointed box):
#   - TOP CAP and BOTTOM CAP are full-width boards that CAP the two sides.
#     The sides' top/bottom EDGES carry tabs that seat into slots in the caps.
#     (A corner box joint - same tool, same idea as the through-tabs.)
#   - The MIDDLE shelves pass THROUGH the side faces on through-tabs.
# This keeps every slot enclosed inside its own panel (no slot at a panel edge).
N_SHELVES   = N_OPENINGS + 1     # total horizontal boards (2 caps + middles)
N_MIDDLE    = N_SHELVES - 2      # interior shelves that through-tab the sides
inner_w     = WIDTH - 2 * T      # clear width between the two sides
shelf_len   = inner_w + 2 * TAB_LEN   # a middle shelf incl. its through-tabs
cap_len     = WIDTH              # caps run the full outside width
side_height = HEIGHT - 2 * T     # sides sit BETWEEN the caps; +2T caps = HEIGHT

# Heights (centre, measured from the bottom of the SIDE panel) of the middle
# shelves. The clear interior runs from the top of the bottom cap to the bottom
# of the top cap = side_height. Evenly divide that into N_OPENINGS gaps.
def middle_shelf_centers():
    # interior span is the full side_height; place N_MIDDLE shelves to make
    # N_OPENINGS equal gaps between the bottom cap, the shelves, and the top cap.
    return [i * side_height / N_OPENINGS for i in range(1, N_MIDDLE + 1)]

# y-position of a middle shelf measured from the SIDE PANEL CENTRE
MID_CY = [c - side_height / 2 for c in middle_shelf_centers()]

# ---------------------------------------------------------------------------
# DOGBONE HELPER
# A router bit is round; it can't cut a sharp inside corner. A mating square
# tab won't fully seat into a slot whose corners are rounded. The fix is a
# "dogbone": a small circle (bit radius) overcut into each inside corner so
# the square tab has clearance to reach the corner. We add dogbones to slots.
# ---------------------------------------------------------------------------

def slot_with_dogbones(width, height, r):
    """A rectangular through-slot (centred at origin) with dogbone overcuts
    at all four inside corners. Returns a Sketch to subtract."""
    with BuildSketch() as s:
        Rectangle(width, height)
        # A true dogbone centres the relief circle ON the corner, so the bit
        # over-travels past the corner by ~ (r - r/sqrt2) on each axis. That
        # gives a square tab clearance to reach the corner instead of jamming
        # on the radius a round bit leaves behind.
        for sx in (-1, 1):
            for sy in (-1, 1):
                cx = sx * (width / 2)
                cy = sy * (height / 2)
                with Locations((cx, cy)):
                    Circle(r)
    return s.sketch

# build123d Locations import (kept here to keep param block clean)
from build123d import Locations  # noqa: E402


# ---------------------------------------------------------------------------
# 2D PART PROFILES  (these are what actually get cut)
# ---------------------------------------------------------------------------
DOG_R = BIT_DIA / 2 + 0.1   # dogbone radius slightly > bit radius for clearance

def _tab_xs():
    """X positions (across DEPTH) of the N_TABS tabs/slots, shared by every
    mating pair so tabs and slots always line up."""
    pitch = DEPTH / (N_TABS + 1)
    return [-DEPTH / 2 + k * pitch for k in range(1, N_TABS + 1)]

def side_profile():
    """One vertical side panel, lying flat (DEPTH along X, side_height along Y).
       - 3 MIDDLE through-slots (dogboned) in the FACE for the middle shelves.
       - tabs on the TOP and BOTTOM edges (corner joint into the caps).
    The body is drawn as a rectangle with edge tabs added, then slots cut."""
    with BuildSketch(Plane.XY) as sk:
        Rectangle(DEPTH, side_height, align=(bd.Align.CENTER, bd.Align.CENTER))
        # edge tabs on top (+Y) and bottom (-Y) edges -> into the caps
        for end in (-1, 1):
            for x in _tab_xs():
                with Locations((x, end * (side_height / 2 + TAB_LEN / 2))):
                    Rectangle(TAB_W - SLOT_FIT, TAB_LEN)
        # middle through-slots in the face
        for y in MID_CY:
            for x in _tab_xs():
                slot = slot_with_dogbones(TAB_W, T + SLOT_FIT, DOG_R)
                add(slot.moved(Location((x, y))), mode=Mode.SUBTRACT)
    return sk.sketch

def shelf_profile():
    """One MIDDLE shelf, flat (DEPTH along X, shelf_len along Y): a board with
    N_TABS through-tabs on EACH end that pass through the side faces."""
    with BuildSketch(Plane.XY) as sk:
        Rectangle(DEPTH, inner_w, align=(bd.Align.CENTER, bd.Align.CENTER))
        for end in (-1, 1):
            for x in _tab_xs():
                with Locations((x, end * (inner_w / 2 + TAB_LEN / 2))):
                    Rectangle(TAB_W - SLOT_FIT, TAB_LEN)
    return sk.sketch

def cap_profile():
    """One CAP (top or bottom), flat (DEPTH along X, cap_len=WIDTH along Y).
    Receives the side EDGE-tabs: a dogboned slot near each end, one per side
    tab. Slots are inset from the cap ends so they stay fully enclosed."""
    with BuildSketch(Plane.XY) as sk:
        Rectangle(DEPTH, cap_len, align=(bd.Align.CENTER, bd.Align.CENTER))
        # the two sides sit at +/- (WIDTH/2 - T/2) along the cap length (Y).
        for side_sign in (-1, 1):
            yc = side_sign * (cap_len / 2 - T / 2)   # centre line of that side
            for x in _tab_xs():
                slot = slot_with_dogbones(TAB_W, T + SLOT_FIT, DOG_R)
                add(slot.moved(Location((x, yc))), mode=Mode.SUBTRACT)
    return sk.sketch

def back_cleat_profile():
    """A back rail/cleat to square the carcass and take wall-anchor screws.
    Two of them. Plain rectangle, no slots: it screws on (no special bit).
    Pilot holes are marked at assembly, not cut here."""
    with BuildSketch(Plane.XY) as sk:
        Rectangle(inner_w, 90.0)
    return sk.sketch


# ---------------------------------------------------------------------------
# 3D ASSEMBLY  (for the isometric drawing only)
# ---------------------------------------------------------------------------

def build_assembly():
    """Assemble the box for the isometric. Z is up; the box centre of the
    interior sits at HEIGHT/2. Two side panels stand between a bottom and top
    cap; three middle shelves span between the sides."""
    parts = []
    SIDE_C = Color(0.82, 0.71, 0.55)
    CAP_C  = Color(0.72, 0.60, 0.43)
    SH_C   = Color(0.88, 0.78, 0.62)

    # --- SIDES: extrude side profile (DEPTH x side_height x T), stand upright.
    side_solid = extrude(side_profile(), amount=T)
    # rotate so side_height -> Z, DEPTH -> Y, T -> X. Centre vertically at HEIGHT/2.
    for sgn in (-1, 1):
        s = side_solid.rotate(Axis.X, 90).rotate(Axis.Z, 90)
        s = s.moved(Location((sgn * (WIDTH / 2 - T / 2), 0, HEIGHT / 2)))
        s.color = SIDE_C
        parts.append(s)

    # --- CAPS: extrude cap profile (DEPTH x WIDTH x T), lay flat at top & bottom.
    cap_solid = extrude(cap_profile(), amount=T)
    # profile: DEPTH along X, WIDTH along Y, T along Z. Want WIDTH->X, DEPTH->Y.
    for z in (T / 2, HEIGHT - T / 2):   # bottom cap centre, top cap centre
        c = cap_solid.rotate(Axis.Z, 90).moved(Location((0, 0, z)))
        c.color = CAP_C
        parts.append(c)

    # --- MIDDLE SHELVES: extrude shelf profile, lay flat at each MID height.
    shelf_solid = extrude(shelf_profile(), amount=T)
    for y in MID_CY:                    # y measured from side-panel centre
        z = HEIGHT / 2 + y              # convert to absolute Z
        sh = shelf_solid.rotate(Axis.Z, 90).moved(Location((0, 0, z)))
        sh.color = SH_C
        parts.append(sh)

    return Compound(children=parts)


# ---------------------------------------------------------------------------
# ISOMETRIC DRAWING  (render the 3D assembly as a clean line iso)
# ---------------------------------------------------------------------------

def export_isometric(asm, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    import numpy as np

    fig = plt.figure(figsize=(8, 10))
    ax = fig.add_subplot(111, projection="3d")

    faces = []
    for solid in asm.solids():
        for face in solid.faces():
            try:
                verts = [(v.X, v.Y, v.Z) for v in face.outer_wire().vertices()]
            except Exception:
                verts = [(v.X, v.Y, v.Z) for v in face.vertices()]
            if len(verts) >= 3:
                faces.append(verts)

    pc = Poly3DCollection(faces, facecolor=(0.86, 0.76, 0.60),
                          edgecolor=(0.15, 0.12, 0.08), linewidths=0.4, alpha=1.0)
    ax.add_collection3d(pc)

    ax.set_xlim(-WIDTH / 2 - 50, WIDTH / 2 + 50)
    ax.set_ylim(-DEPTH / 2 - 50, DEPTH / 2 + 50)
    ax.set_zlim(0, HEIGHT + 50)
    ax.set_box_aspect((WIDTH, DEPTH, HEIGHT))
    ax.view_init(elev=22, azim=-50)
    ax.set_axis_off()
    ax.set_title(
        f"Bookcase  {int(WIDTH)}W x {int(HEIGHT)}H x {int(DEPTH)}D mm\n"
        f"{N_SHELVES} boards, {N_OPENINGS} openings — {int(THICK_NOMINAL)}mm ply",
        fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


# ---------------------------------------------------------------------------
# NEST + DXF  (lay every flat part on one sheet; export cuttable DXF)
# ---------------------------------------------------------------------------

def place(sketch_face, x, y, rot=0):
    f = sketch_face
    if rot:
        f = f.rotate(Axis.Z, rot)
    return f.moved(Location((x, y)))

def build_nest():
    """Nest every flat part across TWO 8x4 sheets (a 1800mm bookcase does not
    fit one sheet at a sane utilisation; see the gate output). Returns a list
    of sheets, each a dict {placed:[faces], labels:[(name,x,y)]}.

    Sheet 1: two SIDES (the long ~1765mm parts) + two back CLEATS.
    Sheet 2: two CAPS + three MIDDLE SHELVES (all ~300x800, laid in a row).
    Both sheets sit far under capacity, so packing is simple and robust."""

    side  = side_profile()         # DEPTH(x) x side_height(y)
    shelf = shelf_profile()        # DEPTH(x) x shelf_len(y)
    cap   = cap_profile()          # DEPTH(x) x WIDTH(y)
    cleat = back_cleat_profile()   # inner_w(x) x 90(y)
    M, G = SHEET_MARGIN, PART_GAP

    def new_sheet():
        return {"placed": [], "labels": []}

    def put(sheet, face, rot, bx, by, label):
        """Place `face` (optionally rotated) so its bbox bottom-left corner
        lands at (bx, by). Returns the placed face's bounding box."""
        f = face.rotate(Axis.Z, rot) if rot else face
        bb = f.bounding_box()
        f = f.moved(Location((bx - bb.min.X, by - bb.min.Y)))
        nb = f.bounding_box()
        sheet["placed"].append(f)
        sheet["labels"].append((label, nb.center().X, nb.center().Y))
        return nb

    # ---- SHEET 1: sides (~1765 long x 300) laid lengthwise, stacked, + cleats
    s1 = new_sheet()
    a = put(s1, side, 90, M, M, "SIDE-L")          # side_height->X, DEPTH->Y
    b = put(s1, side, 90, M, a.max.Y + G, "SIDE-R")
    cl_y = b.max.Y + G                              # band above the two sides
    c1 = put(s1, cleat, 0, M, cl_y, "CLEAT-1")
    put(s1, cleat, 0, c1.max.X + G, cl_y, "CLEAT-2")

    # ---- SHEET 2: two caps + three middle shelves (all 300 deep x 800), in a row
    s2 = new_sheet()
    x = M
    nb = put(s2, cap, 0, x, M, "CAP-BOTTOM"); x = nb.max.X + G
    nb = put(s2, cap, 0, x, M, "CAP-TOP");    x = nb.max.X + G
    for i in range(N_MIDDLE):
        nb = put(s2, shelf, 0, x, M, f"SHELF-{i+1}"); x = nb.max.X + G

    return [s1, s2]


def export_nest_png(sheets, path):
    """One stacked figure: one row per sheet, drawn to scale."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle as MplRect

    n = len(sheets)
    fig, axes = plt.subplots(n, 1, figsize=(12, 4.0 * n))
    if n == 1:
        axes = [axes]

    for si, (ax, sheet) in enumerate(zip(axes, sheets), start=1):
        ax.add_patch(MplRect((0, 0), SHEET_W, SHEET_H, fill=False,
                             edgecolor="black", linewidth=1.5))
        ax.add_patch(MplRect((SHEET_MARGIN, SHEET_MARGIN),
                             SHEET_W - 2 * SHEET_MARGIN, SHEET_H - 2 * SHEET_MARGIN,
                             fill=False, edgecolor="0.7", linewidth=0.6, linestyle="--"))
        for face, (label, lx, ly) in zip(sheet["placed"], sheet["labels"]):
            for edge in face.edges():
                if edge.geom_type == GeomType.CIRCLE:
                    c = edge.arc_center
                    circ = plt.Circle((c.X, c.Y), edge.radius, fill=False,
                                      edgecolor="#b00", linewidth=0.6)
                    ax.add_patch(circ)
                else:
                    pts = [(v.X, v.Y) for v in edge.vertices()]
                    if len(pts) == 2:
                        ax.plot([pts[0][0], pts[1][0]], [pts[0][1], pts[1][1]],
                                color="#06c", linewidth=0.7)
            bb = face.bounding_box()
            ax.text(bb.center().X, bb.center().Y, label, ha="center",
                    va="center", fontsize=7, color="black")
        ax.set_xlim(-30, SHEET_W + 30)
        ax.set_ylim(-30, SHEET_H + 30)
        ax.set_aspect("equal")
        ax.set_title(f"SHEET {si} of {n} — one {int(SHEET_W)}x{int(SHEET_H)}mm "
                     f"(8x4) panel.  blue = cut line, red = dogbone overcut",
                     fontsize=10)
        ax.set_xlabel("mm")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def export_cut_dxf(sheets, base_path):
    """One DXF per sheet, so the operator opens one file per panel.
    base_path 'bookcase_cut.dxf' -> 'bookcase_cut_sheet1.dxf', '..._sheet2.dxf'.
    Returns the list of written paths."""
    import os
    root, ext = os.path.splitext(base_path)
    written = []
    for si, sheet in enumerate(sheets, start=1):
        placed = sheet["placed"]
        merged = placed[0]
        for f in placed[1:]:
            merged = merged + f
        exporter = ExportDXF(unit=bd.Unit.MM, line_weight=0.25)
        exporter.add_shape(merged)
        p = f"{root}_sheet{si}{ext}"
        exporter.write(p)
        written.append(p)
    return written


# ---------------------------------------------------------------------------
# CHECK / GATE  (printed before any cutting)
# ---------------------------------------------------------------------------

def run_gate(sheets):
    lines = []
    all_fit = True

    # 1. per-sheet: every part inside the usable area of its OWN sheet?
    for si, sheet in enumerate(sheets, start=1):
        maxx = maxy = -1e9
        minx = miny = 1e9
        for f in sheet["placed"]:
            bb = f.bounding_box()
            maxx = max(maxx, bb.max.X); maxy = max(maxy, bb.max.Y)
            minx = min(minx, bb.min.X); miny = min(miny, bb.min.Y)
        fits = (maxx <= SHEET_W - SHEET_MARGIN + 0.5) and \
               (maxy <= SHEET_H - SHEET_MARGIN + 0.5) and \
               (minx >= SHEET_MARGIN - 0.5) and (miny >= SHEET_MARGIN - 0.5)
        all_fit = all_fit and fits
        npart = len(sheet["placed"])
        lines.append(
            f"[{'PASS' if fits else 'FAIL'}] sheet {si}: {npart} parts inside "
            f"{int(SHEET_W)}x{int(SHEET_H)} (envelope {maxx-minx:.0f} x "
            f"{maxy-miny:.0f} mm)")

    # 2. dogbone geometry actually verified, not asserted: on a fresh side
    #    profile, every CIRCLE edge centre must coincide with a slot rectangle
    #    corner (within tol). If math were wrong (circle inside the slot), the
    #    centre would sit off the corner and this FAILS.
    sp = side_profile()
    circle_centres = []
    for e in sp.edges():
        if e.geom_type == GeomType.CIRCLE:
            c = e.arc_center
            circle_centres.append((round(c.X, 3), round(c.Y, 3), round(e.radius, 3)))
    n_circ = len(circle_centres)
    expected = N_SHELVES * N_TABS * 4   # 4 dogbones per slot
    radii_ok = all(abs(r - DOG_R) < 0.05 for _, _, r in circle_centres)
    # check each circle centre is on a slot corner: slot half-extent is
    # TAB_W/2 in X-from-slot-centre and (T+SLOT_FIT)/2 in Y. Build the set of
    # valid corner offsets and confirm each circle centre matches one slot.
    tab_pitch = DEPTH / (N_TABS + 1)
    half_w = TAB_W / 2
    half_h = (T + SLOT_FIT) / 2
    slot_centres = []
    for cy in SHELF_CY:
        y = cy - HEIGHT / 2
        for k in range(1, N_TABS + 1):
            x = -DEPTH / 2 + k * tab_pitch
            slot_centres.append((x, y))
    def on_a_corner(px, py):
        for sx, sy in slot_centres:
            for ox in (-half_w, half_w):
                for oy in (-half_h, half_h):
                    if abs(px - (sx + ox)) < 0.02 and abs(py - (sy + oy)) < 0.02:
                        return True
        return False
    corners_ok = all(on_a_corner(px, py) for px, py, _ in circle_centres)
    dog_ok = (n_circ == expected) and radii_ok and corners_ok
    lines.append(
        f"[{'PASS' if dog_ok else 'FAIL'}] dogbones: {n_circ}/{expected} circles, "
        f"r=={DOG_R}mm:{radii_ok}, every circle centred ON a slot corner:"
        f"{corners_ok}. (Square tabs seat only if this PASSes.)")

    # 3. slots actually present in the side (holes survived modelling)
    #    A bare rectangle side has 1 face/wire; with slots it has interior wires.
    n_inner = len(sp.wires()) - 1  # outer wire + N interior slot wires
    slots_ok = n_inner >= N_SHELVES * N_TABS
    lines.append(
        f"[{'PASS' if slots_ok else 'FAIL'}] side panel has {n_inner} interior "
        f"cut-outs (expect >= {N_SHELVES*N_TABS} slots).")

    # 4. material-dependent reminders (cannot be auto-verified here)
    lines.append(f"[CHECK] slot width = measured thickness {T} + fit {SLOT_FIT} = "
                 f"{T+SLOT_FIT}mm. RE-MEASURE your real sheet and set "
                 f"THICK_MEASURED before cutting.")
    lines.append(f"[{'PASS' if abs(TAB_LEN-T)<0.01 else 'WARN'}] tab length "
                 f"{TAB_LEN} == material {T} (tabs sit flush with outer face).")

    ok = all_fit and dog_ok and slots_ok
    return ok, lines


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    out = lambda n: os.path.join(here, n)

    print("Building assembly...")
    asm = build_assembly()
    print("Exporting isometric -> bookcase_iso.png")
    export_isometric(asm, out("bookcase_iso.png"))

    print("Nesting parts across sheets...")
    sheets = build_nest()
    print("Exporting nest preview -> bookcase_nest.png")
    export_nest_png(sheets, out("bookcase_nest.png"))
    print("Exporting cuttable DXFs (one per sheet)...")
    dxfs = export_cut_dxf(sheets, out("bookcase_cut.dxf"))
    for p in dxfs:
        print("  wrote", os.path.basename(p))

    print("\n=== PRE-CUT GATE ===")
    ok, report = run_gate(sheets)
    for r in report:
        print("  " + r)
    print("  RESULT:", "ALL CHECKS PASS" if ok else "BLOCKED - fix FAILs above")
    print("====================\n")
    print("Done.")
