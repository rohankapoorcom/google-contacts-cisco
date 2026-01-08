# Task Execution Prompt

## Overview

You are working on the **Google Contacts Cisco Directory** project, a comprehensive application that synchronizes Google Contacts and exposes them as a Cisco-formatted XML directory for IP phones, along with a modern web interface for contact management.

This project has been fully planned with 25 detailed implementation tasks organized across 8 phases. Your role is to engineer the solution for a **specific task** following the implementation guide provided.

## Project Structure

- **Planning Documents**: `.ai/planning/` - Contains project overview, requirements, architecture, and technology stack documentation
- **Task Index**: `.ai/planning/tasks/00-task-index.md` - Master index of all 25 tasks with dependencies, priorities, and time estimates
- **Task Files**: `.ai/planning/tasks/01-*.md` through `.ai/planning/tasks/25-*.md` - Standalone implementation guides with complete code examples

## Execution Workflow

When starting work, follow this systematic 10-step workflow:

### 0. Task Selection Phase

**Objective**: Find and claim an available task from beads

#### Find Available Work

```bash
# List all tasks ready to be worked on
bd ready
```

This shows tasks that:
- Have all dependencies completed
- Are not currently assigned or in progress
- Are ready for implementation

#### Review Task Details

```bash
# View detailed information about a specific task
bd show <id>

# Example:
bd show 5
```

This displays:
- Task title and description
- Current status and priority
- Dependencies and blockers
- Acceptance criteria
- Implementation notes
- Related files and documentation

#### Claim the Task

Once you've selected a task to work on:

```bash
# Mark the task as in progress and assign it to yourself
bd update <id> --status in_progress

# Example:
bd update 5 --status in_progress
```

**Task Selection Tips**:
- Start with tasks that have no pending dependencies
- Check priority levels - focus on high-priority items first
- Review time estimates to match your available working time
- Verify you have the necessary context and skills for the task
- Ensure the task description is clear before starting

### 1. Review Phase

**Objective**: Understand the task requirements and context

- [ ] Read the task details from `bd show <id>` thoroughly
- [ ] If task references planning documents, read the assigned task file from `.ai/planning/tasks/`
- [ ] Review the task's dependencies listed in beads and the task index
- [ ] Verify that all prerequisite tasks are completed
- [ ] Check the acceptance criteria checklist
- [ ] Review any related documentation linked in the task file
- [ ] Understand the technical context and design decisions

**Key Questions to Answer**:
- What is the task trying to accomplish?
- What are the acceptance criteria?
- What dependencies must be in place?
- What tests are required?
- What are the common pitfalls to avoid?

### 2. Branch Creation

**Objective**: Create an isolated development environment

```bash
# Create a feature branch using the task naming convention
git checkout -b task/{task-number}-{short-description}

# Example:
git checkout -b task/01-environment-setup
```

**Branch Naming Convention**:
- Format: `task/{number}-{kebab-case-description}`
- Keep description short but descriptive
- Match the task file name for clarity

### 3. Implementation Phase

**Objective**: Implement the solution according to task specifications

#### Code Implementation

- [ ] Follow the implementation steps in sequential order
- [ ] Use the code examples provided (they are production-ready)
- [ ] Maintain consistent code style and formatting
- [ ] Add comprehensive inline comments for complex logic
- [ ] Implement proper error handling and logging
- [ ] Follow Python/JavaScript best practices

#### Test-Driven Development (TDD)

**⚠️ Critical**: Tests are NOT separate - write them AS YOU CODE

- [ ] Write unit tests alongside implementation code
- [ ] Aim for >80% code coverage minimum
- [ ] Use the test examples provided in the task file
- [ ] Test edge cases and error conditions
- [ ] Verify all tests pass before proceeding

#### Code Quality Standards

- **Python Backend**:
  - Follow PEP 8 style guidelines
  - Use type hints for function signatures
  - Write docstrings for classes and functions
  - Use async/await for I/O operations
  - Handle exceptions gracefully

- **TypeScript Frontend** (Vue 3):
  - Use Composition API with `<script setup>`
  - Maintain strong typing (no `any`)
  - Use composables for reusable logic
  - Follow Vue style guide conventions
  - Implement proper component lifecycle

- **General**:
  - Keep functions small and focused (single responsibility)
  - Use meaningful variable and function names
  - Avoid code duplication (DRY principle)
  - Add comments for "why", not "what"
  - Consider security implications

### 4. Verification Phase

**Objective**: Ensure the implementation meets all acceptance criteria

#### Automated Verification

```bash
# Run unit tests with coverage
pytest --cov=google_contacts_cisco --cov-report=term-missing

# Run linters and type checkers
ruff check .
mypy google_contacts_cisco/

# Run frontend tests (if applicable)
cd frontend && npm run test
```

