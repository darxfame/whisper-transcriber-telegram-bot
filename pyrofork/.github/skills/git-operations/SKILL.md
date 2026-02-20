---
name: git-operations
description: Expert on Git operations, commit management, and authentication. Handles git add, commit, push operations. Provides instructions for Git authentication when needed. Use when working with Git commits, pushes, or authentication issues.
---

# Git Operations Agent

## Role
Expert on Git operations including commits, pushes, and authentication setup.

## Common Operations

### Commit Changes
```bash
git add .
git commit -m "type(scope): subject"
```

### Push Changes
```bash
git push origin branch-name
```

## Authentication Setup

### For GitHub (HTTPS)

**Option 1: Personal Access Token (Recommended)**
1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token with `repo` scope
3. Use token as password when pushing

**Option 2: SSH Key**
1. Generate SSH key: `ssh-keygen -t ed25519 -C "your_email@example.com"`
2. Add to GitHub: Settings → SSH and GPG keys → New SSH key
3. Change remote URL: `git remote set-url origin git@github.com:user/repo.git`

**Option 3: GitHub CLI**
```bash
gh auth login
```

### For GitLab

**Personal Access Token:**
1. GitLab → User Settings → Access Tokens
2. Create token with `write_repository` scope
3. Use token as password

### For Bitbucket

**App Password:**
1. Bitbucket → Personal settings → App passwords
2. Create app password with repository permissions
3. Use app password as password

## Handling Lock Files

If `.git/index.lock` exists:
1. Close all Git processes (GitHub Desktop, Git GUI, etc.)
2. Wait 5-10 seconds
3. Try removing lock file manually if needed
4. Retry git operations

## Best Practices

- Always check `git status` before committing
- Use meaningful commit messages (conventional commits)
- Commit related changes together
- Push regularly to avoid conflicts
- Use branches for feature development

## Troubleshooting

**Lock file persists:**
- Close all Git applications
- Check Task Manager for git processes
- Restart computer if needed
- Manually delete `.git/index.lock` if safe

**Authentication fails:**
- Check credentials are correct
- Verify token/SSH key has required permissions
- Try using GitHub CLI for easier authentication
