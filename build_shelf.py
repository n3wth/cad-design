"""
Freestanding bookshelf -> isometric drawing + CNC side-panel DXF, ONE model.
Joinery: shelves screwed into cleats / screwed through sides on a marked pilot line.
The side-panel DXF carries the shelf CENTER-LINES and pilot holes so the CNC does
the layout (no hand-measuring shelf positions). Iso + DXF come from the same numbers.
Verified: build123d 0.10, Python 3.12.
"""
import re
from build123d import *
from build123d.exporters import ColorIndex

# ---- design parameters (verified to nest on one 8x4 sheet, 8mm margin, see margin_check) ----
W, H, D, T, N = 800, 1800, 290, 18, 4
VP = dict(viewport_origin=(1600,-1600,1200), viewport_up=(0,0,1), look_at=(0,0,0))

# shelf center-heights from the bottom of the carcass (interior shelves, evenly spaced)
clear = H - 2*T
shelf_centers_from_bottom = [T + (clear*i/(N+1)) + (-T/2 + T/2) for i in range(1,N+1)]
# simpler & exact: interior shelf centerline z (origin-centered model) then convert to from-bottom
shelf_z = [-clear/2 + clear*i/(N+1) for i in range(1,N+1)]
shelf_from_bottom = [round(z + H/2,1) for z in shelf_z]

# ---------- 3D model (same as skill model, D updated) ----------
with BuildPart() as shelf:
    with Locations((-(W/2-T/2),0,0), ((W/2-T/2),0,0)): Box(T, D, H)
    with Locations((0,0,H/2-T/2), (0,0,-(H/2-T/2))):   Box(W-2*T, D, T)
    for z in shelf_z:
        with Locations((0,0,z)): Box(W-2*T, D, T)
part = shelf.part
visible, hidden = part.project_to_viewport(**VP)

def edges_to_lines(edges):
    out=[]
    for e in edges:
        vs=e.vertices()
        if len(vs)>=2: out.append(((vs[0].X,vs[0].Y),(vs[-1].X,vs[-1].Y)))
    return out
vis_l=edges_to_lines(visible); hid_l=edges_to_lines(hidden)

hw,hd,hh=W/2,D/2,H/2
def proj_seg(p0,p1):
    e=Edge.make_line(p0,p1); v,_=e.project_to_viewport(**VP); vs=v.vertices()
    return ((vs[0].X,vs[0].Y),(vs[-1].X,vs[-1].Y))
OH=320
dim_H=proj_seg((-hw-OH,-hd-OH,-hh),(-hw-OH,-hd-OH,hh))
dim_Hw1=proj_seg((-hw,-hd,-hh),(-hw-OH,-hd-OH,-hh)); dim_Hw2=proj_seg((-hw,-hd,hh),(-hw-OH,-hd-OH,hh))
OW=360
dim_W=proj_seg((-hw,-hd,-hh-OW),(hw,-hd,-hh-OW))
dim_Ww1=proj_seg((-hw,-hd,-hh),(-hw,-hd,-hh-OW)); dim_Ww2=proj_seg((hw,-hd,-hh),(hw,-hd,-hh-OW))
OD=360
dim_D=proj_seg((hw,-hd,-hh-OD),(hw,hd,-hh-OD))
dim_Dw1=proj_seg((hw,-hd,-hh),(hw,-hd,-hh-OD)); dim_Dw2=proj_seg((hw,hd,-hh),(hw,hd,-hh-OD))
dim_all=[dim_H,dim_Hw1,dim_Hw2,dim_W,dim_Ww1,dim_Ww2,dim_D,dim_Dw1,dim_Dw2]
allpts=[p for L in (vis_l,hid_l) for seg in L for p in seg]+[p for seg in dim_all for p in seg]
xs=[p[0] for p in allpts]; ys=[p[1] for p in allpts]
minx,maxx,miny,maxy=min(xs),max(xs),min(ys),max(ys); cw=maxx-minx; ch=maxy-miny
scale=0.16; PAD,PAD_B=40,96
CAPTION=f"{N} shelves · {T} mm plywood · nests on one 8×4 sheet"
content_w=cw*scale+PAD*2; Wpx=round(max(content_w,len(CAPTION)*6.6+48)); Hpx=round(ch*scale+PAD*2+PAD_B)
x_shift=(Wpx-content_w)/2
def X(x): return round((x-minx)*scale+PAD+x_shift,1)
def Yt(y): return round((maxy-y)*scale+PAD,1)
INK="#1d1d1f"; THIN="#9a9aa0"
S=[]; S.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {Wpx} {Hpx}" width="{Wpx}" height="{Hpx}" font-family="ui-sans-serif,system-ui,sans-serif">')
S.append(f'<rect width="{Wpx}" height="{Hpx}" fill="white"/>')
def Ln(seg,stroke,w,dash=None):
    (a,b)=seg; d=f' stroke-dasharray="{dash}"' if dash else ''
    S.append(f'<line x1="{X(a[0])}" y1="{Yt(a[1])}" x2="{X(b[0])}" y2="{Yt(b[1])}" stroke="{stroke}" stroke-width="{w}"{d} stroke-linecap="round"/>')
