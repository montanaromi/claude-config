---
name: pr
description: Push branch and create a GitHub pull request with conventional commit conventions, no co-authoring trailers
allowed-tools: [Glob, Grep, Read, "Bash(git status:*)", "Bash(git diff:*)", "Bash(git log:*)", "Bash(git branch:*)", "Bash(git rev-parse:*)", "Bash(git remote:*)", "Bash(git push:*)", "Bash(gh pr:*)", "Bash(gh api:*)"]
---

# PR — Create Pull Requests with Conventional Commit Conventions

Create GitHub pull requests from the current branch. Follows the same conventions as `/commit` — conventional prefixes, imperative mood, safety checks. **Never appends Co-Authored-By or Co-authored-by trailers.**

## Arguments

`only` may contain any combination of:

| Flag | Effect |
|------|--------|
| `--draft` | Create the PR as a draft |
| `--base <branch>` | Target branch (default: `main`) |
| `--fixes #N` | Link PR to issue N with `Fixes #N` in body |
| `--closes #N` | Link PR to issue N with `Closes #N` in body |
| `--quick` | Skip confirmation — auto-detect and create immediately |
| *(plain text)* | Used as the PR title |

## Step 1: Pre-flight Checks

1. Run `git rev-parse --is-inside-work-tree` to confirm this is a git repo.
2. Run `git rev-parse --abbrev-ref HEAD` to get the current branch.
3. If the branch is `main`, `master`, `develop`, `development`, `qa`, `prod`, `production`, `staging`, or `release` — **stop** and tell the user to create a feature branch first. PRs should not be created from protected branches.
4. Run `gh auth status` to confirm GitHub CLI is authenticated. If not, tell the user to run `gh auth login`.

## Step 2: Analyze Changes

1. Determine the base branch (from `--base` flag or default `main`).
2. Run `git log --oneline <base>..HEAD` to see all commits on this branch.
3. Run `git diff <base>...HEAD --stat` to see the full file-level diff summary.
4. If there are uncommitted changes, warn the user and ask whether to proceed or commit first.
5. If there are no commits ahead of base, stop and tell the user there's nothing to PR.

## Step 3: Check Remote State

1. Run `git remote -v` to confirm a remote exists.
2. Check if the branch has been pushed: `git rev-parse --verify origin/<branch> 2>/dev/null`.
3. If not pushed, push with: `git push -u origin <branch>`.
4. If pushed, check if local is ahead: `git status -sb`. If ahead, push first.

## Step 4: Determine PR Title

### If `only` contains a title:
- If it's already in conventional commit format (e.g., `fix: resolve null pointer`), use it as-is.
- If it's plain text, convert to conventional format.

### If `only` is empty:
Auto-detect from the commits on the branch:

- **Single commit:** Use the commit message as the PR title.
- **Multiple commits, same type:** Use the shared type with a summary description.
- **Multiple commits, mixed types:** Use the dominant type or `feat` if unclear, with a summary.

### Title rules:
- Use conventional commit prefix: `feat`, `fix`, `refactor`, `docs`, `chore`, `test`, `style`, `perf`, `ci`, `build`
- **Imperative mood** ("add", "fix", "update" — not "added", "fixes", "updated")
- **Lowercase** first word after the colon
- **No period** at the end
- **Under 72 characters**

## Step 5: Generate PR Body

The diff speaks for itself. Keep the body short — if the commit message is clear, the PR body adds only what the diff cannot show.

Structure the body as:

```markdown
## Summary
<1-3 sentences max. State the bug or motivation, then the fix. No bullet lists of files changed — the diff shows that.>

## Test plan
<2-4 actionable items: exact commands and manual verification steps>
```

**Do not include a "Changes" section.** The diff is the changes section. Duplicating it in prose wastes the reviewer's time.

### Issue linking
If `--fixes #N` or `--closes #N` was passed, add the footer after the test plan:

```markdown
Fixes #123
```

### Body rules:
- Focus on **why**, not **what** — the diff shows what changed.
- The entire body should be under 10 lines. If you need more, the PR is too large — split it.
- Test plan should be actionable — exact commands and specific manual steps.
- **Never** include `Co-Authored-By`, `Co-authored-by`, or any authorship trailers.
- **Never** include "Generated with Claude Code" or similar attribution lines.
- **Never** list files changed, code patterns added, or restate what the diff shows.

## Step 6: Safety Scan

Check that the diff doesn't include:
- `.env`, `.env.*` files
- `*.pem`, `*.key`, `*.p12`, `*.pfx` certificates
- `credentials.json`, `service-account.json`
- `id_rsa`, `id_ed25519`, `*.pub` SSH keys
- `*.sqlite`, `*.db` databases
- `*.secret`, `*_secret*`

If any are found, **warn the user** and ask whether to proceed.

## Step 7: Confirm and Create

### If `--quick` flag is present:
- Skip confirmation, create immediately.
- Still enforce safety scans and branch protection.

### Standard flow:
Present a summary:

```
Branch:  <branch> → <base>
Commits: <count>
Title:   <proposed title>
Body:    <first 3 lines of body>...
Draft:   yes/no
```

Wait for user approval. Then create the PR:

```bash
gh pr create --title "<title>" --base <base> --body "$(cat <<'EOF'
<body content>
EOF
)"
```

Add `--draft` if the flag was passed.

## Step 8: Post-creation Summary

After a successful PR creation, show:

```
Created: <PR URL>
Title:   <title>
Base:    <base> ← <branch>
Status:  <draft|ready>
```

## Edge Cases

- **No remote:** Tell the user to add a remote first.
- **Branch already has a PR:** `gh pr view` to check — show the existing PR URL instead of creating a duplicate.
- **Merge conflicts with base:** Warn the user but still create the PR — conflicts can be resolved later.
- **Large PRs (>20 files):** Warn the user and suggest splitting if possible, but proceed if they confirm.
- **Force push needed:** Never force push. If the remote has diverged, tell the user to pull/rebase first.