#### Manual Verification

- [ ] Review each acceptance criterion from the task file
- [ ] Test the functionality manually if applicable
- [ ] Verify error handling with invalid inputs
- [ ] Check performance metrics if specified
- [ ] Review the verification steps in the task file

#### Completeness Checklist

- [ ] All code is implemented and functional
- [ ] All unit tests written and passing
- [ ] Code coverage meets minimum threshold (>80%)
- [ ] All acceptance criteria satisfied
- [ ] No linter errors or warnings
- [ ] Type checking passes (no mypy errors)
- [ ] Documentation comments added
- [ ] No TODO or FIXME comments left in code

### 5. Code Review Phase

**Objective**: Self-review for quality and accuracy

Perform a thorough self-review:

- [ ] **Correctness**: Does the code solve the problem correctly?
- [ ] **Completeness**: Are all requirements met?
- [ ] **Quality**: Is the code maintainable and well-structured?
- [ ] **Security**: Are there any security vulnerabilities?
- [ ] **Performance**: Are there any obvious performance issues?
- [ ] **Testing**: Is test coverage adequate?
- [ ] **Documentation**: Are complex parts well-documented?
- [ ] **Error Handling**: Are errors handled gracefully?

Use these commands to aid review:

```bash
# Check for common issues
git diff --check

# Review changes
git diff

# Check test coverage
pytest --cov=google_contacts_cisco --cov-report=html
# Open htmlcov/index.html to review coverage visually
```

### 6. Task Status Update

**Objective**: Mark the task as complete in beads and documentation

#### Close the Task in Beads

```bash
# Mark the task as complete in beads
bd close <id>

# Example:
bd close 5
```

This command:
- Updates the task status to completed
- Records completion timestamp
- Unblocks any dependent tasks
- Updates project progress tracking

#### Update Task Documentation (if applicable)

If the task has a corresponding file in `.ai/planning/tasks/`, update it to indicate completion:

- [ ] Add a completion marker at the top of the task file
- [ ] Document any deviations from the planned approach
- [ ] Note any lessons learned or issues encountered
- [ ] Update estimated vs. actual time spent (optional)

**Example Completion Marker**:

```markdown
## Task Status

**Status**: ✅ Completed  
**Completed Date**: December 18, 2024  
**Actual Time**: 4 hours  
**Implemented By**: AI Assistant  
**Notes**: Implementation completed as specified. No major deviations.
```

Add this section right after the task overview/description.

### 7. Commit Phase

**Objective**: Create a clean, descriptive commit

#### Commit Message Guidelines

Follow the conventional commit format:

```
<type>(<scope>): <short summary>

<detailed description>

- Key change 1
- Key change 2
- Key change 3
```

**Types**:
- `feat`: New feature implementation
- `fix`: Bug fix
- `refactor`: Code refactoring without feature changes
- `test`: Adding or updating tests
- `docs`: Documentation updates
- `chore`: Build, configuration, or tooling changes

**Examples**:

```bash
# Example 1: Foundation task
feat(env): setup project environment with uv and devcontainer

Implements Task 01: Environment Setup
- Configure pyproject.toml with all dependencies
- Set up semantic versioning with _version.py
- Add devcontainer for consistent development environment
- Create placeholder modules for project structure
- Add comprehensive unit tests with >90% coverage

# Example 2: Feature implementation
feat(sync): implement full contact synchronization

Implements Task 07: Full Sync Implementation
- Add FullSyncService with batch processing
- Integrate Google People API for contact retrieval
- Store contacts and phone numbers in database
- Add progress tracking and error handling
- Include comprehensive test suite with mocking

# Example 3: Bug fix during implementation
fix(oauth): handle token refresh race condition

- Add lock mechanism for token refresh
- Prevent multiple simultaneous refresh attempts
- Add test coverage for concurrent token access
```

#### Committing Changes

```bash
# Review what will be committed
git status
git diff

# Stage all changes
git add .

# Commit with a descriptive message
git commit -m "feat(scope): description

Detailed notes here..."

# Verify commit
git log -1 --stat

# Sync beads with git commits
bd sync
```

**Note**: The `bd sync` command keeps beads issue tracking synchronized with your git commit history, ensuring task progress is accurately reflected.

### 8. Pull Request Phase

**Objective**: Create a pull request for code review and integration

#### PR Creation Guidelines

After committing your changes, create a pull request to merge your feature branch into the main branch. Use the GitHub MCP tools to create the PR programmatically.

#### Prerequisites

Before creating a PR:
- [ ] All changes are committed locally
- [ ] Branch has been pushed to remote repository
- [ ] All tests pass locally
- [ ] Code quality checks pass (linter, type checker)
- [ ] Task file has been updated with completion status

#### Push Branch to Remote

