# CLAUDE.md - AI Assistant Guide

This document provides comprehensive guidance for AI assistants working with this repository.

## Repository Overview

**Repository**: megrich23/0
**Status**: New repository (currently empty)
**Purpose**: [To be defined as project develops]

## Repository Structure

```
/
├── CLAUDE.md          # This file - AI assistant guidance
├── README.md          # Project documentation (to be created)
├── .gitignore         # Git ignore patterns (to be created)
├── src/               # Source code directory (to be created)
├── tests/             # Test files (to be created)
├── docs/              # Additional documentation (to be created)
└── [other dirs]       # As project needs evolve
```

## Development Workflows

### Git Workflow

**Branch Naming Convention:**
- Feature branches: `claude/claude-md-<session-id>`
- Main branch: TBD (main or master)
- Always work on designated branch provided in task context

**Commit Guidelines:**
1. Write clear, descriptive commit messages
2. Use conventional commits format when applicable:
   - `feat: add new feature`
   - `fix: resolve bug`
   - `docs: update documentation`
   - `refactor: restructure code`
   - `test: add or update tests`
   - `chore: maintenance tasks`

3. Commit atomic changes (one logical change per commit)
4. Always verify changes with `git status` and `git diff` before committing

**Push Protocol:**
- Always use: `git push -u origin <branch-name>`
- Branch must start with `claude/` and end with matching session ID
- Retry on network failures: up to 4 times with exponential backoff (2s, 4s, 8s, 16s)
- Never force push to main/master without explicit permission

### Code Organization

**File Naming:**
- Use descriptive, lowercase names with hyphens or underscores
- Match naming convention of existing files in the project
- Example: `user-service.js`, `data_processor.py`

**Directory Structure:**
- Keep related files together
- Separate concerns (models, views, controllers, utilities)
- Follow language/framework conventions

**Import/Require Organization:**
- Standard library imports first
- Third-party dependencies second
- Local imports last
- Group and alphabetize within each section

### Code Style and Quality

**General Principles:**
1. **Simplicity First**: Avoid over-engineering
2. **YAGNI**: You Aren't Gonna Need It - don't add features speculatively
3. **DRY**: Don't Repeat Yourself, but avoid premature abstraction
4. **Self-Documenting Code**: Prefer clear code over comments
5. **Security**: Always consider OWASP Top 10 vulnerabilities

**What to Avoid:**
- Adding features beyond what's requested
- Refactoring unrelated code
- Adding excessive error handling for impossible scenarios
- Creating abstractions for one-time operations
- Adding comments to unchanged code
- Backwards-compatibility hacks for unused code

**Security Checklist:**
- [ ] No SQL injection vulnerabilities
- [ ] No XSS vulnerabilities
- [ ] No command injection
- [ ] Proper input validation at system boundaries
- [ ] Secure authentication/authorization
- [ ] No hardcoded secrets or credentials
- [ ] Proper error handling (no sensitive data in errors)

### Documentation

**Code Comments:**
- Only add where logic isn't self-evident
- Explain "why" not "what"
- Keep comments up to date with code changes

**README.md Requirements:**
- Project description and purpose
- Installation/setup instructions
- Usage examples
- Configuration options
- Contributing guidelines
- License information

**Function/Class Documentation:**
- Document public APIs
- Include parameter types and return values
- Provide usage examples for complex functions
- Keep docs close to code

### Testing

**Testing Strategy:**
- Write tests for new features
- Ensure tests pass before committing
- Fix failing tests immediately
- Don't commit commented-out tests

**Test Organization:**
- Mirror source directory structure in tests
- Name test files clearly: `test_feature.py`, `feature.test.js`
- Group related tests together
- Use descriptive test names

### Task Management

**Using TodoWrite:**
- Create todos for multi-step tasks (3+ steps)
- Mark tasks in_progress before starting
- Complete tasks immediately when done
- Keep only one task in_progress at a time
- Remove irrelevant tasks

**When to Use Todos:**
- Complex multi-step implementations
- Bug fixes requiring multiple changes
- Tasks with dependencies
- User provides multiple requests

**When to Skip Todos:**
- Single, straightforward tasks
- Simple bug fixes
- Trivial operations

## AI Assistant Best Practices

### Before Making Changes

1. **Read First**: Always read files before modifying
2. **Understand Context**: Review related files and dependencies
3. **Plan Complex Tasks**: Use TodoWrite for multi-step work
4. **Verify Assumptions**: Don't guess - investigate

### During Implementation

1. **Stay Focused**: Only implement what's requested
2. **Test Incrementally**: Verify changes as you go
3. **Check Security**: Review for common vulnerabilities
4. **Follow Patterns**: Match existing code style

### After Implementation

1. **Verify Changes**: Use git diff to review all changes
2. **Run Tests**: Ensure all tests pass
3. **Clean Commits**: Create clear, atomic commits
4. **Update Todos**: Mark tasks complete

### Communication

- Be concise and technical
- No emojis unless requested
- Output text directly (no bash echo for communication)
- Include file references: `file_path:line_number`
- Admit uncertainty rather than guessing

## Project-Specific Conventions

[This section will be updated as project conventions are established]

### Language/Framework

- **Primary Language**: [To be determined]
- **Framework**: [To be determined]
- **Package Manager**: [To be determined]

### Dependencies

- Document all dependencies
- Specify version constraints
- Prefer stable, well-maintained packages
- Review licenses for compatibility

### Configuration

- Use environment variables for secrets
- Provide `.env.example` template
- Document all configuration options
- Never commit sensitive data

### API Design

- Use RESTful conventions (if applicable)
- Version APIs appropriately
- Document all endpoints
- Validate input at boundaries

### Error Handling

- Fail fast for programmer errors
- Handle user errors gracefully
- Log errors appropriately
- Don't expose internals to users

## Tools and Commands

### Useful Git Commands

```bash
# Check status
git status

# View changes
git diff

# View commit history
git log --oneline -10

# Create and switch to branch
git checkout -b branch-name

# Stage and commit
git add <files>
git commit -m "message"

# Push to remote
git push -u origin branch-name

# Fetch updates
git fetch origin branch-name
```

### Project Commands

[To be added as build/test/deploy commands are established]

## Troubleshooting

### Common Issues

1. **Push fails with 403**: Verify branch name starts with `claude/` and ends with session ID
2. **Network failures**: Retry with exponential backoff
3. **Merge conflicts**: Fetch latest, resolve conflicts, commit resolution
4. **Tests failing**: Fix immediately before proceeding

## Resources

### Documentation
- [To be added as relevant docs are created]

### External Resources
- Git documentation: https://git-scm.com/doc
- OWASP Top 10: https://owasp.org/www-project-top-ten/

---

**Last Updated**: 2026-01-07
**Version**: 1.0.0

**Note**: This document should be updated as the project evolves and new conventions are established. AI assistants should help keep this file current by suggesting updates when they notice new patterns or conventions emerging in the codebase.
