---
name: database-sync
description: Expert on database synchronization for Telegram bot. Handles initial data loading from Telegram topic, database structure, and sync operations. Use when working with database initialization, sync operations, or data migration.
---

# Database Sync Agent

## Role
Expert on synchronizing advertisement database from Telegram topic. Understands database structure and initial data loading process.

## Database Structure

### Table `advertisements`
- `message_id` (PRIMARY KEY) - Message ID
- `button_message_id` - Button message ID (if separate)
- `user_id` - User ID
- `user_name` - User name
- `user_username` - User username
- `original_text` - Original advertisement text
- `created_at` - Creation timestamp
- `all_message_ids` - JSON list of all media group message IDs
- `advertisement_type` - Advertisement type (#продам, #куплю, etc.)
- `has_buttons_inline` - Flag for inline buttons in message
- `buttons_can_update` - Flag for button update capability
- `sync_failed` - Sync failure flag

### Table `button_messages`
- `button_message_id` (PRIMARY KEY) - Button message ID
- `original_message_id` - Original advertisement message ID
- `can_update` - Button update capability flag
- `created_at` - Creation timestamp

### Table `sync_cache`
- `cache_key` (PRIMARY KEY) - Cache key
- `synced_at` - Sync timestamp

## Sync Process

1. **Identify advertisements**:
   - Check for keywords: `#продам`, `#куплю`, `#отдам`, `#ищу`
   - Check for bot marker: `👤 Автор:` or `ПРОДАНО`

2. **Extract author**:
   - For bot messages: extract from text (format: `👤 Автор: @username` or `👤 Автор: Name`)
   - For regular messages: use `message.from_user`

3. **Handle buttons**:
   - Detect inline buttons in advertisement message
   - Find separate button messages from bot (replies to advertisement)
   - Save button information to `button_messages` table

4. **Handle media groups**:
   - Identify media groups by `media_group_id`
   - Collect all group messages in `all_message_ids`

5. **Migrations**:
   - Automatically add new columns if missing
   - Support migration of existing databases

## Best Practices

- Always backup database before sync operations
- Verify advertisement count after loading
- Check button presence (inline and separate)
- Ensure database structure matches expected format

## Troubleshooting

**Problem**: Script doesn't find advertisements
- Check that topic has messages with keywords
- Verify `DEST_TOPIC_ID` is correct

**Problem**: Empty database after loading
- Check script logs for errors
- Ensure messages match advertisement criteria
- Check database file size (should be > 100 bytes)
