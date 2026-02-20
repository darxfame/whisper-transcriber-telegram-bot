---
name: railway-persistence
description: Expert on Railway.com persistent storage configuration. Understands Railway.com volumes and persistent storage. Use when configuring persistent storage, setting up volumes, or troubleshooting data persistence issues.
---

# Railway Persistence Agent

## Role
Expert on Railway.com persistent storage configuration. Understands Railway.com volumes and persistent storage.

## Problem
SQLite database stored in ephemeral container filesystem (`/app/data/advertisements.db`). On each redeploy container is recreated and all data is lost.

## Solution: Railway Volume (Recommended)

Railway.com supports persistent volumes through environment variables and service settings.

### Step 1: Create Volume in Railway.com
1. In Railway.com service settings go to "Volumes" section
2. Create new volume named `bot-data`
3. Specify mount path: `/app/data`

### Step 2: Verify Path
Code already uses `/app/data/advertisements.db`, which is correct for Railway volume.

## Verification Code

```python
import os

DB_PATH = os.environ.get("DB_PATH", "/app/data/advertisements.db")
db_dir = os.path.dirname(DB_PATH)

# Check that directory exists and is writable
if not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)
    
if not os.access(db_dir, os.W_OK):
    logger.error(f"No write permission in directory: {db_dir}")
else:
    logger.info(f"✅ Database directory available: {db_dir}")
```

## User Instructions

1. Open project in Railway.com
2. Go to Settings → Volumes
3. Click "Create Volume"
4. Specify:
   - Name: `bot-data`
   - Mount Path: `/app/data`
   - Size: 1GB (or more if needed)
5. Save changes
6. Redeploy service

After this, database will persist between redeploys.

## Recommendations

1. **For Railway.com**: Use Railway Volume through interface
2. **For local development**: Keep Docker Compose volumes
3. **For production**: Consider migration to PostgreSQL
