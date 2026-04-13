# Skill Archetypes

## Analyzer

**Defining characteristics:** Parses structured data (JSON, logs, traces), extracts patterns, surfaces insights.
**Phase structure:** Inject Data → Parse → Analyze → Report
**Reference skills:** trace, aap
**Common allowed-tools:** `[Read, Glob, Grep, Bash(python3:*)]`
**Typical line count:** 80–180

## Generator

**Defining characteristics:** Creates files or artifacts from conventions and templates. Detects project context before generating.
**Phase structure:** Detect Context → Discover Conventions → Generate → Verify
**Reference skills:** readme, test
**Common allowed-tools:** `[Read, Write, Edit, Glob, Grep, Bash]`
**Typical line count:** 200–300

## Validator

**Defining characteristics:** Scores, grades, or renders a pass/fail verdict against a checklist or rubric.
**Phase structure:** Classify Input → Validate Against Criteria → Remediate / Suggest → Report
**Reference skills:** chuck, blitzy-pr
**Common allowed-tools:** `[Read, Glob, Grep, Bash]`
**Typical line count:** 150–400 (rubric-heavy)

## Executor

**Defining characteristics:** Runs sequential shell commands with safety checks and confirmation gates.
**Phase structure:** Pre-flight → Safety Check → Execute → Confirm
**Reference skills:** commit
**Common allowed-tools:** `[Read, Glob, Grep, Bash, Edit]`
**Typical line count:** 200–280

## Advisor

**Defining characteristics:** Gathers context, reasons about priorities, and recommends actions — never executes them directly.
**Phase structure:** Gather → Reason → Recommend → Offer Actions
**Reference skills:** next
**Common allowed-tools:** `[Read, Glob, Grep, Bash]`
**Typical line count:** 100–160

## Orchestrator

**Defining characteristics:** Routes requests through category-specific sub-workflows. Heavy on decision trees and gating logic.
**Phase structure:** Categorize → Route → Execute Pathway → Consolidate
**Reference skills:** z
**Common allowed-tools:** `[Read, Write, Edit, Glob, Grep, Bash]`
**Typical line count:** 250–400

## Hybrid

**Defining characteristics:** Combines two archetypes when the skill both generates artifacts and validates them (or any other two-archetype combination). The primary archetype determines phase structure; the secondary adds a validation or generation sub-phase.
**Phase structure:** Follows the primary archetype's phases, with the secondary archetype's core phase inserted as a sub-step (e.g., Generator phases + Validator scoring pass).
**Reference skills:** skill-writer (Generator-Validator)
**Common allowed-tools:** Union of both archetypes' tools.
**Typical line count:** 200–350 (inherits the larger archetype's range)

---

## Archetype Detection Heuristic

Given a skill description and intended tools, apply in order:

1. Parses structured data / uses `Bash(python3:*)` → **Analyzer**
2. Creates files or artifacts / uses Write+Edit prominently → **Generator**
3. Produces score, verdict, or checklist result → **Validator**
4. Runs sequential shell commands with safety gates → **Executor**
5. Gives recommendations without executing → **Advisor**
6. Routes to multiple sub-workflows based on input category → **Orchestrator**

If multiple match, prefer the one whose phase structure best fits the skill's primary output.

7. If two archetypes match equally and both are central to the skill's purpose → **Hybrid** (name both, e.g., Generator-Validator). Use the primary archetype's phase structure and insert the secondary's core phase as a sub-step.
