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

Two runs (30 docs each, blind-judged), `isometric_drawing` lift in bold:

| Version | avg criteria (with / without) | isometric_drawing (with / without) |
|---|---|---|
| v2.0.0 | 3.40 / 3.33 | **20% / 20%** (lift 0) |
| v2.1.0 ("MANDATORY drawing") | 3.33 / 3.20 | **20% / 40%** (lift −20) |

The finding that shaped the skill: **you cannot make a chat-turn model produce a real isometric drawing by instructing it** — even forceful "this is mandatory, a table is NOT a drawing" language left it at 20%. The drawing only happens when an agent can actually *run* `build123d`. So v2.2.0 stopped overclaiming and reframed the skill around its real value: the execution pipeline (run the model → render + DXF), the pre-cut gate, and the maker judgment. The other criteria (interview-first, collaborative loop, tools-not-have) the base model mostly already does; the skill nudges them slightly.

Lesson for skill authors: instruction strength is not a lever for capabilities the model can't execute in context. Measure, don't assume.

## Output

A scorecard: per-criterion pass rate (with vs without) and the lift, plus the average criteria met per doc in each condition.

## Files

- `skill-eval.workflow.js` — the eval (Claude Code Workflow script).
- `run-eval.sh` — feeds the live `SKILL.md` body to the workflow.
