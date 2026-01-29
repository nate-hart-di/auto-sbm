#!/usr/bin/env bash
set -euo pipefail

PROMPTS_DIR="$(pwd)"

# alias_name => target_filename
declare -A MAP=(
  # bmm agents
  [analyst]="bmad-bmm-agents-analyst.md"
  [architect]="bmad-bmm-agents-architect.md"
  [dev]="bmad-bmm-agents-dev.md"
  [pm]="bmad-bmm-agents-pm.md"
  [sm]="bmad-bmm-agents-sm.md"
  [tea]="bmad-bmm-agents-tea.md"
  [techwriter]="bmad-bmm-agents-tech-writer.md"
  [ux]="bmad-bmm-agents-ux-designer.md"
  [qflow]="bmad-bmm-agents-quick-flow-solo-dev.md"

  # bmm workflows (short, distinctive names)
  [check-ready]="bmad-bmm-workflows-check-implementation-readiness.md"
  [code-review]="bmad-bmm-workflows-code-review.md"
  [correct-course]="bmad-bmm-workflows-correct-course.md"
  [arch]="bmad-bmm-workflows-create-architecture.md"
  [epics]="bmad-bmm-workflows-create-epics-and-stories.md"
  [ex-dataflow]="bmad-bmm-workflows-create-excalidraw-dataflow.md"
  [ex-diagram]="bmad-bmm-workflows-create-excalidraw-diagram.md"
  [ex-flow]="bmad-bmm-workflows-create-excalidraw-flowchart.md"
  [ex-wireframe]="bmad-bmm-workflows-create-excalidraw-wireframe.md"
  [brief]="bmad-bmm-workflows-create-product-brief.md"
  [story]="bmad-bmm-workflows-create-story.md"
  [ux-design]="bmad-bmm-workflows-create-ux-design.md"
  [dev-story]="bmad-bmm-workflows-dev-story.md"
  [doc-project]="bmad-bmm-workflows-document-project.md"
  [context]="bmad-bmm-workflows-generate-project-context.md"
  [prd]="bmad-bmm-workflows-prd.md"
  [quick-dev]="bmad-bmm-workflows-quick-dev.md"
  [quick-spec]="bmad-bmm-workflows-quick-spec.md"
  [research]="bmad-bmm-workflows-research.md"
  [retro]="bmad-bmm-workflows-retrospective.md"
  [sprint-plan]="bmad-bmm-workflows-sprint-planning.md"
  [sprint-status]="bmad-bmm-workflows-sprint-status.md"
  [atdd]="bmad-bmm-workflows-testarch-atdd.md"
  [test-auto]="bmad-bmm-workflows-testarch-automate.md"
  [test-ci]="bmad-bmm-workflows-testarch-ci.md"
  [test-fw]="bmad-bmm-workflows-testarch-framework.md"
  [test-nfr]="bmad-bmm-workflows-testarch-nfr.md"
  [test-design]="bmad-bmm-workflows-testarch-test-design.md"
  [test-review]="bmad-bmm-workflows-testarch-test-review.md"
  [trace]="bmad-bmm-workflows-testarch-trace.md"
  [wf-init]="bmad-bmm-workflows-workflow-init.md"
  [wf-status]="bmad-bmm-workflows-workflow-status.md"

  # core
  [bmad]="bmad-core-agents-bmad-master.md"
  [brainstorm]="bmad-core-workflows-brainstorming.md"
  [party]="bmad-core-workflows-party-mode.md"
)

make_alias () {
  local alias="$1"
  local target="$2"
  local out="${PROMPTS_DIR}/${alias}.md"

  if [[ ! -f "${PROMPTS_DIR}/${target}" ]]; then
    echo "SKIP: missing target ${target}"
    return
  fi

  if [[ -f "${out}" ]]; then
    echo "SKIP: already exists ${alias}.md"
    return
  fi

  cat > "${out}" <<EOF
---
description: "Alias for ${target}"
argument-hint: "Optional: add context after the command (positional args: \$ARGUMENTS)"
---
Load and run the BMAD prompt file:

${target}

Instructions:
1) Read the entire contents of "${PROMPTS_DIR}/${target}".
2) Apply those instructions exactly.
3) If additional context was supplied after the command, treat it as extra user context: \$ARGUMENTS
EOF

  echo "OK: wrote ${alias}.md -> ${target}"
}

for a in "${!MAP[@]}"; do
  make_alias "$a" "${MAP[$a]}"
done

echo
echo "Done. Restart Codex CLI so it reloads prompts."
