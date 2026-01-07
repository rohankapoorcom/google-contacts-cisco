# Code Review Prompt

## Overview

You are conducting a **technical code review** for the **Google Contacts Cisco Directory** project. This project consists of 25 planned implementation tasks across 8 phases, combining a FastAPI backend with a Vue 3 + TypeScript frontend.

A developer (AI or human) has completed a specific task following the task execution workflow. Your role is to **critically review** the implementation to ensure it meets quality standards, acceptance criteria, and best practices before it can be marked as complete.

## Context

### Original Task Instructions

The implementation was completed following these instructions:
- **Task Execution Prompt**: `.ai/prompts/task-execution.md`
- **Task Index**: `.ai/planning/tasks/00-task-index.md`
- **Specific Task File**: (provided in the review context)

### Review Scope

You will be reviewing:
- Code changes in the commit(s) for the task
- Associated unit tests
- Documentation and comments
- Adherence to project standards
- Completion of acceptance criteria

---

## Code Review Framework

Conduct your review across these 10 critical dimensions:

### 1. ✅ Task Completion & Requirements

**Objective**: Verify all task requirements are met

#### Checklist

- [ ] All acceptance criteria from the task file are satisfied
- [ ] Implementation follows the steps outlined in the task file
- [ ] No requirements are missing or partially implemented
- [ ] Task scope is complete (no TODO/FIXME comments)
- [ ] Dependencies on previous tasks are properly utilized
- [ ] Task status is updated in the task file

#### Review Questions

- Does the implementation solve the problem stated in the task?
- Are there any acceptance criteria not met?
- Is anything implemented that wasn't in the requirements (scope creep)?
- Are there any shortcuts taken that compromise quality?

**Rating**: 🟢 Pass | 🟡 Minor Issues | 🔴 Major Issues

---

### 2. 🧪 Testing & Coverage

**Objective**: Ensure comprehensive test coverage and quality

#### Checklist

- [ ] Unit tests are written for all new code
- [ ] Tests cover happy path scenarios
- [ ] Tests cover edge cases and error conditions
- [ ] Tests use appropriate mocking/fixtures
- [ ] Test coverage meets minimum threshold (>80%)
- [ ] All tests pass successfully
- [ ] Test names are descriptive and clear
- [ ] Tests are maintainable and not brittle
- [ ] Async code is tested properly (if applicable)
- [ ] Integration points are tested (if applicable)

#### Specific Checks

```bash
# Verify these commands pass:
pytest --cov=google_contacts_cisco --cov-report=term-missing
pytest -v  # All tests passing
ruff check .  # No linting errors
mypy google_contacts_cisco/  # No type errors
```

#### Common Testing Issues

- ❌ Missing tests for error handling
- ❌ Tests that don't actually test the functionality
- ❌ Hard-coded values instead of proper test data
- ❌ Tests that depend on external services without mocking
- ❌ Insufficient coverage of edge cases
- ❌ Tests that are too tightly coupled to implementation

**Rating**: 🟢 Pass | 🟡 Minor Issues | 🔴 Major Issues

---

### 3. 💻 Code Quality & Style

**Objective**: Ensure code is clean, maintainable, and follows standards

#### Python Backend Standards

- [ ] Follows PEP 8 style guidelines
- [ ] Uses type hints for function signatures
- [ ] Docstrings present for classes and public methods
- [ ] Async/await used appropriately for I/O operations
- [ ] No code duplication (DRY principle)
- [ ] Functions are small and focused (single responsibility)
- [ ] Variable and function names are descriptive
- [ ] Constants are properly defined (uppercase)
- [ ] Imports are organized and sorted
- [ ] No unused imports or variables

#### TypeScript/Vue 3 Standards (if applicable)

