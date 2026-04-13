---
name: trace
description: Parse and analyze LangSmith trace JSON files to surface agent reasoning — decisions, task breakdowns, strategy shifts, and problem-solving narrative
allowed-tools: [Read, Glob, Grep, "Bash(python3:*)"]
---

# Trace — Agent Reasoning Analyzer

You are analyzing a LangSmith trace JSON file exported from Blitzy's agentic coding pipeline. A reasoning-focused extraction has been injected below, surfacing the agent's actual words, decisions, and problem-solving narrative — not infrastructure metrics.

## Arguments

`$ARGUMENTS` may contain any combination of:

| Flag | Effect |
|------|--------|
| `<file-path>` | Path to the trace JSON file (positional, required) |
| `--verbose` | Show full untruncated text for all messages |
| `--focus AREA` | Focus output on a specific area (see Focus Mode below) |

## Injected Data

```
!`python3 ~/.claude/skills/trace/scripts/trace_parser.py $ARGUMENTS`
```

## Error Handling

- **If the file is not found**: The parser will report the error. Confirm the path with the user.
- **If the JSON is malformed**: The parser will report a parse error with details.
- **If the trace has no runs**: The parser will report an empty trace. This may indicate a failed export.

## Your Task

Using the reasoning extraction above, perform a review of **how the agent thought and worked** through the task. Structure your analysis around these 5 sections:

### 1. Task Understanding

- How did the agent interpret the assignment? What was its initial plan?
- Did it correctly identify what needed to be done, or did it misread the requirements?
- Look at the first few reasoning messages — do they show comprehension or confusion?

### 2. Approach & Decisions

- Identify key decision points where the agent chose a strategy
- Did it adapt when things didn't work? Look at messages tagged `[DECISION]` for strategy shifts
- Were the decisions well-reasoned or reactive/flailing?
- Note any moments where the agent committed too early or changed direction wisely

### 3. Problem Solving

- Review messages tagged `[AFTER-ERROR]` — how did the agent respond to failures?
- Did it diagnose root causes or just retry blindly?
- Were there moments of genuine insight vs. brute-force attempts?
- Assess the quality of debugging reasoning

### 4. Task Decomposition

- How did the agent break work into steps? Was the to-do list well-structured?
- Review the To-Do Snapshots — did the list evolve appropriately?
- Did the agent track its own progress effectively?
- Were subtasks at the right granularity (not too broad, not too micro)?

### 5. Verdict

- Overall assessment of the agent's reasoning quality
- Was the agent's approach efficient or wasteful?
- What was the biggest reasoning strength and weakness in this trace?
- One-line summary: would you trust this agent's judgment on a similar task?

## Output Format

Structure your review as a markdown document:

```
## 1. Task Understanding
[How the agent interpreted and planned the task]

## 2. Approach & Decisions
[Key decision points and strategy shifts]

## 3. Problem Solving
[Error handling quality and debugging reasoning]

## 4. Task Decomposition
[To-do structure and progress tracking]

## 5. Verdict
[1-2 paragraph overall assessment of reasoning quality]
```

## Focus Mode

If `--focus AREA` was specified, concentrate the output on that area:

- `decisions` — Only strategy-shift messages. Analyze whether the agent made good calls at each pivot point.
- `todos` — Only to-do list snapshots and progression. Assess task decomposition quality.
- `errors` — Only error→response pairs. Evaluate debugging reasoning quality.

When a focus mode is active, still produce all 5 analysis sections, but weight heavily toward the focus area and draw most examples from the focused data.

## Formatting Rules

- Use markdown headers and bullet points
- Reference specific run numbers (e.g., "Run 14") when citing reasoning
- Quote the agent's own words when they illustrate a point — use blockquotes
- Keep findings specific to this trace, not generic advice
- Be direct about reasoning quality — call out both strong and weak moments
- Use severity indicators for problems: **[STRONG]**, **[WEAK]**, **[NOTABLE]**
