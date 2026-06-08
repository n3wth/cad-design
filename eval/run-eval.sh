#!/usr/bin/env bash
# Run the cad-design skill eval against the LIVE SKILL.md.
#
# Strips the YAML frontmatter from ../SKILL.md and passes the body to the
# workflow via args, so the eval always tests the shipped skill — not a stale
# copy. Requires Claude Code (the `claude` CLI provides the Workflow runtime).
#
#   ./eval/run-eval.sh
#
# The workflow generates build docs with vs without the skill across several
# prompts and trials, scores each blind on the skill's rubric, and prints a
# scorecard: per-criterion pass rate (with vs without) and the lift.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
skill_md="$here/../SKILL.md"
workflow="$here/skill-eval.workflow.js"

[ -f "$skill_md" ] || { echo "SKILL.md not found at $skill_md" >&2; exit 1; }

# Body of SKILL.md with the leading --- frontmatter block removed.
skill_body="$(awk 'NR==1 && $0=="---"{f=1;next} f && $0=="---"{f=0;next} !f' "$skill_md")"

args_json="$(SKILL_BODY="$skill_body" python3 -c 'import json,os; print(json.dumps({"skill": os.environ["SKILL_BODY"]}))')"

echo "Running cad-design skill eval against $skill_md"
echo "(generates + judges ~30 build docs; takes a few minutes)"

# In Claude Code, ask the agent to run the workflow with these args:
echo
echo "From Claude Code, run:"
echo "  Workflow({ scriptPath: \"$workflow\", args: $args_json })"
echo
echo "Or paste this request to the agent:"
echo "  Run the eval workflow at eval/skill-eval.workflow.js, passing args.skill = the body of SKILL.md, and report the scorecard."
