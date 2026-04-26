---
name: ship
description: Automates the full git shipping workflow for the e-invoicing project: runs all tests, commits any uncommitted changes, pushes the current branch to GitHub, creates a PR to main (if one doesn't exist), and merges it. Use this skill whenever the user wants to push code, ship a feature, open a PR, merge to main, or says things like "/ship", "push this", "let's ship", "create the PR", "merge to main", or "send it to GitHub". Always use this skill for end-of-sprint or end-of-feature git workflows — don't just run git commands manually.
---

# Ship Skill

Automate the full workflow: test → commit → push → PR → merge → back to main.

## Before you start

Check two things:
1. Run `git branch --show-current` — if the result is `main`, STOP and tell the user they are already on main. Ask which branch they meant to ship.
2. Run `gh auth status` — if gh is not authenticated, STOP and tell the user to run `gh auth login` first, then retry.

## Step 1 — Run tests

```bash
docker-compose exec api python -m pytest tests/ -v
```

- If all tests pass → continue
- If any test fails → STOP immediately. Show which tests failed. Do NOT proceed with git or PR steps. Tell the user to fix the failures first.

## Step 2 — Commit uncommitted changes (if any)

Check if there is anything to commit:
```bash
git status --short
```

If the output is empty → skip this step (nothing to commit).

If there are changes:
- Stage only the relevant tracked files (avoid `.env`, secrets, binaries)
- Write a concise commit message that describes what changed (follow the existing commit style: `feat(scope): description`)
- Commit normally — do not skip hooks (`--no-verify`)

## Step 3 — Push (if needed)

Check if there is anything to push:
```bash
git log origin/<current-branch>..HEAD --oneline
```

If empty → skip (already up to date on remote).

If there are commits to push:
```bash
git push origin <current-branch>
```

## Step 4 — Create PR (if one doesn't exist)

Check if a PR already exists for this branch:
```bash
gh pr list --head <current-branch> --state open
```

If a PR exists → skip creation, note the existing PR URL, go to Step 5.

If no PR exists:
```bash
gh pr create --base main --head <current-branch> \
  --title "<concise title describing the changes>" \
  --body "<summary of what changed, why, and test status>"
```

The PR body should mention: what sprint/feature this is, what was built, and that all tests are passing.

## Step 5 — Merge

```bash
gh pr merge --squash --auto
```

If the merge is blocked (branch protection, required reviews, failing checks) → STOP. Tell the user what is blocking the merge and what they need to do (e.g., "This PR requires 1 approval on GitHub before it can be merged."). Show the PR URL so they can go approve it.

## Step 6 — Return to main

After a successful merge:
```bash
git checkout main
git pull origin main
```

Tell the user: the branch has been merged, they are now on main, and the feature is shipped.

## Summary output

After completing all steps, give a short summary like:

```
✅ Shipped feature/sprint-2 → main
- Tests: 20/20 passing
- Committed: <N files> (or "nothing new to commit")
- Pushed: yes (or "already up to date")
- PR: #<number> — <title>
- Merged: squash merge
- Now on: main
```

If any step was skipped (e.g., nothing to commit, already pushed), note that in the summary.
