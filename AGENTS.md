# Agent Instructions

This project uses **bd** (beads) for issue tracking. Run `bd onboard` to get started.

## Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>         # Complete work
bd sync               # Sync with git
```

## ⚠️ MANDATORY: Claim Issues Before Starting Work

**CRITICAL RULE**: You MUST claim an issue BEFORE starting any work on it.

### Why This Matters

- **Prevents Duplication**: Multiple agents may be working simultaneously
- **Coordination**: Other agents can see what's being worked on
- **Tracking**: Properly tracks who is working on what
- **Efficiency**: Avoids wasted effort from multiple agents doing the same work

### Required Workflow for Every Task

**BEFORE you write any code or start implementation:**

1. **Find Available Work**:
   ```bash
   export BEADS_NO_DAEMON=1  # Recommended for worktrees
   bd ready
   ```

2. **Review Task Details**:
   ```bash
   bd show <id>
   ```

3. **CLAIM THE TASK** (MANDATORY):
   ```bash
   bd update <id> --status in_progress
   ```
   **⚠️ DO NOT SKIP THIS STEP** - Failing to claim the task means another agent may start working on it simultaneously.

4. **Create Feature Branch**:
   ```bash
   git checkout -b task/<task-number>-<short-description>
   ```

5. **Implement Solution**:
   - Write code
   - Write tests (TDD - alongside implementation)
   - **MANDATORY: Run quality checks BEFORE committing**:
     ```bash
     # Check linting
     uv run ruff check .
     uv run ruff format --check .
     uv run black --check .
     uv run mypy google_contacts_cisco
     
     # Run tests
     uv run pytest -v
     ```
   - **FIX ALL LINTING ERRORS AND TEST FAILURES BEFORE COMMITTING**
   - Never commit code with linting errors or failing tests

6. **Mark Task Complete**:
   ```bash
   bd close <id>
   ```

7. **Sync, Commit, and Push**:
   ```bash
   bd sync
   
   # MANDATORY: Final quality check before committing
   uv run ruff check . && uv run ruff format . && uv run pytest -v
   
   # Only commit if all checks pass
   git add -A
   git commit -m "..."
   git push -u origin <branch-name>
   ```

8. **Create Pull Request** (MANDATORY):
   - Use GitHub MCP tools to create PR
   - Include summary, changes, test results
   - Reference issue ID in PR body

### Common Mistakes to Avoid

❌ **WRONG** - Missing critical steps:
```bash
# Start coding immediately after seeing "Execute the next available task"
git checkout -b task/feature
# Write code...
bd close <id>              # Claim and close at the end
git push                   # Push but forget PR - INCOMPLETE!
```

✅ **CORRECT** - Complete workflow:
```bash
bd ready                    # 1. Find work
bd show <id>               # 2. Review details
bd update <id> --status in_progress  # 3. CLAIM FIRST (mandatory!)
git checkout -b task/feature         # 4. Create branch
# Write code and tests...             5. Implement
uv run ruff check . && uv run pytest -v  # 5b. MANDATORY: Check linting & tests
bd close <id>              # 6. Mark complete
bd sync                    # 7. Sync with git
uv run ruff format .       # 8a. Format code
git add -A && git commit   # 8b. Commit changes (only if checks pass)
git push -u origin task/feature     # 9. Push to remote
# Use GitHub MCP to create PR        10. CREATE PR (mandatory!)
```

**⚠️ CRITICAL**: Steps 3 (claim) and 10 (create PR) are MANDATORY and often forgotten!

## Detailed Task Execution Workflow

For comprehensive guidance on executing tasks, including implementation, testing, code review, and PR creation, see:

**[.ai/prompts/task-execution.md](.ai/prompts/task-execution.md)**

This document provides:
- Complete 10-step workflow from task selection to PR creation
- Code quality standards and testing philosophy
- Commit message guidelines and PR templates
- Common pitfalls and troubleshooting
- Integration with beads issue tracking

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until a PR is created.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - **MANDATORY BEFORE COMMITTING**:
   ```bash
   # Check all linting
   uv run ruff check .
   uv run ruff format --check .
   uv run black --check .
   uv run mypy google_contacts_cisco
   
   # Run all tests
   uv run pytest -v
   
   # Fix any errors before proceeding
   ```
   **NEVER commit code with linting errors or failing tests**
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **CREATE PULL REQUEST** - This is MANDATORY:
   - Use GitHub MCP tools to create PR
   - Include comprehensive summary of changes
   - List all acceptance criteria met
   - Include test results
   - Reference the issue ID in PR body
   - NEVER skip this step - a pushed branch without a PR is incomplete work
6. **Clean up** - Clear stashes, prune remote branches
7. **Verify** - All changes committed, pushed, AND PR created
8. **Hand off** - Provide PR URL and context for next session

**CRITICAL RULES:**
- **NEVER commit code with linting errors or failing tests** - Always run `uv run ruff check .` and `uv run pytest -v` before committing
- **Always format code** - Run `uv run ruff format .` before committing
- Work is NOT complete until PR is created
- NEVER stop after just pushing - YOU must create the PR
- NEVER say "ready to create PR when you are" - YOU must create it
- If PR creation fails, resolve and retry until it succeeds
- A pushed branch without a PR is INCOMPLETE
- **Quality gates are MANDATORY** - Linting and tests must pass before every commit

