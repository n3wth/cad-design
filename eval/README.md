# Skill eval

Does the `cad-design` skill actually make an agent produce better build docs than no skill? This is the RED/GREEN test skill-authoring specs prescribe: measure baseline behavior, then behavior with the skill present, and compare.

## What it measures

For each prompt, an agent generates a build doc **with the skill injected** and **without it**, repeated over several trials. An independent judge then scores every doc, blind to its condition, against the skill's own rubric:

| Criterion | Passes when the response… |
|---|---|
| `interviewed_first` | asks clarifying questions before designing, not one-shot |
| `isometric_drawing` | produces/specifies a real isometric or CAD drawing (not a dimensions table or ASCII sketch) |
| `collaborative_loop` | frames the design as iterative with concrete follow-up prompts |
| `precut_gate` | includes an explicit check to run before cutting |
| `tools_not_have` | accounts for tools the user lacks, so joinery stays buildable |

If the skill adds value, the **with** column beats **without**. If a criterion shows little lift, that is a concrete signal to revise the skill text.

## Run it

```bash
./eval/run-eval.sh
```

The runner inlines the current `../SKILL.md` body into a generated copy of the workflow, so the eval always tests the shipped skill — never a stale one. (Inlining, not `args`: the Workflow args channel does not reliably carry large multi-line strings.) It prints the exact `Workflow({...})` call to run from Claude Code.

Defaults: 5 prompts × {with, without} × 3 trials = 30 docs generated and judged. Edit the `PROMPTS`/`TRIALS` in `skill-eval.workflow.js` to change the matrix.

## What the eval found

Running it on v2.0.0 returned a near-null result: 3.40 vs 3.33 criteria met (within noise), and the headline `isometric_drawing` criterion fired only 20% even with the skill — base models read "use build123d" but, in a chat turn, just write a dimensions table. v2.1.0 makes the drawing a mandatory first step with a no-code fallback (inline SVG / 3D ASCII), targeting that exact gap. Re-run after any skill edit to confirm the lift holds.

## Output

A scorecard: per-criterion pass rate (with vs without) and the lift, plus the average criteria met per doc in each condition.

## Files

- `skill-eval.workflow.js` — the eval (Claude Code Workflow script).
- `run-eval.sh` — feeds the live `SKILL.md` body to the workflow.
