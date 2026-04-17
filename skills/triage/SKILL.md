---
name: triage
description: Use when a bug is reported but you don't know where it lives in the codebase — systematically searches, narrows, and locates the faulty code before any fix is attempted
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(git log:*)
  - Bash(git diff:*)
  - Bash(git blame:*)
  - Bash(git bisect:*)
  - Bash(git show:*)
  - Agent
---

# Bug Triage

## Role

Locate the source of a bug in a codebase. Produce a ranked list of suspects with evidence. **Never propose or implement fixes** — that is the job of `superpowers:systematic-debugging` after triage completes.

## Arguments

| Arg | Required | Description |
|-----|----------|-------------|
| `<description>` | Yes | Bug description: error message, symptom, or reproduction steps |
| `--scope <path>` | No | Limit search to a subdirectory (default: entire repo) |
| `--since <date>` | No | Only consider changes after this date (ISO 8601 or relative like `2w`) |
| `--severity` | No | Flag as high-severity to prioritize blast-radius analysis |

If `<description>` is empty, ask: "Describe the bug — paste the error message, stack trace, or unexpected behavior."

## Phase 1: Classify the Bug Report

Determine the investigation strategy from the input type:

| Input Type | Detection Signal | Primary Strategy |
|------------|-----------------|------------------|
| **Stack trace / error message** | Contains file paths, line numbers, exception names | Trace backward from crash site |
| **Behavioral bug** | "X should do Y but does Z" | Search for logic controlling the behavior |
| **Performance regression** | "Slow", "timeout", "memory", latency numbers | Profile hot paths, recent changes to critical loops |
| **Intermittent / flaky** | "Sometimes", "random", "race condition" | Search for shared state, concurrency, timing |
| **Security issue** | Auth, injection, access control, data exposure | Trace trust boundaries and input validation |
| **UI/UX defect** | Visual, layout, rendering, user-facing text | Locate templates, components, stylesheets |

**Output:** State the classification and chosen strategy before proceeding.

## Phase 2: Gather Evidence

Execute ALL applicable evidence-gathering steps. Run independent searches in parallel using the Agent tool when possible.

### Step 1: Extract Search Anchors

From the bug report, extract every searchable token:
- Error messages (exact strings)
- Function/method names
- Variable names
- File paths mentioned
- HTTP status codes, error codes
- UI text or labels

### Step 2: Search by Symptoms

For each search anchor:
1. **Grep** for exact error strings and exception messages.
2. **Grep** for function/variable names from the report.
3. **Glob** for files matching mentioned paths or naming patterns.
4. **Read** the top 3-5 matching files to understand context.

Record every hit with file path, line number, and surrounding context.

### Step 3: Analyze Recent Changes

Run in parallel:
- `git log --oneline --since="2 weeks ago" -- <scope>` to find recent commits in the affected area.
- `git log --all -S "<error_string>" --oneline` to find commits that introduced or removed the error string.
- `git log --all --grep="<keyword>" --oneline` for commits mentioning the bug's domain.

If `--since` was provided, use that date instead of 2 weeks.

For the most suspicious commits:
- `git show <sha> --stat` to see what files changed.
- `git diff <sha>~1 <sha>` to read the actual diff.

### Step 4: Trace Data Flow

Starting from the symptom location found in Step 2:
1. Identify the function where the bad behavior occurs.
2. Find all callers of that function (grep for the function name).
3. Find what data flows into that function (read parameters, trace origins).
4. Follow the chain until you reach the entry point (API handler, CLI arg, config load, user input).

Build a call chain: `entry_point → middleware → handler → service → <suspect>`.

### Step 5: Check for Known Patterns

Search for common bug-producing patterns near the symptom:
- Off-by-one errors in loops or slicing
- Null/None/undefined checks missing
- Incorrect type conversions or comparisons
- Race conditions (shared mutable state without locks)
- Resource leaks (unclosed files, connections, cursors)
- Silent exception swallowing (bare `except:`, empty `catch`)
- Stale cache or memoization
- Environment-dependent behavior (env vars, config files)
- Incorrect string encoding/decoding

### Step 6: Blast Radius Assessment (if --severity or high-impact suspected)

1. Find all callers and dependents of the suspect code.
2. Check if the suspect is in a shared library, utility, or base class.
3. Count how many code paths flow through the suspect.
4. Check for tests covering the suspect area: `grep -r "test.*<function_name>" tests/`.

## Phase 3: Rank Suspects

Score each candidate location on three axes:

| Axis | Weight | Scoring |
|------|--------|---------|
| **Evidence strength** | 40% | Direct match (5), strong correlation (3), circumstantial (1) |
| **Recency of change** | 30% | Changed this week (5), this month (3), older (1), never (0) |
| **Pattern match** | 30% | Known anti-pattern present (5), code smell (3), clean (1) |

Rank all suspects by weighted score. Keep the top 5 (or fewer if evidence is thin).

## Phase 4: Deliver Triage Report

Present findings in this exact format:

```
## Triage Report: <one-line bug summary>

**Classification:** <type from Phase 1>
**Scope searched:** <paths and date range>
**Confidence:** High | Medium | Low

### Suspects (ranked)

#### 1. <file_path>:<line_range> — <one-line description>
- **Evidence:** <what points here>
- **Recency:** <last changed date and commit>
- **Pattern:** <anti-pattern or code smell if any>
- **Score:** <N>/5.0

#### 2. <file_path>:<line_range> — <one-line description>
...

### Evidence Trail
- <chronological list of key findings from Phase 2>

### Recommended Next Steps
1. <specific action — e.g., "Add logging at X to confirm Y">
2. <specific action — e.g., "Run /superpowers:systematic-debugging on suspect #1">
3. <specific action — e.g., "Write a failing test for the scenario described">
```

**Confidence levels:**
- **High:** Direct evidence links symptom to suspect (stack trace, error string match, recent breaking change).
- **Medium:** Strong correlation but no direct proof (code smell in area, recent changes nearby).
- **Low:** Circumstantial only (area is complex, no recent changes, no direct matches).

## Edge Cases

- **No error message or stack trace provided:** Ask the user for reproduction steps. If unavailable, search by behavioral keywords and recent changes only.
- **Bug is in generated code:** Trace to the generator/template, not the output. Search for template files, code generation scripts, or build artifacts.
- **Bug spans multiple services/repos:** Note the boundary. Triage the local repo only. Recommend checking upstream/downstream services in the report.
- **No git history available:** Skip Phase 2 Step 3. Rely on code search and pattern analysis only.
- **Thousands of grep results:** Narrow with additional context (file type, directory scope, combining multiple search terms). Never dump raw results — always filter and rank.
- **Suspect is in a dependency, not the repo:** Report it as an external suspect. Include the dependency name, version, and the specific API call that triggers the bug.
- **Codebase is unfamiliar:** Start with entry points (main files, route definitions, CLI handlers). Map the architecture before diving into specifics.

## Composability

- **After triage:** Run `superpowers:systematic-debugging` on the top suspect to find root cause and fix.
- **To verify the fix:** Run `superpowers:test-driven-development` to write a regression test.
- **To commit the fix:** Run `/commit` to stage and commit with a conventional message.
- **For broad investigation:** Run `superpowers:dispatching-parallel-agents` to triage multiple suspects in parallel.