- [ ] Uses Composition API with `<script setup>`
- [ ] Strong typing (no `any` types)
- [ ] Props and emits properly typed
- [ ] Composables used for reusable logic
- [ ] Components are small and focused
- [ ] Follows Vue style guide conventions
- [ ] CSS is scoped or uses Tailwind classes
- [ ] No console.log or debug statements

#### General Quality

- [ ] Code is self-documenting (clear intent)
- [ ] Complex logic has explanatory comments
- [ ] No commented-out code blocks
- [ ] No magic numbers or strings (use named constants)
- [ ] Error messages are descriptive and actionable
- [ ] Logging is appropriate and informative

**Rating**: 🟢 Pass | 🟡 Minor Issues | 🔴 Major Issues

---

### 4. 🔒 Security & Data Validation

**Objective**: Identify security vulnerabilities and data validation issues

#### Security Checklist

- [ ] No hardcoded credentials or API keys
- [ ] Sensitive data not logged
- [ ] SQL injection prevention (using ORM properly)
- [ ] XSS prevention (Vue auto-escaping, proper sanitization)
- [ ] CSRF protection considered (if applicable)
- [ ] Authentication/authorization implemented correctly
- [ ] OAuth tokens handled securely
- [ ] Environment variables used for sensitive config
- [ ] Input validation with Pydantic models
- [ ] File path traversal vulnerabilities prevented
- [ ] Rate limiting considered for API endpoints

#### Data Validation

- [ ] All user inputs are validated
- [ ] Type checking is enforced
- [ ] Boundary conditions are handled
- [ ] Database constraints are appropriate
- [ ] API responses are properly validated
- [ ] Error responses don't leak sensitive information

**Rating**: 🟢 Pass | 🟡 Minor Issues | 🔴 Major Issues

---

### 5. 🐛 Error Handling & Robustness

**Objective**: Ensure the code handles failures gracefully

#### Error Handling Checklist

- [ ] Try-catch blocks used appropriately
- [ ] Exceptions are specific (not catching bare `Exception`)
- [ ] Errors are logged with appropriate context
- [ ] User-facing error messages are helpful
- [ ] Database transactions are properly committed/rolled back
- [ ] Resource cleanup happens (files, connections, etc.)
- [ ] Async operations handle cancellation
- [ ] Network errors are handled gracefully
- [ ] Timeouts are implemented where needed
- [ ] Retries with backoff for transient failures

#### Edge Cases

- [ ] Null/None values handled
- [ ] Empty collections handled
- [ ] Large datasets considered
- [ ] Concurrent access considered
- [ ] Race conditions prevented

**Rating**: 🟢 Pass | 🟡 Minor Issues | 🔴 Major Issues

---

### 6. ⚡ Performance & Efficiency

**Objective**: Ensure code meets performance requirements

#### Performance Checklist

- [ ] Database queries are optimized (no N+1 queries)
- [ ] Appropriate indexes exist for queries
- [ ] Batch operations used where appropriate
- [ ] Async operations used for I/O
- [ ] Caching implemented where beneficial
- [ ] Large datasets are paginated
- [ ] Memory usage is reasonable
- [ ] No unnecessary computations in loops
- [ ] API endpoints respond within targets (<100-250ms)

#### Specific Targets

- **Cisco XML Directory**: <100ms response time
- **Search API**: <250ms response time
- **Database**: Support 10,000+ contacts
- **Sync Operations**: Efficient incremental sync

#### Common Performance Issues

- ❌ Loading all records instead of paginating
- ❌ Making API calls in loops
- ❌ Not using database indexes
- ❌ Synchronous I/O in async contexts
- ❌ Unnecessary data transformations
- ❌ Loading related data that's not needed

**Rating**: 🟢 Pass | 🟡 Minor Issues | 🔴 Major Issues

---

### 7. 🏗️ Architecture & Design

**Objective**: Ensure code follows architectural patterns

#### Architecture Checklist