def mid(seg): a,b=seg; return ((a[0]+b[0])/2,(a[1]+b[1])/2)
for seg in hid_l: Ln(seg,THIN,0.8,dash="3 3")
for seg in vis_l: Ln(seg,INK,1.5)
for w in (dim_Hw1,dim_Hw2,dim_Ww1,dim_Ww2,dim_Dw1,dim_Dw2): Ln(w,THIN,0.9,dash="1 3")
for d in (dim_H,dim_W,dim_D): Ln(d,THIN,1.1,dash="1 3")
def dl(seg,txt,dx=0,dy=0,rot=None):
    mx,my=mid(seg); sx,sy=X(mx)+dx,Yt(my)+dy
    tr=f' transform="rotate({rot} {sx} {sy})"' if rot is not None else ''
    S.append(f'<text x="{sx}" y="{sy}" font-size="15" font-weight="600" fill="{INK}" text-anchor="middle" dominant-baseline="middle"{tr}>{txt}</text>')
dl(dim_H,f"{H} mm",dx=-12,rot=-90); dl(dim_W,f"{W} mm",dx=-14,dy=16); dl(dim_D,f"{D} mm",dx=14,dy=16)
cap_cx=Wpx/2; capy=Hpx-50
S.append(f'<text x="{cap_cx}" y="{capy}" font-size="17" font-weight="700" fill="{INK}" text-anchor="middle">Freestanding bookshelf</text>')
S.append(f'<text x="{cap_cx}" y="{capy+22}" font-size="13" fill="#6b6b70" text-anchor="middle">{CAPTION}</text>')
S.append('</svg>')
open('/Users/oliver/code/cad-design/shelf-iso.svg','w').write("\n".join(S))

# ---------- side-panel DXF WITH shelf center-lines + pilot holes ----------
# Panel local coords: 0..D (x) by 0..H (y). Outline + a dashed centerline at each
# shelf z + 2 pilot holes per shelf (cut as 4mm circles for screws from the side).
dxf=ExportDXF(unit=Unit.MM)
dxf.add_layer("CUT", color=ColorIndex.BLACK)    # outline -> cut
dxf.add_layer("MARK", color=ColorIndex.BLUE)    # shelf centerlines -> engrave/score
dxf.add_layer("DRILL", color=ColorIndex.RED)    # pilot holes -> drill/peck
outline=Rectangle(D,H,align=(Align.MIN,Align.MIN)).wire()  # D wide x H tall, origin at corner
dxf.add_shape(outline, layer="CUT")
PILOT=4.0
for z in shelf_z:
    yb=z+H/2     # center height from bottom = panel y
    line=Edge.make_line((0,yb,0),(D,yb,0))
    dxf.add_shape(line, layer="MARK")
    for px in (D*0.25, D*0.75):
        c=Circle(PILOT/2).located(Location((px,yb,0)))
        dxf.add_shape(c.wire(), layer="DRILL")
dxf.write('/Users/oliver/code/cad-design/side-panel.dxf')
print("OK D=%d  shelf centers from bottom (mm): %s" % (D, shelf_from_bottom))
