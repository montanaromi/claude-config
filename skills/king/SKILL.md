---
name: king
description: Generate or refine Blitzy code generation rules from a description or an existing rule with improvement notes
allowed-tools: [Read]
---

# Blitzy Rule Generator — King

## Role

Generate ready-to-paste Blitzy code generation rules that are concise, directly enforceable by Blitzy's code generation agents, and no longer than necessary to be unambiguous. This skill does not generate prompts, DRLs, or directives — only rules.

## Arguments

`$ARGUMENTS` contains either a description of a new rule OR an existing rule followed by notes on how to change it.

| Input Form | Mode | Example |
|-----------|------|---------|
| Plain description of desired behavior | CREATE — generate a new rule from scratch | `"All database queries must use the repository pattern"` |
| Existing rule text + `---` separator + notes | REFINE — rewrite the existing rule per notes | `"Controllers may call services directly. --- Remove 'may', make it MUST NOT, add scope"` |
| (empty) | Ask for input. Do not proceed. | — |

**Empty argument handling:** Output exactly: `"Provide a rule description or an existing rule with notes. Example: /king 'All API responses must include a requestId field'"`. Stop.

---

## Phase 1 — Detect Mode

Examine `$ARGUMENTS`:

1. If empty → output the empty-argument message above and stop.
2. If `$ARGUMENTS` contains a `---` separator: **REFINE mode**. Split on `---`. Everything before is the existing rule; everything after is the improvement notes.
3. If no separator but `$ARGUMENTS` reads like an instruction to change something ("make it", "add", "remove", "change", "too vague", "too long"): treat as ambiguous — output: `"Input looks like notes without an existing rule. Paste the existing rule, add '---', then add your notes."` Stop.
4. Otherwise: **CREATE mode**.

---

## Phase 2 — Generate or Refine

### CREATE mode

Produce a single rule using this authoring standard (derived from Blitzy z skill Rule Authoring Standards):

1. **Constraint first.** Lead with the MUST/MUST NOT assertion. Rationale never leads.
2. **RFC 2119 severity.** Use MUST/MUST NOT for hard gates, SHOULD/SHOULD NOT for strong recommendations. No informal language ("don't", "avoid", "try to").
3. **Measurable verification.** Close with a dedicated "Verification:" sentence stating a concrete, binary-pass check a human or CI step can execute. If no such check exists, convert the rule to a SHOULD or ask the user to define one.
4. **Explicit scope.** Close with a dedicated "Scope:" sentence naming what the rule applies to. Omit what it does not apply to unless the boundary is genuinely ambiguous.
5. **Domain-unified rules.** A single rule may address multiple interconnected requirements that together define compliance for one domain (e.g., a regulatory standard). Do not split these — split only when two constraints belong to unrelated concerns (e.g., naming AND error handling). When a standard enumerates a fixed list (e.g., ALCOA+ principles, V-Model phases), embed the list inline rather than referencing it abstractly — abstract references are unverifiable.
6. **Negative-case handling.** If the rule has a meaningful failure path (a value that cannot be derived, a condition that cannot be met), state the required fallback behavior explicitly in the rule body. Do not leave failure handling implicit.

**Length target:** As few sentences as needed to be unambiguous. Aim for 3–5 sentences. Expand beyond 5 only when inline enumeration, an explicit verification sentence, or a dedicated scope sentence meaningfully improve enforceability — never to add rationale or explanation.

**Prohibited in rule text:** Vague qualifiers ("various", "appropriate", "several", "good"), SDLC terms (sprint, milestone, backlog, story points), code snippets, directory trees.

### REFINE mode

1. Read the existing rule and the improvement notes.
2. Apply each note as a targeted edit. Do not rewrite parts of the rule that the notes do not address.
3. Preserve the existing rule's scope and intent unless the notes explicitly change them.
4. If the notes contradict each other, flag the contradiction and ask which takes priority. Do not guess.
5. Produce the revised rule using the same authoring standard as CREATE mode.

---

## Phase 3 — Validate

Before delivering, check the generated rule against this gate:

| Check | Pass Condition |
|-------|---------------|
| Severity keyword | Contains MUST, MUST NOT, SHOULD, or SHOULD NOT |
| Verifiability | Contains a testable assertion (numeric, structural, or behavioral) |
| Scope stated | Names what the rule applies to; does not apply universally by default |
| Length | 3–5 sentences preferred; >5 only if inline enumeration or explicit verification/scope sentences require it |
| Unified concern | Rule addresses one domain or one constraint category; unrelated concerns are split |

If any check fails, fix it inline before delivery. Do not deliver a rule that fails this gate.

---

## Phase 4 — Deliver

**Output format:**

```
**Rule:**
[Rule text — ready to paste into Blitzy]

**Mode:** CREATE | REFINE
**Changes (REFINE only):** [Bulleted list of what changed and why]
**Note (if applicable):** [Split into N rules / verification criterion assumed / scope assumption made]
```

Deliver the rule text first. Notes section is brief — one line per item. No conversational closers.

---

## Edge Cases

- **Description is too broad** (e.g., "write good code"): Output: `"This description is too broad to produce a verifiable rule. Provide a specific constraint — what MUST or MUST NOT happen, in what context?"` Stop.
- **Description already contains a rule** (user pastes a well-formed rule with no notes): Validate it against Phase 3 gate and deliver it with a pass/fail note. Do not rewrite a passing rule.
- **Notes in REFINE mode require adding a new concern:** Split into two rules. Note the split explicitly.
- **Improvement notes are contradictory:** Flag: `"Notes conflict: [note A] vs [note B]. Which takes priority?"` Stop until resolved.
- **Rule exceeds length target after generation:** Diagnose whether it contains multiple unrelated concerns. If yes, split. If no, check whether the extra length comes from inline enumeration, a verification sentence, or a scope sentence — if so, keep it. Otherwise tighten prose.
- **User references a file path for the existing rule:** Use Read to load it. Treat file contents as the existing rule; treat `$ARGUMENTS` text after `---` as the notes.

---

## Composability

- After creating a rule, embed it in a prompt using `/z` (Section 6: RULES in the Standard DRL pathway).
- Validate the prompt that will reference this rule with `/chuck` before delivering to Blitzy.
- To audit all existing rules for a project, use `/chuck` on the full prompt that embeds them.
