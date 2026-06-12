---
name: git-watch
description: Automated version control guardian - commits code after every change to prevent data loss
---

# Git Watch - Automated Version Control Guardian

## Purpose
Prevent code loss by ensuring EVERY change is committed immediately. This skill was created after days of work were lost due to uncommitted code.

## When to Use
- After ANY file change, edit, write, or code generation
- At the end of every development session
- Before switching tasks or agents

## CRITICAL RULES

### 1. Commit After Every Change
After any file modification, you MUST:
```bash
git add <changed-files>
git commit -m "type: description"
git log --oneline -1  # Verify
```

### 2. Conventional Commits
Use descriptive commit messages:
- `feat:` - New feature
- `fix:` - Bug fix
- `refactor:` - Code refactoring
- `docs:` - Documentation
- `test:` - Tests
- `chore:` - Maintenance
- `infra:` - Infrastructure/MCP/agent config

### 3. NEVER End With Uncommitted Changes
Always run `git status` before wrapping up. Working tree must be clean.

### 4. Recovery Procedure
If changes are lost:
- Run `git reflog` to find dangling commits
- Check `.trash/` directory for recent files
- NEVER force push

## Example Session
```
# After writing code...
git add src/new-feature.ts
git commit -m "feat: add user authentication"
git log --oneline -1
# Output: abc1234 feat: add user authentication

git status
# Must show: nothing to commit, working tree clean
```
