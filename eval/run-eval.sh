#!/usr/bin/env bash
# Run the cad-design skill eval against the LIVE SKILL.md.
#
# Builds a throwaway eval script with the current SKILL.md body INLINED, then
# prints the Workflow call to run it from Claude Code. Inlining (rather than
# passing the skill via args) is deliberate: the Workflow args channel does not
# reliably carry large multi-line strings, so the skill text is baked into a
# generated copy each run — keeping the eval honest against the shipped skill.
#
#   ./eval/run-eval.sh
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
skill_md="$here/../SKILL.md"
template="$here/skill-eval.workflow.js"
out="${TMPDIR:-/tmp}/cad-design-eval.run.js"

[ -f "$skill_md" ] || { echo "SKILL.md not found at $skill_md" >&2; exit 1; }

SKILL_MD="$skill_md" TEMPLATE="$template" OUT="$out" python3 - <<'PY'
import json, os
md = open(os.environ['SKILL_MD']).read()
lines = md.split('\n')
if lines and lines[0] == '---':                      # strip YAML frontmatter
    end = lines.index('---', 1)
    md = '\n'.join(lines[end + 1:])
src = open(os.environ['TEMPLATE']).read()
needle = "const SKILL = args && args.skill\nif (!SKILL) throw new Error('Pass the SKILL.md body via args.skill (use eval/run-eval.sh).')"
src = src.replace(needle, 'const SKILL = ' + json.dumps(md))
open(os.environ['OUT'], 'w').write(src)
print('Wrote', os.environ['OUT'], '(' + str(len(md)) + ' chars of skill inlined)')
PY

echo
echo "From Claude Code, run:"
echo "  Workflow({ scriptPath: \"$out\" })"
echo
echo "Or paste to the agent:"
echo "  Run the eval at $out and report the scorecard."