- [ ] Follows layered architecture (API → Service → Repository → Model)
- [ ] Separation of concerns maintained
- [ ] Dependency injection used appropriately
- [ ] Database models properly defined with relationships
- [ ] Services contain business logic (not in routes)
- [ ] Repositories handle data access (not in services)
- [ ] DTOs/schemas used for API contracts
- [ ] Configuration managed through Pydantic Settings
- [ ] Follows SOLID principles

#### Design Patterns

- [ ] Appropriate design patterns used
- [ ] Singleton pattern for shared resources
- [ ] Factory pattern for object creation (if needed)
- [ ] Strategy pattern for varying behaviors (if needed)
- [ ] No anti-patterns present

#### Project Structure

- [ ] Files placed in correct directories
- [ ] Module organization is logical
- [ ] Imports follow project conventions
- [ ] Public vs. private methods/functions clearly defined

**Rating**: 🟢 Pass | 🟡 Minor Issues | 🔴 Major Issues

---

### 8. 📚 Documentation & Comments

**Objective**: Ensure code is well-documented

#### Documentation Checklist

- [ ] Docstrings for all classes and public methods
- [ ] Docstrings follow Google or NumPy style
- [ ] Complex algorithms have explanatory comments
- [ ] "Why" comments explain reasoning, not "what"
- [ ] API endpoints have OpenAPI documentation
- [ ] Type hints serve as inline documentation
- [ ] README updated if needed
- [ ] Configuration options documented

#### Comment Quality

- [ ] Comments are accurate and up-to-date
- [ ] No misleading comments
- [ ] No commented-out code
- [ ] TODOs/FIXMEs are resolved or justified

**Example Good Docstring**:

```python
async def sync_contacts(
    self,
    user_id: str,
    full_sync: bool = False
) -> SyncResult:
    """
    Synchronize contacts from Google for a specific user.
    
    Args:
        user_id: The unique identifier for the user
        full_sync: If True, performs full sync. If False, performs incremental.
        
    Returns:
        SyncResult containing sync statistics and status
        
    Raises:
        AuthenticationError: If OAuth token is invalid or expired
        GoogleAPIError: If Google API returns an error
        DatabaseError: If database operations fail
        
    Note:
        Full sync should be used sparingly as it's resource-intensive.
        Incremental sync is recommended for regular operations.
    """
```

**Rating**: 🟢 Pass | 🟡 Minor Issues | 🔴 Major Issues

---

### 9. 🔗 Integration & Dependencies

**Objective**: Ensure proper integration with other components

#### Integration Checklist

- [ ] APIs/interfaces match expected contracts
- [ ] Database schema changes include migrations
- [ ] Dependencies on other tasks are used correctly
- [ ] New dependencies added to `pyproject.toml`/`package.json`
- [ ] Version pinning is appropriate
- [ ] Third-party library usage is idiomatic
- [ ] Configuration variables properly defined
- [ ] Environment variables documented

#### Compatibility

- [ ] Changes are backward compatible (if required)
- [ ] Database migrations are reversible
- [ ] API changes maintain versioning
- [ ] No breaking changes to existing interfaces

**Rating**: 🟢 Pass | 🟡 Minor Issues | 🔴 Major Issues

---

### 10. 🎯 Best Practices & Conventions

**Objective**: Ensure adherence to project-specific and general best practices

#### Project Conventions

- [ ] Follows established naming conventions
- [ ] Consistent with existing codebase style
- [ ] Uses project utilities/helpers where appropriate
- [ ] Logging uses project's logging configuration
- [ ] Error handling follows project patterns

#### Python Best Practices

- [ ] Context managers used for resources (`with` statements)
- [ ] List/dict comprehensions used appropriately
- [ ] F-strings used for string formatting
- [ ] Pathlib used for file paths
- [ ] Dataclasses/Pydantic for data structures
- [ ] Type annotations for better IDE support

#### Vue/TypeScript Best Practices

