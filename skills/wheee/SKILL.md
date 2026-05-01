---
name: wheee
description: Automate the /z → /chuck feedback loop to generate, validate, and refine Blitzy prompts until approved
allowed-tools: [Read, Write, Bash(mkdir:*)]
---

# Wheee — Automated Blitzy Prompt Refinement Loop

## Role

Orchestrate the /z → /chuck → /z refinement cycle autonomously. Accept a user request, generate a Blitzy prompt via /z, validate it with /chuck, apply /chuck findings back through /z as targeted corrections, and repeat until /chuck returns APPROVED or the iteration cap is reached. Deliver the approved prompt as a markdown artifact.

**Scope:** Prompt generation and validation loop only. Does not execute generated prompts, modify application code, or make decisions outside the /z and /chuck contracts. Invokes /z and /chuck as skills — do not reproduce their logic inline.

## Arguments

`$ARGUMENTS` contains the user's request and an optional save path.

| Arg | Format | Effect |
|-----|--------|--------|
| `<request text>` | Free text | Passed to /z as the initial prompt request |
| `<request text> --save <path>` | Text + flag | Same; saves approved prompt to `<path>` on approval |
| (empty) | — | Halt: "Provide a request. Example: `/wheee build a REST API for user management`" |

**Save path detection:** Scan $ARGUMENTS for a token matching a Unix file path pattern (starts with `/`, `~/`, or `./`, ends with `.md`). If found, extract as `SAVE_PATH` and remove from the request text passed to /z. If not found, set `SAVE_PATH = null`.

## Phase 1: Parse & Initialize

1. If $ARGUMENTS is empty → halt: "Provide a request. Example: `/wheee build a REST API for user management`"
2. Extract `SAVE_PATH` using save path detection rule above.
3. Set state variables: `ITERATION = 0`, `MAX_ITERATIONS = 5`, `STATUS = PENDING`.
4. Print initialization block:

