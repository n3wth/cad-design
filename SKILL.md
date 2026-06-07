---
name: cad-design
description: Use when helping someone design a physical build (shelves, desk, bench, planter, cabinet, anything cut from wood or sheet goods) with AI, especially for a beginner or someone with shop access (power tools, CNC router, table saw). Produces a reusable doc with an isometric drawing, a parameterized prompt, a worked example, and a pre-cut verification gate.
argument-hint: [what to build, e.g. "freestanding bookshelf 1.8m"]
metadata:
  author: n3wth
  version: "1.1.0"
---

# cad-design

## Overview

Turn a vague build idea ("I want some shelves") into a document the person keeps and reuses: an isometric drawing of the piece, a copy-paste prompt, a worked example, a back-and-forth refinement loop, and a verification gate before anything gets cut.

**Core principle:** A cut list is abstract; a drawing is real. A build is a *conversation* with the AI, not a one-shot — the doc must teach both.

## Quick start

1. Generate the isometric drawing and a CNC DXF from the parametric model — run [shelf.py](assets/shelf.py) (see [Generating the drawing](#generating-the-drawing)).
2. Assemble the doc with the six sections in [Quick reference](#quick-reference).
3. Add the four things agents skip (drawing, collaborative loop, pre-cut gate, durable artifact).
4. Run the pre-cut verification gate before any cutting.

## What agents already do well — do not re-teach

Baseline testing shows agents reliably produce, unprompted:

- A parameterized copy-paste prompt with fill-in blanks.
- A hard-coded toolset including an explicit "tools I do NOT have" list (stops the AI assuming a table saw or pocket jig).
- An "interview me first" instruction.
- A cut-list table, priced shopping list, and standard safety facts (stud-mounting, nominal-vs-real lumber e.g. 1x4 = ¾"×3½", ~⅛" saw kerf).

Lean on the model's defaults for prompt and cut-list content. Spend effort on the four things below, which agents skip.

## The four things to ADD

### 1. An isometric drawing of the finished piece

Numbers do not let a beginner picture the object. Include a real isometric drawing with W×H×D labeled.

**Primary tool: `build123d` (Python, parametric CAD on Open Cascade) — do NOT hand-roll an SVG projection.** build123d models the piece once in real mm and produces BOTH a hidden-line isometric render AND a cuttable DXF/STEP from the same model, so the drawing and the toolpath cannot drift apart. An SVG-only iso library draws lines but knows nothing about the geometry, so its picture and the cut list are independent and can disagree.

Three bundled scripts (all verified on build123d 0.10, Python 3.12):

- [shelf.py](assets/shelf.py) — parametric model → isometric SVG + CNC DXF. Edit `W, H, D, T, N` for any box-carcass build.
- [shelf-blueprint.py](assets/shelf-blueprint.py) — renders a refined blueprint iso: dashed hidden edges for depth, line-weight hierarchy, and isometric dimension callouts. Produces the dimensioned drawing.
- [make_cover.py](assets/make_cover.py) — builds a cover banner and social card from the iso.

#### Generating the drawing

```bash
# OCP is large; install takes minutes and may flake on slow pypi — retry
python3.12 -m venv venv && ./venv/bin/pip install build123d

# writes shelf-iso.svg + side-panel.dxf
./venv/bin/python assets/shelf.py .

# bake a white background, then LOOK at it
rsvg-convert --background-color=white shelf-iso.svg -o shelf-iso.png
```

Rules that prevent the failures hit while building this skill:

- **Render and LOOK on the actual destination, not a white preview.** Strokes are dark; on a dark page (Notion dark mode, GitHub dark) a transparent PNG vanishes. Bake a white background with `--background-color=white`.
- **Project dimension lines as 3D edges through the same viewport as the model.** Hand-computed screen angles produce callouts that do not follow the isometric axes. See `base_dim` / the projected-edge approach in [shelf-blueprint.py](assets/shelf-blueprint.py).
- **Pin Python 3.12.** On 3.14 the resolver pulls an OCP build missing `HashCode` and the model errors.
- **Reuse a fresh image filename when re-publishing to GitHub.** GitHub's camo CDN caches images by URL; overwriting `shelf-iso.png` serves the stale copy.

**Fallbacks** (use only when build123d is overkill or unavailable):

- *Interactive web drawing:* [`@elchininet/isometric`](https://github.com/elchininet/isometric) (TypeScript, browser or Node-with-jsdom). Clean lines, but no auto-fit and no DXF.
- *Vibe-only render (not measurable):* AI text→image/3D (Meshy, Tripo, ZSky). Good to show "the look"; never use its dimensions for cutting.

### 2. Frame it as a collaborative LOOP, not a one-shot

Show the refinement that follows the first answer. Include 3–4 concrete follow-up prompts:

- "Make it 20 cm shorter and add one more shelf."
- "I only have 15 mm ply, not 18 — redo the cut list and joinery."
- "Swap the dados for screwed cleats; I do not have a router bit for dados."
- "Nest the parts to waste less of the sheet, and show me the leftover."

This loop is what turns "the AI gave me a plan" into "I designed this with AI."

### 3. A pre-cut verification gate — AI dimensions are NOT gospel

Sheet goods and CNC time cost money; an AI off-by-one ruins a sheet. Put a blocking checklist before any cutting:

- Re-add every part against the stock size — do the parts fit one 8×4 (2440×1220 mm) sheet with kerf and spacing gaps?
- Confirm material thickness matches what the joinery assumes (an 18 mm dado is wrong for 15 mm ply).
- Dry-fit or cardboard-mock the tricky joint before committing.
- Hand the "questions for your CNC operator" list to whoever runs the machine (holddown, tabs, bit diameter, file format and units).
- **CNC-specific:** open and measure any AI-generated DXF in CAD before it touches the machine. Treat AI geometry as a draft, never a toolpath. For real parts, rebuild the final geometry in FreeCAD (free, parametric, Python-scriptable, with woodworking cutlist workbenches and CAM) and export the toolpath from there.

### 4. Make it a durable, reusable artifact

Write the doc where the person will find it again (Notion page, repo file). End with a reuse note: "Change only the fill-in blanks to design the next build." One doc, many builds.

## Quick reference

| Section of the doc | Source |
|---|---|
| Isometric drawing (hero) | Generate it — agents skip this |
| Setup line (tools available, skill level, helper) | Prompt blanks |
| Copy-paste prompt with "tools I do NOT have" | Model default — let it write this |
| Worked example (cut list, sheet yield, joinery, assembly) | Model default |
| Collaborative follow-up prompts | Add this — agents skip it |
| Pre-cut verification gate | Add this — agents skip it |
| Reuse note | Add this |

## Examples

**Invoke:** `/cad-design freestanding bookshelf, ~1.8m tall, plywood, beginner with a CNC`

**Produces:** a document with —

1. An isometric drawing (hero), generated by [shelf.py](assets/shelf.py) / [shelf-blueprint.py](assets/shelf-blueprint.py), W×H×D labeled.
2. A setup line stating tools available, skill level, and whether an operator runs the CNC.
3. A copy-paste prompt with fill-in blanks and a "tools I do NOT have" list.
4. A worked example: cut list, sheet yield from one 8×4, joinery, assembly steps.
5. 3–4 collaborative follow-up prompts (the refinement loop).
6. A pre-cut verification gate.
7. A reuse note.

**Reference output:** the freestanding bookshelf at [github.com/n3wth/cad-design](https://github.com/n3wth/cad-design) — 800 × 1800 × 300 mm, 4 shelves, 18 mm ply, cuts from one 8×4 sheet.

## Common mistakes

- **Shipping numbers without a picture.** The drawing is the point for a beginner. Do not skip it because "the cut list has the dimensions."
- **Hand-rolling the iso projection.** Model it in build123d; then render and look. Every time.
- **Flat dimension callouts on an isometric drawing.** Project the dimension lines as 3D edges through the same viewport so they follow the iso axes.
- **One-shot framing.** If the doc reads as "here is your plan," it failed the collaborative goal. Show the loop.
- **Letting AI geometry reach the CNC unverified.** Always gate on a CAD measure-check.
- **Over-styling the drawing.** Flat fills, labeled edges. No 3D-render shading, no shadows, no gradients.

## Tailoring to skill level

- **Beginner (hung shelves, used a drill):** define every term on first use (kerf, dado, nominal). Prefer joinery that needs no special bit (screwed cleats, or pocket holes if a jig is available). Keep the first build a guaranteed win.
- **Has a helper running the CNC:** the prompt MAY request precision sheet parts, because the operator handles the machine. State this in the setup line so the AI does not dumb down the design.
