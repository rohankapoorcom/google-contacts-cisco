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
   - Verify quality checks

6. **Mark Task Complete**:
   ```bash
   bd close <id>
   ```

7. **Sync and Commit**:
   ```bash
   bd sync
   git add -A
   git commit -m "..."
   ```

### Common Mistake to Avoid

❌ **WRONG**:
```bash
# Start coding immediately after seeing "Execute the next available task"
git checkout -b task/feature
# Write code...
bd close <id>  # Claim and close at the end
```

✅ **CORRECT**:
```bash
bd ready                    # Find work
bd show <id>               # Review details
bd update <id> --status in_progress  # CLAIM FIRST
git checkout -b task/feature
# Write code...
bd close <id>              # Mark complete
bd sync                    # Sync with git
```

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

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds

