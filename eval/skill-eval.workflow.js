// cad-design skill eval — A/B: does the skill make agents produce better build
// docs than no skill? Run via eval/run-eval.sh, which feeds the LIVE SKILL.md
// text in through `args` so the eval never tests stale skill content.
//
//   args = { skill: <SKILL.md body>, prompts?: string[], trials?: number }
//
// Method (the RED/GREEN pattern skill-authoring specs prescribe): for each
// prompt, generate a build doc WITH the skill injected and WITHOUT it, repeated
// over N trials, then score every doc blind against the skill's own rubric.

export const meta = {
  name: 'cad-design-skill-eval',
  description: 'A/B eval: does the cad-design skill beat no-skill on its own rubric?',
  phases: [
    { title: 'Generate', detail: 'prompts x {with-skill, no-skill} x trials build docs' },
    { title: 'Judge', detail: 'blind rubric scoring of each doc on 5 criteria' },
  ],
}

const SKILL = args && args.skill
if (!SKILL) throw new Error('Pass the SKILL.md body via args.skill (use eval/run-eval.sh).')

const PROMPTS = (args && args.prompts) || [
  "My friend wants to build a set of shelves with AI. She's a moderate DIYer with power tools and access to an 8x4 CNC. Help her design them.",
  'I want to build a simple desk for my home office. Help me design it so I can build it myself.',
  'Help me design a wooden planter box for my balcony that I can build this weekend.',
  "I'd like to make a small bookshelf for my kid's room. Can you help me design it to build?",
  'Design a workbench for my garage that I can cut and assemble myself.',
]
const TRIALS = (args && args.trials) || 3

const RUBRIC_SCHEMA = {
  type: 'object',
  properties: {
    interviewed_first: { type: 'boolean', description: 'Asked clarifying questions BEFORE giving a full design/cut list, rather than answering one-shot' },
    isometric_drawing: { type: 'boolean', description: 'Produced or concretely specified a real isometric/3D drawing of the finished piece (an actual drawing, generated image, or build123d/CAD model — NOT just a dimensions table and NOT a rough ASCII sketch)' },
    collaborative_loop: { type: 'boolean', description: 'Explicitly framed the design as iterative and offered concrete follow-up/refinement prompts the user can send back' },
    precut_gate: { type: 'boolean', description: 'Included an explicit verification/check step to do BEFORE cutting (e.g. re-measure, dry-fit, verify parts fit the sheet, check the file)' },
    tools_not_have: { type: 'boolean', description: 'Accounted for which tools the user does NOT have, so joinery never assumes equipment they lack' },
    notes: { type: 'string', description: 'One sentence of evidence for the scores' },
  },
  required: ['interviewed_first', 'isometric_drawing', 'collaborative_loop', 'precut_gate', 'tools_not_have', 'notes'],
}

const CELLS = []
PROMPTS.forEach((p, pi) => {
  for (const cond of ['with', 'without']) {
    for (let t = 0; t < TRIALS; t++) CELLS.push({ pi, prompt: p, cond, trial: t })
  }
})

phase('Generate')
const results = await pipeline(
  CELLS,
  (cell) => {
    const sys = cell.cond === 'with'
      ? `You have a skill loaded. Follow it exactly when responding:\n\n<skill name="cad-design">\n${SKILL}\n</skill>\n\nUser request: ${cell.prompt}`
      : `User request: ${cell.prompt}\n\nRespond as you normally would to help them.`
    return agent(sys, { label: `gen:p${cell.pi}:${cell.cond}:t${cell.trial}`, phase: 'Generate' })
      .then((doc) => ({ ...cell, doc }))
  },
  (gen) => {
    if (!gen || !gen.doc) return null
    const judgePrompt = `You are scoring an AI assistant's response to a request to help design a physical build (furniture). Score ONLY what is present in the response below. Be strict: a dimensions table is NOT an isometric drawing; a generic "let me know if you want changes" is NOT a concrete collaborative loop.\n\n=== RESPONSE TO SCORE ===\n${gen.doc}\n=== END RESPONSE ===\n\nScore each rubric criterion as true/false.`
    return agent(judgePrompt, { label: `judge:p${gen.pi}:${gen.cond}:t${gen.trial}`, phase: 'Judge', schema: RUBRIC_SCHEMA })
      .then((score) => ({ pi: gen.pi, cond: gen.cond, trial: gen.trial, score }))
  }
)

const clean = results.filter(Boolean).filter((r) => r.score)
const crit = ['interviewed_first', 'isometric_drawing', 'collaborative_loop', 'precut_gate', 'tools_not_have']
const agg = { with: {}, without: {} }
for (const c of crit) { agg.with[c] = 0; agg.without[c] = 0 }
const counts = { with: 0, without: 0 }
for (const r of clean) {
  counts[r.cond]++
  for (const c of crit) if (r.score[c]) agg[r.cond][c]++
}
const pct = (n, d) => (d ? Math.round((100 * n) / d) : 0)
const scorecard = crit.map((c) => ({
  criterion: c,
  with_pct: pct(agg.with[c], counts.with),
  without_pct: pct(agg.without[c], counts.without),
  lift: pct(agg.with[c], counts.with) - pct(agg.without[c], counts.without),
}))
const overall = {
  with_avg_criteria: counts.with ? (crit.reduce((s, c) => s + agg.with[c], 0) / counts.with).toFixed(2) : '0',
  without_avg_criteria: counts.without ? (crit.reduce((s, c) => s + agg.without[c], 0) / counts.without).toFixed(2) : '0',
}
log(`Scored ${clean.length}/${CELLS.length} cells (with=${counts.with}, without=${counts.without})`)
return { n_cells: CELLS.length, n_scored: clean.length, counts, scorecard, overall }