```bash
# Push branch to remote (first time)
git push -u origin task/{task-number}-{description}

# Or if already tracking
git push
```

#### PR Title Format

Follow the same convention as commit messages:

```
<type>(<scope>): <short summary>
```

**Examples**:
- `feat(auth): implement OAuth 2.0 authentication with Google`
- `feat(db): setup database with SQLAlchemy and Alembic`
- `fix(oauth): handle token refresh race condition`

#### PR Description Template

Create a comprehensive PR description that includes:

```markdown
## Overview

Brief description of what this PR accomplishes and which task it implements.

## Changes

### [Module/Component Name]
- ✅ Feature or change 1
- ✅ Feature or change 2
- ✅ Feature or change 3

### [Another Module/Component]
- ✅ Additional changes

### Features
- Key feature 1
- Key feature 2
- Key feature 3

## Testing

- ✅ **X comprehensive unit tests** covering [what]
- ✅ **Y% code coverage** for [modules]
- ✅ Tests for success paths, error handling, and edge cases
- ✅ All [N] project tests pass

### Test Coverage
- What is tested
- Edge cases covered
- Integration scenarios

## Quality Checks

- ✅ All tests pass ([N]/[N])
- ✅ Code coverage: X% (exceeds 80% requirement)
- ✅ Ruff linter: All checks pass
- ✅ Mypy type checking: No issues found
- ✅ Follows project coding standards

## Security

- Security consideration 1
- Security consideration 2

## Related

- Implements: `.ai/planning/tasks/{task-number}-{task-name}.md`
- Dependencies: Task X, Task Y ✅

## Next Steps

After merge, this enables:
- Next task or feature
- Related functionality
```

#### Creating the PR with GitHub MCP

Use the `mcp_github_create_pull_request` tool:

**Required Parameters**:
- `owner`: Repository owner (e.g., "rohankapoorcom")
- `repo`: Repository name (e.g., "google-contacts-cisco")
- `title`: PR title following conventional commit format
- `head`: Feature branch name (e.g., "task/04-oauth-implementation")
- `base`: Base branch (typically "main" or "master")

**Optional Parameters**:
- `body`: Detailed PR description (use template above)
- `draft`: Set to `true` if PR is work-in-progress

**Example**:
```python
mcp_github_create_pull_request(
    owner="rohankapoorcom",
    repo="google-contacts-cisco",
    title="feat(auth): implement OAuth 2.0 authentication with Google",
    head="task/04-oauth-implementation",
    base="main",
    body="[PR description using template above]",
    draft=False
)
```

#### Getting Repository Information

If you need to determine the repository owner and name:

```bash
# Get remote URL
git remote -v

# Extract owner/repo from URL like:
# origin  git@github.com:owner/repo.git
# or
# origin  https://github.com/owner/repo.git
```

#### PR Best Practices

1. **Clear Title**: Use conventional commit format, be specific
2. **Comprehensive Description**: Include all relevant details
3. **Link to Task**: Reference the task file being implemented
4. **Test Results**: Include test counts and coverage percentages
5. **Quality Metrics**: Show that all checks pass
6. **Dependencies**: List prerequisite tasks and their status
7. **Next Steps**: Explain what this PR enables

#### PR Checklist

Before creating the PR:
- [ ] Branch name follows convention: `task/{number}-{description}`
- [ ] All commits follow conventional commit format
- [ ] PR title matches commit message style
- [ ] PR description is comprehensive and follows template
- [ ] All tests pass and coverage meets requirements
- [ ] Code quality checks pass
- [ ] Task file updated with completion status
- [ ] No sensitive data in code or commits
- [ ] Branch is pushed to remote

#### After PR Creation

- [ ] Verify PR was created successfully
- [ ] Check that PR description renders correctly
- [ ] Confirm base and head branches are correct
- [ ] Note the PR number and URL for reference
- [ ] Update task file with PR link (optional)

### 9. Final Checklist

Before considering the task complete:

- [ ] Task claimed in beads with `bd update <id> --status in_progress`
- [ ] Branch created and checked out
- [ ] Task details reviewed and understood (via `bd show <id>`)
- [ ] All implementation steps completed
- [ ] Unit tests written and passing (>80% coverage)
- [ ] Code self-reviewed for quality and accuracy
- [ ] All acceptance criteria verified
- [ ] Linters and type checkers passing
- [ ] Task closed in beads with `bd close <id>`
- [ ] Task file updated with completion status (if applicable)
- [ ] Changes committed with descriptive message
- [ ] Branch pushed to remote repository
- [ ] Pull request created (if applicable)
- [ ] Ready to proceed to next task

---

## Important Guidelines

### Testing Philosophy

**⚠️ Critical**: Tests are an integral part of implementation, not a separate phase.