- [ ] Reactive references used correctly (`ref`, `reactive`)
- [ ] Computed properties for derived state
- [ ] Watch used sparingly (prefer computed)
- [ ] Props are readonly
- [ ] Events emitted for parent communication
- [ ] Composables for cross-component logic

**Rating**: 🟢 Pass | 🟡 Minor Issues | 🔴 Major Issues

---

## Review Execution Process

### Step 1: Prepare for Review

```bash
# Check out the branch
git checkout task/{number}-{description}

# Review the changes
git log --oneline
git diff main --stat
git show HEAD

# Run the test suite
pytest --cov=google_contacts_cisco --cov-report=html
pytest -v

# Run code quality checks
ruff check .
mypy google_contacts_cisco/

# For frontend changes
cd frontend && npm run test && npm run type-check
```

### Step 2: Review Each Dimension

Go through each of the 10 review dimensions above:
1. Read the code changes carefully
2. Check against the checklist items
3. Note any issues or suggestions
4. Assign a rating: 🟢 Pass | 🟡 Minor Issues | 🔴 Major Issues

### Step 3: Test the Implementation

If applicable:
- Run the application locally
- Test the functionality manually
- Verify the feature works as expected
- Test edge cases interactively

### Step 4: Write Review Summary

Create a structured review with:
- Overall assessment
- Dimension ratings
- Critical issues (must fix)
- Suggestions for improvement (nice to have)
- Positive observations
- Final recommendation

---

## Review Output Format

Provide your review in this structured format:

### 📊 Review Summary

**Task**: [Task Number and Name]  
**Reviewer**: [Your Name/AI]  
**Review Date**: [Date]  
**Commit(s) Reviewed**: [Commit SHA(s)]

**Overall Status**: 🟢 APPROVED | 🟡 APPROVED WITH COMMENTS | 🔴 CHANGES REQUIRED

---

### 📈 Dimension Ratings

| Dimension | Rating | Notes |
|-----------|--------|-------|
| 1. Task Completion | 🟢/🟡/🔴 | Brief note |
| 2. Testing & Coverage | 🟢/🟡/🔴 | Brief note |
| 3. Code Quality | 🟢/🟡/🔴 | Brief note |
| 4. Security | 🟢/🟡/🔴 | Brief note |
| 5. Error Handling | 🟢/🟡/🔴 | Brief note |
| 6. Performance | 🟢/🟡/🔴 | Brief note |
| 7. Architecture | 🟢/🟡/🔴 | Brief note |
| 8. Documentation | 🟢/🟡/🔴 | Brief note |
| 9. Integration | 🟢/🟡/🔴 | Brief note |
| 10. Best Practices | 🟢/🟡/🔴 | Brief note |

---

### 🔴 Critical Issues (Must Fix)

If any exist, list them here with:

1. **Issue Title**
   - **Location**: `file.py:123`
   - **Problem**: Detailed description of the issue
   - **Impact**: Why this is critical
   - **Solution**: Specific recommendation to fix
   - **Priority**: P0/P1/P2

Example:
```
1. **Missing Error Handling for Database Connection**
   - **Location**: `services/sync_service.py:45`
   - **Problem**: Database connection errors are not caught, causing the application to crash
   - **Impact**: User experience is degraded; application becomes unreliable
   - **Solution**: Wrap database operations in try-except block, catch specific SQLAlchemy exceptions
   - **Priority**: P0 (Critical)
```

---

### 🟡 Suggestions for Improvement (Optional)

Non-blocking suggestions that would improve code quality:

1. **Suggestion Title**
   - **Location**: `file.py:123`
   - **Current**: Description of current implementation
   - **Suggestion**: How it could be improved
   - **Benefit**: Why this improvement is valuable
   - **Effort**: Low/Medium/High

Example:
```
1. **Extract Complex Logic into Helper Function**
   - **Location**: `services/xml_formatter.py:78-95`
   - **Current**: 18-line method with nested conditionals
   - **Suggestion**: Extract grouping logic into separate `_determine_group()` method
   - **Benefit**: Improved readability and testability
   - **Effort**: Low (~15 minutes)
```

