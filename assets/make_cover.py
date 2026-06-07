import re

# Pull the inner drawing (everything between <svg ...> and </svg>) of the iso
iso = open('cover-iso.svg').read()
inner = iso[iso.index('>', iso.index('<svg'))+1 : iso.rindex('</svg>')]
ISO_W, ISO_H = 385, 540

# The iso canvas (540 tall) has empty space + trailing dotted construction lines, so the
# SHELF BODY's visual center is not the canvas center. Find the solid-edge bounds and the
# full content bounds so we can center on what the eye reads as the shelf.
import re as _re
_xs=[]; _ys=[]; _solid_ys=[]; _solid_xs=[]
for _m in _re.finditer(r'<line x1="([\d.]+)" y1="([\d.]+)" x2="([\d.]+)" y2="([\d.]+)" stroke="(#[0-9a-f]+)"', iso):
    _x1,_y1,_x2,_y2,_c=_m.groups()
    _xs+= [float(_x1),float(_x2)]; _ys+= [float(_y1),float(_y2)]
    if _c=="#ffffff":
        _solid_xs+= [float(_x1),float(_x2)]; _solid_ys+= [float(_y1),float(_y2)]
BODY_CX=(min(_solid_xs)+max(_solid_xs))/2     # iso-space center x of the solid shelf
BODY_CY=(min(_solid_ys)+max(_solid_ys))/2     # iso-space center y of the solid shelf
BODY_H=max(_ys)-min(_ys)                        # full content height (incl construction lines)

BG    = "#0b0b0d"   # near-black blueprint card
GRID  = "#1c1c22"   # faint grid
INK   = "#ffffff"
SUB   = "#8a8a94"
ACCENT= "#e5e5ea"

def grid(w, h, step=40):
    lines=[]
    x=0
    while x<=w:
        lines.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{h}" stroke="{GRID}" stroke-width="1"/>'); x+=step
    y=0
    while y<=h:
        lines.append(f'<line x1="0" y1="{y}" x2="{w}" y2="{y}" stroke="{GRID}" stroke-width="1"/>'); y+=step
    return "\n".join(lines)

def banner(W, H, iso_scale, iso_cx, title_y, out, pad=28):
    # Place so the SOLID shelf body's center lands at (iso_cx, H/2).
    # translate t makes: t + BODY_C*scale = target  ->  t = target - BODY_C*scale
    iso_x = iso_cx - BODY_CX*iso_scale
    iso_y = H/2 - BODY_CY*iso_scale
    S=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="ui-sans-serif,-apple-system,system-ui,sans-serif">']
    S.append(f'<rect width="{W}" height="{H}" fill="{BG}"/>')
    S.append(grid(W,H))
    # left text block
    S.append(f'<text x="80" y="{title_y}" font-size="86" font-weight="800" fill="{INK}" letter-spacing="-2">cad-design</text>')
    S.append(f'<text x="82" y="{title_y+52}" font-size="30" font-weight="500" fill="{SUB}">design furniture with AI, then cut it</text>')
    S.append(f'<text x="82" y="{title_y+150}" font-size="20" font-weight="600" fill="{ACCENT}" font-family="ui-monospace, monospace">npx skills add n3wth/cad-design</text>')
    # iso on the right, bigger and vertically centered
    S.append(f'<g transform="translate({round(iso_x,1)},{round(iso_y,1)}) scale({iso_scale})">{inner}</g>')
    S.append('</svg>')
    open(out,'w').write("\n".join(S))
    print("wrote", out, W, "x", H, "| body center ->", round(iso_cx), round(H/2))

# README banner 1280x480 — bigger iso, vertically centered, right third
banner(1280, 480, 0.80, 1010, 230, 'cover-banner.svg')
# Social card 1280x640 — even bigger iso, vertically centered
banner(1280, 640, 1.08, 1000, 300, 'cover-social.svg')