- Write tests ALONGSIDE your code (TDD approach recommended)
- Each function/class should have corresponding tests
- Don't mark a task "complete" until tests are written and passing
- Minimum 80% coverage required per module
- Focus on testing behavior, not implementation details

### Dependency Management

- Always verify dependencies are completed before starting
- If a dependency is incomplete, address it first
- Dependencies are listed in each task file and the task index
- Some tasks can be parallelized if dependencies allow

### Performance Considerations

Keep these performance targets in mind:

- **Cisco XML Directory**: Response time <100ms
- **Search API**: Response time <250ms
- **Database**: Support 10,000+ contacts efficiently
- **Sync Operations**: Use incremental sync after initial full sync

### Security Best Practices

- Never commit sensitive credentials or API keys
- Use environment variables for configuration
- Validate all user inputs with Pydantic models
- Implement proper error handling (don't leak sensitive info)
- Use HTTPS for production deployments
- Follow OAuth 2.0 best practices for token management

### Code Organization

The project follows this structure:

```
google_contacts_cisco/
├── __init__.py
├── _version.py
├── main.py              # FastAPI application entry point
├── api/                 # API endpoints (routers)
├── auth/                # OAuth and authentication
├── models/              # SQLAlchemy database models
├── repositories/        # Database access layer
├── services/            # Business logic
└── utils/               # Helper utilities

frontend/                # Vue 3 + TypeScript frontend
├── src/
│   ├── components/      # Vue components
│   ├── views/           # Page views
│   ├── composables/     # Reusable composition functions
│   ├── types/           # TypeScript type definitions
│   └── utils/           # Helper utilities

tests/                   # Test suite
├── unit/                # Unit tests (mirror src structure)
├── integration/         # Integration tests
└── e2e/                 # End-to-end tests
```

### Common Pitfalls to Avoid

1. **Skipping Tests**: Don't defer test writing - write tests as you code
2. **Ignoring Dependencies**: Ensure prerequisite tasks are truly complete
3. **Copying Without Understanding**: Understand the code, don't just copy-paste
4. **Incomplete Error Handling**: Always handle exceptions and edge cases
5. **Poor Commit Messages**: Write clear, descriptive commit messages
6. **Not Verifying Acceptance Criteria**: Check each criterion explicitly
7. **Leaving Debug Code**: Remove console.log, print statements, and breakpoints
8. **Ignoring Type Checking**: Resolve all mypy and TypeScript errors

### Getting Help

If you encounter issues:

1. **Review Related Documentation**: Check links in the task file
2. **Check Architecture Docs**: Review `.ai/planning/` for design decisions
3. **Look at Previous Tasks**: Similar patterns may be used elsewhere
4. **Review Common Issues**: Each task file has a "Common Issues" section
5. **Consult Official Docs**: Links provided in each task file

---

## Success Criteria

A task is successfully completed when:

✅ All acceptance criteria are met  
✅ All unit tests written and passing (>80% coverage)  
✅ Code passes all linters and type checkers  
✅ Functionality verified manually (if applicable)  
✅ Code reviewed for quality and security  
✅ Task file updated with completion status  
✅ Changes committed with descriptive message  
✅ Branch pushed to remote repository  
✅ Pull request created (if applicable)  
✅ No known bugs or issues remaining  

---

## Next Steps

After completing a task:

1. **Create Pull Request**: Use GitHub MCP tools to create a PR for code review
2. **Review the Task Index**: Check what tasks are now unblocked
3. **Plan Next Task**: Identify the next task in the dependency chain
4. **Take a Break**: Complex tasks are mentally demanding
5. **Share Knowledge**: Document any insights or learnings

**Note**: You can create a PR after each task completion, or wait for logical milestones (e.g., after completing a phase). Use your judgment based on project workflow.

---

## Additional Resources

- **Task Index**: `.ai/planning/tasks/00-task-index.md`
- **Project Overview**: `.ai/planning/01-project-overview.md`
- **Architecture**: `.ai/planning/03-architecture.md`
- **Technology Stack**: `.ai/planning/04-technology-stack.md`
- **Cisco XML Requirements**: `.ai/planning/06-cisco-xml-requirements.md`

---

## Ready to Begin?

When you're ready to execute a task:

1. Run `bd ready` to find available tasks
2. Use `bd show <id>` to review task details
3. Claim the task with `bd update <id> --status in_progress`
4. Follow the 10-step execution workflow above (starting from step 0)
5. Use the task details and any referenced planning documents as your implementation guide
6. Maintain high code quality and test coverage standards
7. Close the task with `bd close <id>` when all criteria are satisfied

**Let's build something great! 🚀**

---

*Version: 1.0*  
*Last Updated: December 18, 2024*  
*Project: Google Contacts Cisco Directory*
