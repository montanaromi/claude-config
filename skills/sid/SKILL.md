---
name: sid
description: Enforce blitzy-utils-python gold-standard coding patterns (PR #534) — comments, docstrings, error handling, logging, structure, and commit style. Invoke before or during any code writing in this repo.
allowed-tools:
  - Read
  - Edit
  - Write
  - Glob
  - Grep
  - Bash(git diff:*)
  - Bash(git log:*)
  - Bash(git status:*)
---

# Sid — Gold-Standard Coding Agent

Enforce the exact coding patterns from PR #534 ("Optional write access for all submodules") when writing or modifying Python code in `blitzy-utils-python`. Every line of code, every comment, every docstring, every error handler must match these patterns to a T.

This skill is the coding constitution. No deviation.

## When to Invoke

- Writing new functions or classes
- Modifying existing code
- Adding error handling or logging
- Writing comments or docstrings
- Preparing commits

## Phase 1 — Pre-flight

Before writing any code:

1. Read the file(s) you will modify. Understand surrounding patterns.
2. Identify which patterns from the sections below apply to your change.
3. If adding a function that mirrors an existing one across platforms (GitHub/Azure/GitLab), read the existing implementation first — you must mirror its structure exactly.

## Phase 2 — Write Code Following These Patterns

### 2.1 Comment Style

**Rule: Explain *why*, never *what*.**

**Inline comments** — motivation and consequence:
```python
# Defer push to the push/pull step — only push when the
# submodule actually has new commits.  This avoids write-
# access failures on read-only submodules that have no
# changes to push.
```

Format rules:
- `#` + one space + lowercase start (unless proper noun)
- Wrap at ~60–65 characters per line
- Em-dash `—` for clause separation (not `--` or `-`)
- Two spaces before period at sentence boundaries within a block (`commits.  This avoids`)

**Block comments** before major logic sections:
```python
# Handle submodule branches first (ensure each submodule is on a
# named branch instead of detached HEAD).  Pushes are deferred to
# the per-submodule loop below — only submodules with new commits
# will be pushed, which avoids write-access errors on read-only
# submodules.
```
- Parenthetical: *what* the section does
- Then: the *design decision* and *why*

**Tracking-variable comments** — purpose AND downstream consumption:
```python
# Push submodule only if there are commits to push.
# Track whether we successfully pushed so we know the remote
# branch exists for the subsequent pull.
sub_pushed = False
```

**Decision comments** — state the decision, preference order, and fallback:
```python
# Determine the base branch for the submodule PR.
# Prefer the parent's base_branch (so the PR targets the same
# branch the submodule was cloned from). Fall back to the
# submodule's default branch if base_branch doesn't exist there.
```

**Fast-path comments** — label explicitly, explain the invariant:
```python
# Fast path: if branch doesn't exist in the parent repo it won't
# exist in submodules either — skip all submodule API calls.
```

### 2.2 Docstring Style

```python
def delete_branch_in_submodules_github(
    repo: Repository,
    branch_name: str,
    base_branch: str,
    git_project_repo_id: str,
    hostname: Optional[str] = None,
) -> None:
    """Delete a branch in all submodules of a GitHub repository.

    Used during branch setup when delete_existing_branch is True, so the
    working branch is also cleaned up in submodules before re-creation.

    Skips all submodule work when the branch does not exist in the parent
    repo (common on first runs), avoiding unnecessary API calls.

    Args:
        repo: PyGithub Repository object for the parent repo.
        branch_name: Branch name to delete in submodules.
        base_branch: Base branch to read .gitmodules from.
        git_project_repo_id: Project repository ID for credential lookup.
        hostname: GitHub API hostname (None for github.com).
    """
```

Structure (in order):
1. **First line:** imperative verb, what the function does
2. **Second paragraph:** *when* and *why* it is called
3. **Third paragraph:** notable optimization, skip behavior, or caveats
4. **Args:** `name: Description ending with period.` (one line each)
5. **Returns:** only if the function returns a value (omit for `-> None`)

### 2.3 Error Handling

**Critical failures** — build message, log, raise with chaining:
```python
try:
    if not push_local_changes(full_submodule_path, branch_name, env):
        error_msg = f"Push failed for submodule {canonical_path}"
        logger.error(error_msg)
        raise SubmodulePushPullError(canonical_path, "push", error_msg)
except GitAccessError as e:
    error_msg = (
        f"No write access to submodule '{canonical_path}'. "
        f"The submodule has commits that need pushing but the credentials "
        f"lack write permission. Grant write access or avoid modifying this submodule."
    )
    logger.error(error_msg)
    raise SubmodulePushPullError(canonical_path, "push", error_msg) from e
```

Rules:
- Catch **specific** exceptions — never bare `except`
- Build `error_msg` as a variable
- `logger.error(error_msg)` immediately before `raise`
- `raise ... from e` for exception chaining always
- Error message formula: **what's wrong** + **why** + **what the user should do**

**Non-critical failures** — warn and continue:
```python
except Exception as e:
    logger.warning(f"Could not process submodule {submodule_path} for branch deletion: {e}")
```
- `logger.warning` (not error) for non-critical failures
- Continue the loop — do not abort

### 2.4 Logging

| Level | When | Example |
|-------|------|---------|
| `logger.info` | Happy path, status updates | `f"Deleted branch '{branch_name}' in submodule {submodule_path}"` |
| `logger.warning` | Non-critical failures, degraded paths | `f"Could not find project for submodule: {name}"` |
| `logger.error` | Immediately before `raise` only | `f"No write access to submodule '{path}'"` |

Rules:
- Always use f-strings
- Quote identifiers (branch names, paths) with **single quotes** in log messages
- Include entity context (submodule path, repo name) in every log line

### 2.5 Function Signatures

```python
def delete_branch_in_submodules_azure(
    git_project_repo: "GitProjectRepo",
    branch_name: str,
    base_branch: str,
) -> None:
```

- One parameter per line when > 2 parameters
- Type hints on **all** parameters
- Return type annotation **always** present
- `Optional[str] = None` for optional parameters

### 2.6 Code Structure

**Guard clauses** — early return with informative log:
```python
if not gitmodules_content:
    logger.info("No .gitmodules file found, no submodule branches to delete")
    return
```

**Boolean flag tracking** for downstream decisions:
```python
sub_pushed = False
if sub_has_commits:
    # ... push logic ...
    sub_pushed = True

remote_has_branch = sub_pushed
if not remote_has_branch:
    # ls-remote check ...
```

**Platform mirroring** — when implementing for GitHub and Azure (or GitLab):
- Same logical structure in both implementations
- Same docstring structure, same comment style, same error handling
- Same fast-path optimizations
- Platform-specific API calls are the only divergence

## Phase 3 — Verify

After writing code, check every item:

1. Every comment explains *why*, not *what*
2. Comments wrap at ~60–65 chars with `#` prefix
3. Em-dashes `—` used (not `--`)
4. Two spaces before periods in multi-sentence comment blocks
5. Docstrings follow the 3-paragraph + Args structure
6. All exceptions are specific (no bare `except`)
7. `error_msg` variable pattern used for all raises
8. `from e` chaining on all re-raises
9. `logger.error` appears only immediately before `raise`
10. Identifiers single-quoted in log messages
11. Every log line includes entity context
12. Guard clauses use early return with `logger.info`
13. Function signatures have full type hints and return annotations
14. Platform-mirrored functions match structure exactly

## Phase 4 — Commit Style

When the code is ready:

- **Feature commit:** short imperative sentence, no ticket prefix
  `Optional write access for all submodules`
- **Linting commit:** conventional commit prefix, separate from logic
  `chore: linting`
- **CI skip:** bracket prefix for automated changes
  `[skip ci] Update package versions`
- **Never** mix logic changes with formatting/linting in the same commit

## Edge Cases

- **Editing a file with inconsistent existing style:** match the gold patterns, not the surrounding code. The gold standard wins.
- **One-line functions:** docstring can be single-line imperative. Still needs type hints and return annotation.
- **No logging available:** if the module doesn't import `logger`, add the import following existing patterns in the file.
- **Test files:** docstrings and type hints are optional in tests. Comment style still applies.
- **Scripts (root-level .py files):** follow the same patterns but `print()` may substitute for `logger` where logging isn't configured.

## Composability

- After coding: run `/commit` to stage and commit with the correct message style
- After committing: run `/simplify` to review for reuse and quality
- For new functions: run `/test` to generate test coverage
