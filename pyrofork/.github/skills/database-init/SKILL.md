---
name: database-init
description: Expert on database initialization with Railway.com persistent storage and GitHub repository files. Use when initializing database, handling mount volumes, or setting up database persistence.
---

# Database Initialization Agent

## Role
Expert on database initialization considering Railway.com persistent storage and GitHub repository files.

## Problem
On first Railway.com startup:
1. Mount volume is empty - database file not created automatically
2. Database file from GitHub repository (`data/advertisements.db`) not pulled into mount
3. Bot creates empty database in mount, losing repository data

## Solution: Smart Database Initialization

### Initialization Logic

1. **Check mount volume** (`/app/data/advertisements.db`):
   - If file exists and has data (COUNT(*) > 0) → use it
   - If file exists but empty (COUNT(*) = 0) → check repository
   - If file doesn't exist → check repository

2. **Check repository** (`data/advertisements.db`):
   - If file exists and has data → copy to mount
   - If file exists but empty → create new database in mount
   - If file doesn't exist → create new database in mount

3. **Copy from repository to mount**:
   - Copy database file from `data/advertisements.db` to `/app/data/advertisements.db`
   - Preserve file permissions
   - Log operation

## Algorithm

```
1. Check mount: /app/data/advertisements.db
   ├─ File exists?
   │  ├─ Yes → Check record count
   │  │  ├─ COUNT(*) > 0 → Use mount (✅)
   │  │  └─ COUNT(*) = 0 → Go to step 2
   │  └─ No → Go to step 2
   │
2. Check repository: data/advertisements.db
   ├─ File exists?
   │  ├─ Yes → Check record count
   │  │  ├─ COUNT(*) > 0 → Copy to mount (📥)
   │  │  └─ COUNT(*) = 0 → Create new DB in mount (🆕)
   │  └─ No → Create new DB in mount (🆕)
   │
3. Initialize DB (create tables, migrations)
```

## Edge Cases

1. **Mount available but file corrupted**:
   - Check database integrity
   - If corrupted → use repository

2. **Both files empty**:
   - Create new database in mount

3. **Both files contain data**:
   - Use mount (priority to persistent storage)

4. **Copy error**:
   - Log error
   - Create new database in mount

## Success Criteria

- ✅ Mount checked first priority
- ✅ Repository used as fallback
- ✅ Data not lost on first startup
- ✅ All operations logged
- ✅ Error handling at each step