```
━━━ /wheee ━━━━━━━━━━━━━━━━━━━━━━━━━━━
Request : [extracted request text]
Save    : [SAVE_PATH or "none"]
Cap     : 5 iterations
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Gate:** Request text is non-empty before proceeding.

## Phase 2: Generate Prompt via /z

**Trigger:** Phase 1 complete.

1. Invoke `/z` with the extracted request text as $ARGUMENTS.
2. /z executes its full workflow:
   - Standard pathway (New Product, New Feature, Refactor, etc.): Phases 1–4 → markdown prompt artifact
   - Directive pathway (Bug Fix, Add Testing, Refine PR, etc.): Phases 1–2 → CRITICAL Directive artifact
3. **DRL alignment gates — auto-respond, never surface to user:**
   - **Standard pathway Phase 2 gate** ("USER NEXT STEPS: Return YES if aligned or completed DRL when ready"): `/wheee` responds YES immediately. Do not pause or ask the user. If the user pre-supplied a modified DRL in $ARGUMENTS, pass it here instead of YES.
   - **Standard pathway Phase 3 gate** ("Review and return YES to proceed to prompt generation"): `/wheee` responds YES immediately. Do not pause or ask the user.
   - **Directive pathway gate** ("USER NEXT STEPS: Return YES if aligned or modified directive when ready"): `/wheee` responds YES immediately. Do not pause or ask the user.
   - The only exception: if /z requests clarification (a question requiring domain knowledge or user intent — not a YES/NO confirmation gate), pause and surface the question to the user. Resume the loop after the user responds.
4. Capture the final /z output as `CURRENT_PROMPT`.

**Gate:** `CURRENT_PROMPT` is non-empty. If /z produces no artifact, surface the /z output to the user and halt.

## Phase 3: Validate → Refine Loop

**Trigger:** `CURRENT_PROMPT` ready, `ITERATION < MAX_ITERATIONS`, `STATUS != APPROVED`.

### Step 1 — Run /chuck

1. Print iteration header:
```
━━━ Chuck Pass [ITERATION + 1] / [MAX_ITERATIONS] ━━━━━━━━━━━━━━━━━━━
```
2. Invoke `/chuck` with `CURRENT_PROMPT` as $ARGUMENTS.
3. Capture /chuck's status verdict and full Optimization Report findings.

### Step 2 — Evaluate verdict

**APPROVED:**
- Set `STATUS = APPROVED`.
- Proceed to Phase 4.

**NEEDS REVISION or REJECTED:**
- Increment `ITERATION`.
- **If `ITERATION >= MAX_ITERATIONS`:**
  - Print:
  ```
  ✗ Iteration cap reached. [N] findings unresolved after 5 passes.
  Manual resolution required — resolve the findings below and re-run /wheee.
  ```
  - Print all remaining /chuck findings verbatim from the final Optimization Report.
  - Halt. Do not save.
- Otherwise → proceed to Step 3.

### Step 3 — Refine via /z

1. Extract all findings from /chuck's Optimization Report: item tags (`[Item #N]`), severity scores, and the exact replacement wording from the Actionable Corrections section.
2. Invoke `/z` with a **Refine Pull Request** request structured as:

```
Refine Pull Request — apply [N] targeted /chuck corrections to [CURRENT_PROMPT name].
Do not modify any content outside the scope of these findings.

[List each finding: Item tag, severity, exact replacement wording from /chuck Optimization Report]
```

3. When /z presents "USER NEXT STEPS: Return YES if aligned or modified directive when ready": respond YES immediately without surfacing to user.
4. Capture refined output as `CURRENT_PROMPT`.
5. Return to Step 1.

**Minimal change mandate:** Each refinement pass MUST apply only the corrections enumerated in the /chuck findings for that pass. Additions, structural changes, or content modifications outside the finding scope are prohibited. If /z proposes changes beyond the finding scope, reject them and re-invoke with tighter scope constraints.

## Phase 4: Deliver Artifact

**Trigger:** `STATUS = APPROVED`.

1. Present `CURRENT_PROMPT` as a markdown artifact.
2. Update the artifact header to include validation status:
```
> Validated: [date] | /chuck status: APPROVED ([N] passes)
```
3. **If `SAVE_PATH` is set:**
   - Extract parent directory from `SAVE_PATH`.
   - Run `mkdir -p <directory>` to ensure path exists.
   - Write `CURRENT_PROMPT` to `SAVE_PATH`.
   - Confirm: `Saved → [SAVE_PATH]`
4. Print approval summary:
```
━━━ /wheee complete ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Approved in [N] pass(es). [M] findings resolved. 0 remaining.
Saved: [SAVE_PATH or "not saved — pass --save <path> to persist"]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Edge Cases

| Condition | Behavior |
|-----------|----------|
| Empty $ARGUMENTS | Halt with usage example before Phase 1 |
| /z presents any "USER NEXT STEPS: Return YES" gate | Auto-respond YES immediately — never surface YES/NO confirmation gates to user; the loop must not stall on /z alignment checkpoints |
| /z requests clarification mid-workflow | Pause loop, surface question to user, resume after response; do not auto-answer ambiguous /z prompts |
| /z produces a Directive pathway artifact | Treat CRITICAL Directive as `CURRENT_PROMPT`; /chuck validates it normally |
| /chuck findings conflict across passes | Apply only the current pass's findings; do not carry forward superseded findings from earlier passes |
| Save path directory does not exist | Create with `mkdir -p`; if Bash is denied, print the path and instruct the user to create the directory manually, then re-run |
| Save path does not end in `.md` | Warn: "Save path `[path]` is not a .md file — saving anyway." Proceed. |
| Iteration cap reached with REJECTED status | Surface all Critical violation findings, warn that unresolved Critical violations remain, halt |
| User provides a modified DRL | Accept and pass to /z Phase 3; reset `ITERATION = 0` |
| `CURRENT_PROMPT` empty after /z | Surface /z output, halt with: "/z produced no artifact — check /z output above for errors." |

## Composability

- `/z` — run standalone when you need to inspect or modify the DRL before /chuck validation
- `/chuck` — run standalone to validate a pre-existing prompt without generating a new one
- `/commit` — run after `/wheee` to stage the saved prompt file
- `/tech-spec` — run on the approved prompt before Blitzy execution for spec-level review

**Workflow position:** `/wheee` replaces the manual `/z` → `/chuck` → `/z` cycle. Use it when the request is well-defined and you want a hands-off path to an approved prompt. Use `/z` + `/chuck` separately when inspecting DRL alignment or iterating on requirements manually.

**Full pipeline:**
`/wheee <request> --save <path>` → approved artifact → `/tech-spec` (optional) → Blitzy run → `/blitzy-pr`
