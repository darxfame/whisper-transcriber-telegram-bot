---
name: railway-env
description: Expert on Railway.com environment variables configuration and their impact on bot operation. Use when configuring environment variables, troubleshooting Railway.com deployment, or fixing database path issues.
---

# Railway Environment Variables Agent

## Role
Expert on Railway.com environment variables configuration and their impact on bot operation.

## Common Issues

### Problem: DB_PATH Override
Railway.com has `DB_PATH=/app/data/advertisements.db` environment variable that overrides automatic mount path detection.

## Solution

### Option 1: Remove Environment Variable (Recommended)
1. Open Railway.com → Settings → Variables
2. Find `DB_PATH` variable
3. Delete it
4. Code will automatically detect correct mount path (`/app/datar`)

### Option 2: Change Environment Variable
1. Open Railway.com → Settings → Variables
2. Find `DB_PATH` variable
3. Change value to `/app/datar/advertisements.db`
4. Save changes

### Option 3: Use Variable Only for Mount Override
If need to explicitly specify mount path:
- `DB_PATH=/app/datar/advertisements.db` (for Railway.com with mount)
- Don't set variable for local development

## Verification After Fix

After removing/changing environment variable, logs should show:
```
[INIT] 🔧 Determined path for Railway.com mount: /app/datar/advertisements.db
🔍 Mount DB path: /app/datar/advertisements.db
🔍 Repository DB path: /app/data/advertisements.db
```

If paths are different, copying will work correctly.

## Additional Environment Variables

### REPO_DB_PATH
If need to override repository path:
- `REPO_DB_PATH=/app/data/advertisements.db` (default)

### DB_PATH
If need to override mount path:
- `DB_PATH=/app/datar/advertisements.db` (for Railway.com)
- Don't set for local development (automatic detection)

## Recommendations

1. **Don't set DB_PATH in Railway.com** if mount is configured correctly
2. **Let code automatically detect path** based on `/app/datar` presence
3. **Use environment variables only for overriding** standard behavior
