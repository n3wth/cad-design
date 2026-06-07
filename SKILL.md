---
name: cad-design
description: Use when helping someone design a physical build (shelves, desk, bench, planter, cabinet, anything cut from wood/sheet goods) with AI, especially for a beginner or someone with shop access (power tools, CNC router, table saw). Produces a reusable doc with an isometric drawing, a parameterized prompt, a worked example, and a pre-cut verification gate.
metadata:
  author: n3wth
  version: "1.0.0"
---

# Designing Physical Builds With AI

## Overview

Help a person turn a vague build idea ("I want some shelves") into a buildable artifact they can keep and reuse. The deliverable is a **document** (Notion page, markdown file) containing: an isometric drawing of the piece, a copy-paste prompt, a worked example, the back-and-forth refinement loop, and a verification gate before anything gets cut.

**Core principle:** A cut list is abstract; a drawing is real. And a build is a *conversation* with the AI, not a one-shot — the doc must teach both.

## What agents already do well (don't re-teach)

Baseline testing showed agents reliably produce, unprompted:
- A parameterized copy-paste prompt with fill-in blanks
- Hard-coded toolset INCLUDING an explicit "tools I do NOT have" list (stops the AI assuming a table saw / pocket jig)
- An "interview me first" instruction
- A cut-list table, priced shopping list, and standard safety facts (stud-mounting, nominal-vs-real lumber e.g. 1x4 = ¾"×3½", ~⅛" saw kerf)

So your prompt and cut-list content can lean on the model's defaults. Spend your effort on the four things below, which agents skip.

## The four things to ADD (agents skip these)

### 1. An isometric drawing of the finished piece
Numbers don't let a beginner picture the object. Include a real isometric drawing of the finished piece with W×H×D labeled.

**Primary tool: `build123d` (Python, parametric CAD on Open Cascade) — do NOT hand-roll an SVG projection.** Why this and not an SVG iso library: build123d models the piece *once* in real mm and gives you BOTH a true hidden-line isometric render AND a cuttable DXF/STEP export from the same model. The drawing and the toolpath can't drift apart — which is exactly the failure mode the verification gate (below) exists to prevent. An SVG-only iso library draws lines but knows nothing about the geometry, so its picture and your cut list are independent and can disagree.

`assets/shelf.py` is a verified, runnable example (build123d 0.10 on Python 3.12). Setup and run:

```bash
python3.12 -m venv venv && ./venv/bin/pip install build123d   # OCP is large; minutes, may flake on slow pypi — retry
./venv/bin/python assets/shelf.py                              # writes shelf-iso.svg + side-panel.dxf
rsvg-convert shelf-iso.svg -o shelf-iso.png                   # then LOOK at it
```

Core of the model (full version in `assets/shelf.py`):

```python
from build123d import *
W, H, D, T, N = 800, 1800, 300, 18, 4   # mm; N interior shelves
with BuildPart() as shelf:
    with Locations((-(W/2-T/2),0,0), ((W/2-T/2),0,0)): Box(T, D, H)        # sides
    with Locations((0,0,H/2-T/2), (0,0,-(H/2-T/2))):   Box(W-2*T, D, T)    # top+bottom
    clear = H - 2*T
    for i in range(1, N+1):
        with Locations((0,0,-clear/2 + clear*i/(N+1))): Box(W-2*T, D, T)   # shelves
part = shelf.part
exporter = ExportSVG(scale=0.18); exporter.add_layer("solid", line_weight=0.5)
visible, _ = part.project_to_viewport(viewport_origin=(1600,-1600,1200), viewport_up=(0,0,1), look_at=(0,0,0))
exporter.add_shape(visible, layer="solid"); exporter.write("shelf-iso.svg")  # auto-framed by viewBox
```

- **Always render and LOOK** before shipping — and look at it on the *actual destination*, not just a white preview. The strokes are dark; on a dark-themed page (e.g. Notion dark mode) a transparent PNG makes the drawing vanish. Bake a white background: `rsvg-convert --background-color=white in.svg -o out.png`.
- Add W/H/D labels + caption by appending `<text>`/`<line>` to the SVG (build123d draws geometry, not annotations).
- **Version pin matters:** install into a Python 3.12 venv. On 3.14 the resolver pulled an OCP build missing `HashCode` and the model errored — a real trap worth avoiding.

**Fallbacks (use only when build123d is overkill or unavailable):**
- *Interactive web drawing:* `@elchininet/isometric` (TS, runs in browser or Node-with-jsdom). Clean lines, but no auto-fit and no DXF — you tune scale/offset by hand.
- *Vibe-only render (not measurable):* AI text→image/3D (Meshy, Tripo, ZSky). Good to show "the look"; never use its dimensions for cutting.

### 2. Frame it as a collaborative LOOP, not a one-shot
The doc must show the refinement that follows the first answer. Include 3–4 concrete follow-up prompts as examples:
- "Make it 20 cm shorter and add one more shelf."
- "I only have 15 mm ply, not 18 — redo the cut list and joinery."
- "Swap the dados for screwed cleats; I don't have a router bit for dados."
- "Nest the parts to waste less of the sheet, and show me the leftover."

This is the single biggest thing that turns "AI gave me a plan" into "I designed this with AI."

### 3. A pre-cut verification gate (AI dimensions are NOT gospel)
Sheet goods and CNC time cost money; an AI off-by-one ruins a sheet. Put a short, blocking checklist before any cutting:
- Re-add every part against the stock size — do the parts actually fit one 8×4 (2440×1220 mm) sheet with kerf/spacing gaps?
- Confirm material thickness matches what joinery assumes (an 18 mm dado is wrong for 15 mm ply).
- Dry-fit / cardboard mock the tricky joint before committing.
- Hand the "questions for your CNC operator" list to whoever runs the machine (holddown, tabs, bit diameter, file format — DXF/SVG, units).
- **CNC-specific:** an AI-generated DXF/SVG must be opened and measured in CAD before it touches the machine. Treat AI geometry as a draft, never a toolpath. The clean path for real parts: rebuild the final geometry in **FreeCAD** (free, parametric, Python-scriptable, has woodworking cutlist workbenches + CAM for toolpaths) and export the toolpath from there — don't cut from an LLM-authored DXF.

### 4. Make it a durable, reusable artifact
Write it where they'll find it again (Notion page, repo file), and end with a reuse note: "Change only the fill-in blanks to design the next build." One doc, many builds.

## Quick reference

| Section of the doc | Source |
|---|---|
| Isometric drawing (hero) | You generate it — agents skip this |
| Setup line (tools available, skill level, helper) | Prompt blanks |
| Copy-paste prompt w/ "tools I do NOT have" | Model default — let it write this |
| Worked example (cut list, sheet yield, joinery, assembly) | Model default |
| Collaborative follow-up prompts | You add this — agents skip it |
| Pre-cut verification gate | You add this — agents skip it |
| Reuse note | You add this |

## Common mistakes

- **Shipping numbers without a picture.** The drawing is the point for a beginner. Don't skip it because "the cut list has the dimensions."
- **Hand-rolling the iso projection.** Model it in build123d (`assets/shelf.py`); then render and look. Every time.
- **One-shot framing.** If the doc reads as "here's your plan," you failed the collaborative goal. Show the loop.
- **Letting AI geometry reach the CNC unverified.** Always gate on a CAD measure-check.
- **Over-styling the drawing.** Flat fills, labeled edges. No 3D-render shading.

## Tailoring to skill level

- **Beginner (hung shelves, used a drill):** define every term on first use (kerf, dado, nominal). Prefer joinery that needs no special bit (screwed cleats, pocket holes if they have the jig). Keep the first build a guaranteed win.
- **Has a helper running the CNC:** the prompt MAY request precision sheet parts, because the operator handles the machine. Note this in the setup line so the AI doesn't dumb down the design.
