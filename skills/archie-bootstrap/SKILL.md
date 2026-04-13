---
name: archie-bootstrap
description: Set up the Blitzy dev environment with archie-bootstrap and persist shell state to .archie-env
allowed-tools: [Read, Write, Glob, Grep, Bash]
---

# Archie Bootstrap — Dev Environment Setup with Shell Persistence

You are setting up the Blitzy development environment by running `archie-bootstrap` and persisting the shell environment so it survives after the agent closes.

## Arguments

`$ARGUMENTS` may contain:

| Arg | Effect |
|-----|--------|
| `dev` | Bootstrap for development (default) |
| `ci` | Bootstrap for CI environment |
| `--skip-make` | Skip the `make` build step |
| (empty) | Same as `dev` |

## Step 1: Detect Project Root

Find the project root by looking for these markers (walk up from cwd):
- `archie-bootstrap` script
- `Makefile` with archie targets
- `.archie-env` (already bootstrapped)

If `.archie-env` already exists, ask the user:
> "Environment snapshot `.archie-env` already exists. Re-bootstrap? (This will overwrite the existing snapshot.)"

## Step 2: Capture Environment Before

Save the current environment state:

```bash
env | sort > /tmp/archie-before.env
```

## Step 3: Run archie-bootstrap

Run the bootstrap in a subshell that captures the resulting environment:

```bash
bash -c 'source ./archie-bootstrap $ARGUMENTS 2>&1 && env | sort' > /tmp/archie-after.env
```

If the bootstrap fails, report the error output and stop.

## Step 4: Generate .archie-env Snapshot

Compute the environment delta and write it as a sourceable file:

```bash
# Find new/changed env vars
comm -13 /tmp/archie-before.env /tmp/archie-after.env | sed 's/^/export /' > .archie-env

# Add venv activation if VIRTUAL_ENV was set
grep -q VIRTUAL_ENV .archie-env && echo 'source "$VIRTUAL_ENV/bin/activate" 2>/dev/null' >> .archie-env
```

## Step 5: Verify

Source the snapshot in a fresh subshell and verify key env vars are present:

```bash
bash -c 'source .archie-env && echo "VIRTUAL_ENV=$VIRTUAL_ENV" && echo "PATH includes venv: $(echo $PATH | grep -c venv)"'
```

## Step 6: Report and Print Shell Instructions

Print the results and the exact commands for the user:

```
Environment snapshot written to .archie-env

To activate now (in your current shell):
  source .archie-env

To auto-activate whenever you cd into this project, add this to your shell config (~/.zshrc or ~/.bashrc):

  # Blitzy auto-activate env on cd
  blitzy-env-hook() {
    [[ -f .archie-env ]] && source .archie-env
  }
  chpwd_functions+=(blitzy-env-hook)
```

**Important:** Print these instructions exactly as shown. Do NOT modify the user's shell config automatically.

## Rules

- Never modify ~/.zshrc, ~/.bashrc, or any shell config file — only print instructions
- Always write .archie-env to the project root
- The .archie-env file must be sourceable (`source .archie-env` must work)
- Clean up /tmp/archie-before.env and /tmp/archie-after.env after generating the snapshot
- If archie-bootstrap doesn't exist in the project, stop: "No archie-bootstrap script found. This skill requires a Blitzy project with archie-bootstrap."

## Composability

After bootstrap, suggest:
- "Run `/blitzy-onboarding` to continue the full developer onboarding flow."
- "Run `/onboard` to generate an architecture overview of this codebase."
