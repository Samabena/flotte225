---
name: audit
description: Run a full code quality and security audit on the e-invoicing backend. Checks linting (ruff), formatting (black), security vulnerabilities in code (bandit), and known CVEs in dependencies (safety). Reports all issues by severity and auto-fixes safe linting/formatting issues. Use whenever the user wants to audit code quality, check for security issues, or enforce coding standards. Triggers on "/audit", "run audit", "check security", "lint the code", "code quality check", "find vulnerabilities", "check dependencies".
---

# Audit Skill

Run a full code quality and security audit: lint → format → security scan → dependency CVE check.

---

## Before you start

Check that Docker is running:
```bash
docker-compose ps
```

If the `api` container is not running → start it:
```bash
docker-compose up -d
```

---

## Step 1 — Ensure audit tools are installed

Install the required tools inside the container if not already present:
```bash
docker-compose exec api pip install ruff black bandit safety --quiet
```

These tools are not in `requirements.txt` by default (they are dev-only). Do NOT add them to `requirements.txt`.

---

## Step 2 — Linting with ruff

Run ruff on the full backend source:
```bash
docker-compose exec api ruff check app/ tests/ --output-format=concise
```

Capture the output. Note any errors and warnings.

Then **auto-fix** all safe issues:
```bash
docker-compose exec api ruff check app/ tests/ --fix --output-format=concise
```

Report how many issues were fixed automatically vs. how many remain.

---

## Step 3 — Formatting with black

Check for formatting violations:
```bash
docker-compose exec api black app/ tests/ --check --diff
```

If violations are found, **auto-fix** them:
```bash
docker-compose exec api black app/ tests/
```

Report which files were reformatted (if any).

---

## Step 4 — Security scan with bandit

Scan for common security issues (SQL injection, hardcoded secrets, insecure functions, etc.):
```bash
docker-compose exec api bandit -r app/ -f txt -ll
```

Flags:
- `-r app/` — recursive scan of the app directory only (not tests)
- `-ll` — only show MEDIUM and HIGH severity issues (skip LOW noise)
- `-f txt` — plain text output

Group findings by severity:
- **HIGH** — must fix before shipping
- **MEDIUM** — should fix, review carefully
- LOW is suppressed by `-ll` flag

If no issues → print "No medium/high security issues found."

---

## Step 5 — Dependency CVE check with safety

Check all installed packages for known CVEs:
```bash
docker-compose exec api safety check --full-report
```

If this command requires authentication (safety v3+), use:
```bash
docker-compose exec api pip install "safety<3" --quiet
docker-compose exec api safety check --full-report
```

Group findings by:
- **Critical / High** — must update before shipping
- **Medium / Low** — review and plan updates

If no vulnerabilities → print "All dependencies are CVE-free."

---

## Step 6 — Run tests to confirm nothing is broken

After auto-fixes (ruff + black), confirm tests still pass:
```bash
docker-compose exec api python -m pytest tests/ -q
```

- If all pass → continue to report
- If any fail → revert the auto-fixes (ruff/black should not break tests, but if they do, investigate and report to the user)

---

## Step 7 — Summary report

Print a structured report:

```
╔══════════════════════════════════════════╗
║         CODE AUDIT REPORT                ║
╠══════════════════════════════════════════╣
║ LINTING (ruff)                           ║
║   Auto-fixed: N issues                   ║
║   Remaining:  N issues  ← list them      ║
╠══════════════════════════════════════════╣
║ FORMATTING (black)                       ║
║   Reformatted: N files  ← list them      ║
║   (or) All files correctly formatted ✅  ║
╠══════════════════════════════════════════╣
║ SECURITY (bandit)                        ║
║   HIGH:   N issues  ← list each with file:line + description ║
║   MEDIUM: N issues  ← list each with file:line + description ║
║   (or) No issues found ✅                ║
╠══════════════════════════════════════════╣
║ DEPENDENCIES (safety)                    ║
║   Critical/High: N CVEs  ← list package + CVE + fix version  ║
║   Medium/Low:    N CVEs                  ║
║   (or) All dependencies CVE-free ✅      ║
╠══════════════════════════════════════════╣
║ TESTS                                    ║
║   55/55 passing ✅  (or list failures)   ║
╠══════════════════════════════════════════╣
║ OVERALL STATUS                           ║
║   ✅ Clean  /  ⚠️ Warnings  /  🚨 Action required ║
╚══════════════════════════════════════════╝
```

**Overall status rules:**
- ✅ Clean — zero remaining lint issues, zero medium/high security issues, zero critical/high CVEs
- ⚠️ Warnings — only low/medium CVEs or low bandit findings remain
- 🚨 Action required — any HIGH security issue or critical CVE, or remaining lint errors that block CI

---

## What NOT to do

- Do not modify `requirements.txt` to add dev tools (ruff, black, bandit, safety)
- Do not auto-fix bandit or safety findings — these require manual developer review
- Do not suppress bandit warnings with `# nosec` unless the user explicitly asks
- Do not skip the test run after auto-fixes
- Do not run bandit on the `tests/` directory (test code has intentionally weak patterns)
