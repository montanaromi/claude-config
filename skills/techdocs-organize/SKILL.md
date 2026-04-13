---
name: techdocs-organize
description: Audit and organize TechDocs for Backstage catalog components — checks mkdocs.yml, docs/, annotations, and Blitzy documentation
allowed-tools: [Bash, Read, Edit, Write, Glob, Grep]
---

# TechDocs Organize

Audit and fix TechDocs configuration for Backstage catalog components. Ensures every component has working documentation that builds and renders in TechDocs.

**Scope:** One repo, a list of repos, or all repos in a GitHub org.

## Arguments

| Argument | Effect |
|----------|--------|
| `<repo-name>` | Audit and fix a single repo (e.g., `blitzy-curl`) |
| `--all` | Audit all repos in the configured org |
| `--check` | Audit only — report issues without fixing |
| `--org <name>` | GitHub org (default: `Blitzy-Sandbox`) |
| *(empty)* | Ask which repo to audit |

## Phase 1: Audit

For each repo, check:

| Check | Pass condition |
|-------|---------------|
| `catalog-info.yaml` exists | File present on default branch |
| `backstage.io/techdocs-ref: dir:.` annotation | Present in metadata.annotations |
| `mkdocs.yml` exists | File present at repo root |
| `mkdocs.yml` has `techdocs-core` plugin | `plugins: [techdocs-core]` or `- techdocs-core` |
| `docs_dir` matches reality | If repo has `doc/` but not `docs/`, `docs_dir: doc` must be set |
| `docs/index.md` exists | File present with meaningful content (not just a title) |
| `blitzy/documentation/` checked | Check default branch and open PR branches |
| Project Guide in docs/ | `docs/project-guide.md` exists if blitzy docs available |
| Technical Specs in docs/ | `docs/technical-specifications.md` exists if blitzy docs available |
| `mkdocs.yml` nav is complete | All docs files listed in nav |
| No upstream conflicts | docs/ doesn't have upstream files that break the build |

**Output:** Table of pass/fail for each check.

## Phase 2: Fix

For each failing check, apply the fix:

| Issue | Fix |
|-------|-----|
| Missing techdocs-ref | Add annotation to catalog-info.yaml via GitHub API |
| Missing mkdocs.yml | Create with site_name, nav, techdocs-core plugin |
| Wrong docs_dir | Add `docs_dir: doc` to mkdocs.yml |
| Missing docs/index.md | Create with repo description from catalog-info.yaml |
| Blitzy docs not in docs/ | Fetch from default or PR branch, push to docs/ |
| Incomplete nav | Update mkdocs.yml nav to include all docs files |
| Upstream conflicts | Switch to `docs_dir: blitzy-docs`, move our files there |

All fixes are pushed via `gh api -X PUT` to the GitHub Contents API.

## Phase 3: Verify

After fixes, trigger a TechDocs sync:
```
curl -s "http://localhost:7007/api/techdocs/sync/default/component/REPO_NAME"
```

Check the last event for `{"updated":true}` or report the error.

## docs/index.md Template

A good index.md has:

```markdown
# {repo-name}

{description from catalog-info.yaml}

## Tech Stack

- **Language:** {from tags}
- **Type:** {from spec.type}
- **Lifecycle:** {from spec.lifecycle}

## Quick Links

- [GitHub Repository](https://github.com/Blitzy-Sandbox/{repo-name})
- [Blitzy PR](https://github.com/Blitzy-Sandbox/{repo-name}/pull/1)
```

If a Project Guide exists, the index should link to it rather than duplicate content.

## Organization Principles

1. **index.md** — project summary, tech stack, quick links
2. **project-guide.md** — Blitzy Project Guide (architecture, status, human tasks)
3. **technical-specifications.md** — Blitzy Technical Specifications (detailed design)
4. Nav order: Home > Project Guide > Technical Specifications
5. For repos with upstream `docs/` that conflicts, use `docs_dir: blitzy-docs` and a separate directory

## Edge Cases

- **No catalog-info.yaml** — Skip. Report: "No catalog entry for {repo}."
- **No blitzy docs anywhere** — Create only index.md. Report: "No Blitzy documentation found."
- **Large upstream docs/** — Don't touch upstream files. Use separate docs_dir.
- **PR branch docs only** — Fetch from PR branch, push to default.
- **mkdocs build fails** — Check error, likely upstream file conflicts. Switch docs_dir.

## Composability

- After organizing: "Run the app and navigate to the component's Documentation tab to verify."
- For new repos: "Add a catalog-info.yaml first, then run `/techdocs-organize <repo>`."
- For style cleanup: "Run `/kurt docs/index.md` to tighten the prose."