---

### ✅ Positive Observations

Highlight what was done well:

- ✨ Excellent test coverage (95%)
- ✨ Clear and descriptive variable names
- ✨ Proper error handling with specific exceptions
- ✨ Well-documented complex algorithms
- ✨ Efficient use of async/await
- ✨ Good separation of concerns

---

### 🎯 Acceptance Criteria Verification

Review each acceptance criterion from the task file:

- [x] ✅ Criterion 1: Description - **Met**
- [x] ✅ Criterion 2: Description - **Met**
- [ ] ❌ Criterion 3: Description - **Not Met** - Reason

---

### 📋 Test Coverage Report

```
Module Coverage:
- google_contacts_cisco/services/sync_service.py: 92%
- google_contacts_cisco/repositories/contact_repo.py: 88%
- google_contacts_cisco/models/contact.py: 95%

Overall Coverage: 91% (Target: >80%) ✅
```

---

### 💭 Additional Comments

Any other observations, context, or recommendations.

---

### 🏁 Final Recommendation

**Decision**: 🟢 APPROVE | 🟡 APPROVE WITH MINOR CHANGES | 🔴 REQUEST CHANGES

**Justification**: [1-2 sentence summary of why you made this decision]

**Next Steps**:
- If approved: Ready to merge/move to next task
- If minor changes: List specific items to address (can be done in follow-up)
- If changes required: List critical issues that must be fixed before approval

---

## Review Guidelines

### Be Constructive

- Focus on the code, not the person
- Provide specific, actionable feedback
- Explain the "why" behind your suggestions
- Acknowledge good work
- Assume positive intent

### Be Thorough But Efficient

- Don't nitpick minor style issues if tooling catches them
- Focus on correctness, security, and maintainability
- Prioritize critical issues over minor improvements
- Use automated tools to catch basic issues

### Consider Context

- Understand the task's scope and purpose
- Consider time constraints and priorities
- Balance perfectionism with pragmatism
- Recognize when "good enough" is appropriate

### Follow Up

- Be available for questions and discussion
- Help implement suggested changes if needed
- Re-review after changes are made
- Celebrate when tasks are successfully completed

---

## Common Review Scenarios

### Scenario 1: Foundation Tasks (1-6)

Focus on:
- Proper setup and configuration
- Establishing patterns for future tasks
- Solid test infrastructure
- Clear documentation

### Scenario 2: Integration Tasks (4-11)

Focus on:
- API integration correctness
- Error handling for external services
- Data transformation accuracy
- Performance of sync operations

### Scenario 3: Frontend Tasks (15-19)

Focus on:
- Component structure and reusability
- Type safety in TypeScript
- Reactive state management
- User experience and accessibility
- API integration

### Scenario 4: Testing Tasks (20-22)

Focus on:
- Test coverage and quality
- Proper use of fixtures and mocks
- Testing strategy and organization
- CI/CD integration

---

## Success Criteria

A review is complete when:

✅ All 10 dimensions have been evaluated  
✅ Ratings assigned for each dimension  
✅ Critical issues identified and documented  
✅ Suggestions provided where appropriate  
✅ Acceptance criteria verified  
✅ Test coverage confirmed  
✅ Final recommendation made  
✅ Feedback is clear and actionable  

---

## Remember

The goal of code review is to:

1. **Ensure Quality**: Catch bugs and issues before they cause problems
2. **Share Knowledge**: Help the team learn and grow
3. **Maintain Standards**: Keep the codebase consistent and maintainable
4. **Improve Collaboration**: Foster team communication and shared ownership

Be thorough, be kind, and be constructive. Great code reviews make great software! 🚀

---

*Version: 1.0*  
*Last Updated: December 18, 2024*  
*Project: Google Contacts Cisco Directory*
